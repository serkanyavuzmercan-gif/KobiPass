"""
kobiPass şifreleme katmanı — KBPS zarf şifreleme formatı.

- Rastgele DEK ile vault JSON şifrelenir.
- DEK yönetici ve kullanıcı parolalarıyla ayrı ayrı sarılır.
- v1: PBKDF2-HMAC-SHA256, 100.000 iterasyon.
- v2: Argon2id (yeni dosyalar).
- AES-256-GCM.
"""

from __future__ import annotations

import hashlib
import os
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from kobipass.vault_model import (
    KobiVault,
    USER_SLOT_COUNT,
    vault_from_json_bytes,
    vault_to_json_bytes,
)

MAGIC = b"KBPS"
VERSION_PBKDF2 = 0x01
VERSION_ARGON2 = 0x02
VERSION = VERSION_ARGON2
SUPPORTED_VERSIONS = frozenset({VERSION_PBKDF2, VERSION_ARGON2})
SALT_SIZE = 16
NONCE_SIZE = 12
DEK_SIZE = 32
PBKDF2_ITERATIONS = 100_000
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65_536
ARGON2_PARALLELISM = 4
KEY_LENGTH = 32
WRAP_CIPHERTEXT_SIZE = DEK_SIZE + 16  # AES-GCM tag
WRAP_BLOCK_SIZE = SALT_SIZE + NONCE_SIZE + WRAP_CIPHERTEXT_SIZE
HEADER_SIZE = 5 + WRAP_BLOCK_SIZE + USER_SLOT_COUNT * (1 + WRAP_BLOCK_SIZE)
FILE_CHECKSUM_SIZE = 32


class VaultCryptoError(Exception):
    """Şifreleme/çözme veya dosya formatı hatası."""


class WrongPasswordError(VaultCryptoError):
    """Parola yanlış veya bütünlük doğrulaması başarısız."""


class AccessDeniedError(VaultCryptoError):
    """Hiçbir rol ile dosya açılamadı."""


@dataclass
class UserSlotWrap:
    enabled: bool = False
    wrap: bytes = field(default_factory=lambda: bytes(WRAP_BLOCK_SIZE))


@dataclass
class VaultFileKeys:
    """Dosyadan okunan sarmalayıcılar — kullanıcı kaydında yeniden kullanılır."""

    admin_wrap: bytes
    user_slots: list[UserSlotWrap]
    dek: bytes
    version: int = VERSION


@dataclass
class UnlockResult:
    role: Literal["admin", "user"]
    user_slot: int | None
    vault: KobiVault
    keys: VaultFileKeys


def derive_key(password: str, salt: bytes, version: int = VERSION) -> bytes:
    if len(salt) != SALT_SIZE:
        raise VaultCryptoError("crypto.invalid_salt")
    if version == VERSION_PBKDF2:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))
    if version == VERSION_ARGON2:
        return hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=KEY_LENGTH,
            type=Type.ID,
        )
    raise VaultCryptoError("crypto.unsupported_version")


def _wrap_dek(dek: bytes, password: str, version: int = VERSION) -> bytes:
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt, version)
    ciphertext = AESGCM(key).encrypt(nonce, dek, None)
    if len(ciphertext) != WRAP_CIPHERTEXT_SIZE:
        raise VaultCryptoError("crypto.wrap_failed")
    return salt + nonce + ciphertext


def _unwrap_dek(wrap: bytes, password: str, version: int = VERSION) -> bytes:
    if len(wrap) != WRAP_BLOCK_SIZE:
        raise VaultCryptoError("crypto.invalid_wrap")
    salt = wrap[:SALT_SIZE]
    nonce = wrap[SALT_SIZE : SALT_SIZE + NONCE_SIZE]
    ciphertext = wrap[SALT_SIZE + NONCE_SIZE :]
    key = derive_key(password, salt, version)
    try:
        dek = AESGCM(key).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise WrongPasswordError("crypto.wrong_password") from exc
    if len(dek) != DEK_SIZE:
        raise VaultCryptoError("crypto.invalid_dek")
    return dek


def _encrypt_vault_blob(vault: KobiVault, dek: bytes) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    plaintext = vault_to_json_bytes(vault)
    ciphertext = AESGCM(dek).encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def _decrypt_vault_blob(blob: bytes, dek: bytes) -> KobiVault:
    if len(blob) < NONCE_SIZE + 16:
        raise VaultCryptoError("crypto.file_too_short")
    nonce = blob[:NONCE_SIZE]
    ciphertext = blob[NONCE_SIZE:]
    try:
        plaintext = AESGCM(dek).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise VaultCryptoError("crypto.corrupt_vault") from exc
    return vault_from_json_bytes(plaintext)


def _empty_wrap() -> bytes:
    return bytes(WRAP_BLOCK_SIZE)


def _finalize_vault_bytes(blob: bytes) -> bytes:
    return blob + hashlib.sha256(blob).digest()


def _strip_file_checksum(data: bytes) -> bytes:
    """Sondaki SHA-256 özetini doğrular; eski dosyalar için geriye dönük uyumluluk."""
    if len(data) < FILE_CHECKSUM_SIZE + HEADER_SIZE + NONCE_SIZE + 16:
        return data
    body = data[:-FILE_CHECKSUM_SIZE]
    if hashlib.sha256(body).digest() == data[-FILE_CHECKSUM_SIZE:]:
        return body
    if len(data) >= HEADER_SIZE and data[:4] == MAGIC:
        return data
    raise VaultCryptoError("crypto.file_corrupt")


def _parse_file(data: bytes) -> tuple[int, bytes, list[UserSlotWrap], bytes]:
    data = _strip_file_checksum(data)
    if len(data) < HEADER_SIZE + NONCE_SIZE + 16:
        raise VaultCryptoError("crypto.file_too_short")
    if data[:4] != MAGIC:
        raise VaultCryptoError("crypto.invalid_file")
    version = data[4]
    if version not in SUPPORTED_VERSIONS:
        raise VaultCryptoError("crypto.unsupported_version")

    offset = 5
    admin_wrap = data[offset : offset + WRAP_BLOCK_SIZE]
    offset += WRAP_BLOCK_SIZE

    user_slots: list[UserSlotWrap] = []
    for _ in range(USER_SLOT_COUNT):
        enabled = data[offset] == 1
        offset += 1
        wrap = data[offset : offset + WRAP_BLOCK_SIZE]
        offset += WRAP_BLOCK_SIZE
        user_slots.append(UserSlotWrap(enabled=enabled, wrap=wrap))

    vault_blob = data[offset:]
    return version, admin_wrap, user_slots, vault_blob


def _serialize_keys(keys: VaultFileKeys, vault: KobiVault) -> bytes:
    parts = [MAGIC, bytes([keys.version]), keys.admin_wrap]
    for slot in keys.user_slots:
        parts.append(struct.pack("B", 1 if slot.enabled else 0))
        parts.append(slot.wrap)
    parts.append(_encrypt_vault_blob(vault, keys.dek))
    return _finalize_vault_bytes(b"".join(parts))


def build_vault_file(
    vault: KobiVault,
    admin_password: str,
    user_passwords: list[tuple[bool, str]],
    *,
    version: int = VERSION,
) -> bytes:
    """Vault dosyası oluşturur veya tüm sarmalayıcıları yeniden üretir."""
    if len(user_passwords) != USER_SLOT_COUNT:
        raise VaultCryptoError("crypto.invalid_user_slots")
    if version not in SUPPORTED_VERSIONS:
        raise VaultCryptoError("crypto.unsupported_version")

    dek = os.urandom(DEK_SIZE)
    admin_wrap = _wrap_dek(dek, admin_password, version)

    parts = [MAGIC, bytes([version]), admin_wrap]
    for enabled, password in user_passwords:
        parts.append(struct.pack("B", 1 if enabled else 0))
        if enabled and password:
            parts.append(_wrap_dek(dek, password, version))
        else:
            parts.append(_empty_wrap())

    parts.append(_encrypt_vault_blob(vault, dek))
    return _finalize_vault_bytes(b"".join(parts))


def write_vault_file_with_keys(
    path: Path,
    vault: KobiVault,
    keys: VaultFileKeys,
) -> None:
    """Mevcut sarmalayıcıları koruyarak yalnızca vault gövdesini yeniden şifreler."""
    path.write_bytes(_serialize_keys(keys, vault))


def update_user_wraps(
    keys: VaultFileKeys,
    user_passwords: list[tuple[bool, str]],
) -> list[UserSlotWrap]:
    """
    Kullanıcı slot sarmalayıcılarını günceller.
    Boş parola = mevcut sarmalayıcı korunur (parola değişmedi).
    """
    if len(user_passwords) != USER_SLOT_COUNT:
        raise VaultCryptoError("crypto.invalid_user_slots")

    updated: list[UserSlotWrap] = []
    for index, (enabled, password) in enumerate(user_passwords):
        old = keys.user_slots[index]
        if not enabled:
            updated.append(UserSlotWrap(enabled=False, wrap=_empty_wrap()))
        elif password:
            updated.append(
                UserSlotWrap(
                    enabled=True,
                    wrap=_wrap_dek(keys.dek, password, keys.version),
                )
            )
        elif old.enabled:
            updated.append(UserSlotWrap(enabled=True, wrap=old.wrap))
        else:
            updated.append(UserSlotWrap(enabled=False, wrap=_empty_wrap()))
    return updated


def update_admin_wrap(keys: VaultFileKeys, new_admin_password: str) -> VaultFileKeys:
    """Yönetici sarmalayıcısını yeni parola ile yeniden üretir."""
    return VaultFileKeys(
        admin_wrap=_wrap_dek(keys.dek, new_admin_password, keys.version),
        user_slots=list(keys.user_slots),
        dek=keys.dek,
        version=keys.version,
    )


def write_vault_file_updated(
    path: Path,
    vault: KobiVault,
    keys: VaultFileKeys,
    user_passwords: list[tuple[bool, str]] | None = None,
    *,
    admin_password: str | None = None,
) -> VaultFileKeys:
    """Vault gövdesini yazar; isteğe bağlı sarmalayıcıları günceller."""
    user_slots = (
        update_user_wraps(keys, user_passwords)
        if user_passwords is not None
        else keys.user_slots
    )
    admin_wrap = keys.admin_wrap
    if admin_password:
        admin_wrap = _wrap_dek(keys.dek, admin_password, keys.version)
    new_keys = VaultFileKeys(
        admin_wrap=admin_wrap,
        user_slots=user_slots,
        dek=keys.dek,
        version=keys.version,
    )
    path.write_bytes(_serialize_keys(new_keys, vault))
    return new_keys


def try_unlock_vault(data: bytes, password: str) -> UnlockResult:
    version, admin_wrap, user_slots, vault_blob = _parse_file(data)

    try:
        dek = _unwrap_dek(admin_wrap, password, version)
        vault = _decrypt_vault_blob(vault_blob, dek)
        keys = VaultFileKeys(
            admin_wrap=admin_wrap,
            user_slots=user_slots,
            dek=dek,
            version=version,
        )
        return UnlockResult(role="admin", user_slot=None, vault=vault, keys=keys)
    except WrongPasswordError:
        pass

    for index, slot in enumerate(user_slots):
        if not slot.enabled:
            continue
        try:
            dek = _unwrap_dek(slot.wrap, password, version)
            vault = _decrypt_vault_blob(vault_blob, dek)
            keys = VaultFileKeys(
                admin_wrap=admin_wrap,
                user_slots=user_slots,
                dek=dek,
                version=version,
            )
            return UnlockResult(
                role="user",
                user_slot=index + 1,
                vault=vault,
                keys=keys,
            )
        except WrongPasswordError:
            continue

    raise AccessDeniedError("crypto.wrong_password")


def read_vault_file(path: Path, password: str) -> UnlockResult:
    return try_unlock_vault(path.read_bytes(), password)


def write_vault_file(
    path: Path,
    vault: KobiVault,
    admin_password: str,
    user_passwords: list[tuple[bool, str]],
    *,
    version: int = VERSION,
) -> None:
    path.write_bytes(
        build_vault_file(vault, admin_password, user_passwords, version=version)
    )


def verify_password_against_keys(keys: VaultFileKeys, password: str) -> bool:
    """Mevcut oturum anahtarlarına karşı parola doğrular (kilit açma)."""
    try:
        dek = _unwrap_dek(keys.admin_wrap, password, keys.version)
        return dek == keys.dek
    except WrongPasswordError:
        pass
    for slot in keys.user_slots:
        if not slot.enabled:
            continue
        try:
            dek = _unwrap_dek(slot.wrap, password, keys.version)
            if dek == keys.dek:
                return True
        except WrongPasswordError:
            continue
    return False
