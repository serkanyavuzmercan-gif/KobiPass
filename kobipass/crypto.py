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
import stat
import struct
import tempfile
import time
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
    hidden_tabs_json_bytes,
    merge_hidden_tabs,
    vault_from_json_bytes,
    vault_main_json_bytes,
    vault_to_json_bytes,
)

MAGIC = b"KBPS"
# Sürüm hem KDF'yi hem slot düzenini kodlar:
#   v1 = PBKDF2,  sabit 3 slot   (eski)
#   v2 = Argon2id, sabit 3 slot  (eski)
#   v3 = Argon2id, değişken slot (slot sayısı byte'ı ile)
#   v4 = PBKDF2,  değişken slot  (eski v1 dosyasına kullanıcı eklenince)
#   v5 = Argon2id, değişken slot + gizli sekme bölmesi (yönetici-özel AEK)
#   v6 = PBKDF2,  değişken slot + gizli sekme bölmesi
VERSION_PBKDF2 = 0x01
VERSION_ARGON2 = 0x02
VERSION_ARGON2_MULTI = 0x03
VERSION_PBKDF2_MULTI = 0x04
VERSION_ARGON2_HIDDEN = 0x05
VERSION_PBKDF2_HIDDEN = 0x06
VERSION = VERSION_ARGON2_HIDDEN  # yeni kasalar gizli sekme bölmesini içerir
SUPPORTED_VERSIONS = frozenset({0x01, 0x02, 0x03, 0x04, 0x05, 0x06})
# Slot sayısı byte'ı taşıyanlar (değişken slot).
MULTI_VERSIONS = frozenset({0x03, 0x04, 0x05, 0x06})
# Yönetici-özel gizli sekme bölmesini (AEK) taşıyanlar.
HIDDEN_VERSIONS = frozenset({0x05, 0x06})
_PBKDF2_VERSIONS = frozenset({0x01, 0x04, 0x06})     # KDF = PBKDF2 olanlar
LEGACY_SLOT_COUNT = 3
MAX_USER_SLOTS = 64
# Değişken slotlu dosyaya kullanıcı eklenince aynı KDF'yi koruyan yeni sürüm.
_UPGRADE_VERSION = {VERSION_PBKDF2: VERSION_PBKDF2_MULTI, VERSION_ARGON2: VERSION_ARGON2_MULTI}


def _hidden_sibling(version: int) -> int:
    """Verilen sürümün, aynı KDF ailesinden gizli-sekme yeteneğine sahip
    kardeşini döndürür."""
    return VERSION_PBKDF2_HIDDEN if version in _PBKDF2_VERSIONS else VERSION_ARGON2_HIDDEN
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
# En küçük geçerli gövde: magic+sürüm(+sayı) + admin_wrap + min vault blob.
MIN_BODY_SIZE = 6 + WRAP_BLOCK_SIZE + NONCE_SIZE + 16
FILE_CHECKSUM_SIZE = 32


def _atomic_write(path: Path, data: bytes) -> None:
    """Kasayı atomik yazar: aynı dizinde geçici dosya + fsync + os.replace.

    Kayıt sırasında çökme/elektrik kesintisi olsa bile hedef dosya ya eski
    ya da yeni tam haliyle kalır; yarım yazılmış bozuk .enc oluşmaz.
    """
    path = Path(path)
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(
        dir=str(directory), prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _replace_with_retry(tmp_path: Path, path: Path) -> None:
    """os.replace'i Windows'a karşı dayanıklı uygular.

    Hedef dosya salt-okunur olabilir (koruma katmanı) ya da Windows Defender /
    indeksleyici gibi bir süreç kısa süreliğine kilitlemiş olabilir; her ikisi
    de 'Erişim engellendi' (WinError 5) üretir. Salt-okunuru temizleyip birkaç
    kez kısa aralıklarla yeniden deneriz.
    """
    try:
        os.replace(tmp_path, path)
        return
    except PermissionError:
        pass
    # Hedefteki salt-okunur özniteliğini kaldır (kayıt öncesi zaten denenir ama
    # geçici kilit nedeniyle atlanmış olabilir).
    try:
        if path.exists():
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass
    for delay in (0.05, 0.1, 0.2, 0.4):
        time.sleep(delay)
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError:
            continue
    # Son bir deneme; hâlâ başarısızsa hatayı yükselt (çağıran yakalar).
    os.replace(tmp_path, path)


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
    """Dosyadan okunan sarmalayıcılar — kullanıcı kaydında yeniden kullanılır.

    Gizli sekme izolasyonu (v5/v6):
      - ``aek_wrap``: yönetici-özel AEK sarmalayıcısı (yalnızca yönetici parolası
        açar). Yoksa boş.
      - ``aek``: AEK açık metni — yalnızca yönetici oturumunda bilinir; alt
        kullanıcıda ``None``. ``None`` iken gizli blok aynen taşınır.
      - ``hidden_blob``: AEK ile şifreli gizli sekmeler (nonce+şifreli metin).
        Alt kullanıcı bunu çözemez, olduğu gibi taşır.
    """

    admin_wrap: bytes
    user_slots: list[UserSlotWrap]
    dek: bytes
    version: int = VERSION
    aek_wrap: bytes = b""
    aek: bytes | None = None
    hidden_blob: bytes = b""


@dataclass
class UnlockResult:
    role: Literal["admin", "user"]
    user_slot: int | None
    vault: KobiVault
    keys: VaultFileKeys


def derive_key(password: str, salt: bytes, version: int = VERSION) -> bytes:
    if len(salt) != SALT_SIZE:
        raise VaultCryptoError("crypto.invalid_salt")
    if version not in SUPPORTED_VERSIONS:
        raise VaultCryptoError("crypto.unsupported_version")
    if version in _PBKDF2_VERSIONS:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=KEY_LENGTH,
        type=Type.ID,
    )


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


def _encrypt_vault_blob(vault: KobiVault, dek: bytes, version: int = VERSION) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    # Gizli-sekme yeteneği olan sürümlerde ana gövde YALNIZCA normal sekmeleri
    # taşır; gizli sekmeler ayrı AEK bloğunda durur. Eski sürümlerde tüm
    # sekmeler ana gövdededir (gizli bölme yoktur).
    if version in HIDDEN_VERSIONS:
        plaintext = vault_main_json_bytes(vault)
    else:
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


def _encrypt_hidden_blob(vault: KobiVault, aek: bytes) -> bytes:
    """Gizli sekmeleri AEK ile şifreler (nonce+şifreli metin)."""
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(aek).encrypt(nonce, hidden_tabs_json_bytes(vault), None)
    return nonce + ciphertext


def _decrypt_hidden_into(vault: KobiVault, blob: bytes, aek: bytes) -> None:
    """AEK ile gizli bloğu çözüp sekmeleri vault içine yerleştirir."""
    if not blob:
        return
    if len(blob) < NONCE_SIZE + 16:
        raise VaultCryptoError("crypto.corrupt_vault")
    nonce = blob[:NONCE_SIZE]
    ciphertext = blob[NONCE_SIZE:]
    try:
        plaintext = AESGCM(aek).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise VaultCryptoError("crypto.corrupt_vault") from exc
    merge_hidden_tabs(vault, plaintext)


def _empty_wrap() -> bytes:
    return bytes(WRAP_BLOCK_SIZE)


def _finalize_vault_bytes(blob: bytes) -> bytes:
    return blob + hashlib.sha256(blob).digest()


def _strip_file_checksum(data: bytes) -> bytes:
    """Sondaki SHA-256 özetini doğrular; eski dosyalar için geriye dönük uyumluluk."""
    if len(data) < FILE_CHECKSUM_SIZE + MIN_BODY_SIZE:
        return data
    body = data[:-FILE_CHECKSUM_SIZE]
    if hashlib.sha256(body).digest() == data[-FILE_CHECKSUM_SIZE:]:
        return body
    if len(data) >= MIN_BODY_SIZE and data[:4] == MAGIC:
        return data
    raise VaultCryptoError("crypto.file_corrupt")


def _parse_file(
    data: bytes,
) -> tuple[int, bytes, list[UserSlotWrap], bytes, bytes, bytes]:
    data = _strip_file_checksum(data)
    if len(data) < MIN_BODY_SIZE:
        raise VaultCryptoError("crypto.file_too_short")
    if data[:4] != MAGIC:
        raise VaultCryptoError("crypto.invalid_file")
    version = data[4]
    if version not in SUPPORTED_VERSIONS:
        raise VaultCryptoError("crypto.unsupported_version")

    offset = 5
    if version in MULTI_VERSIONS:
        slot_count = data[offset]
        offset += 1
        if slot_count > MAX_USER_SLOTS:
            raise VaultCryptoError("crypto.invalid_user_slots")
    else:
        slot_count = LEGACY_SLOT_COUNT

    end_of_slots = offset + WRAP_BLOCK_SIZE + slot_count * (1 + WRAP_BLOCK_SIZE)
    if len(data) < end_of_slots + NONCE_SIZE + 16:
        raise VaultCryptoError("crypto.file_too_short")

    admin_wrap = data[offset : offset + WRAP_BLOCK_SIZE]
    offset += WRAP_BLOCK_SIZE

    user_slots: list[UserSlotWrap] = []
    for _ in range(slot_count):
        enabled = data[offset] == 1
        offset += 1
        wrap = data[offset : offset + WRAP_BLOCK_SIZE]
        offset += WRAP_BLOCK_SIZE
        user_slots.append(UserSlotWrap(enabled=enabled, wrap=wrap))

    aek_wrap = b""
    hidden_blob = b""
    if version in HIDDEN_VERSIONS:
        # Yönetici-özel AEK sarmalayıcısı + uzunluk önekli gizli blok.
        if len(data) < offset + WRAP_BLOCK_SIZE + 4:
            raise VaultCryptoError("crypto.file_too_short")
        aek_wrap = data[offset : offset + WRAP_BLOCK_SIZE]
        offset += WRAP_BLOCK_SIZE
        (hidden_len,) = struct.unpack(">I", data[offset : offset + 4])
        offset += 4
        if len(data) < offset + hidden_len + NONCE_SIZE + 16:
            raise VaultCryptoError("crypto.file_too_short")
        hidden_blob = data[offset : offset + hidden_len]
        offset += hidden_len

    vault_blob = data[offset:]
    return version, admin_wrap, user_slots, aek_wrap, hidden_blob, vault_blob


def _header_prefix(version: int, slot_count: int) -> list[bytes]:
    parts = [MAGIC, bytes([version])]
    if version in MULTI_VERSIONS:
        parts.append(bytes([slot_count]))
    return parts


def _hidden_section_bytes(keys: VaultFileKeys, vault: KobiVault) -> bytes:
    """Gizli sekme bölmesini (aek_wrap + uzunluk + gizli blok) üretir.

    Yönetici (``aek`` bilinir): gizli sekmeleri AEK ile tazeler.
    Alt kullanıcı (``aek is None``): mevcut opak bloğu aynen taşır.
    """
    aek_wrap = keys.aek_wrap if keys.aek_wrap else _empty_wrap()
    if keys.aek is not None:
        hidden_blob = _encrypt_hidden_blob(vault, keys.aek)
    else:
        hidden_blob = keys.hidden_blob or b""
    return b"".join(
        [aek_wrap, struct.pack(">I", len(hidden_blob)), hidden_blob]
    )


def _serialize_keys(keys: VaultFileKeys, vault: KobiVault) -> bytes:
    parts = _header_prefix(keys.version, len(keys.user_slots))
    parts.append(keys.admin_wrap)
    for slot in keys.user_slots:
        parts.append(struct.pack("B", 1 if slot.enabled else 0))
        parts.append(slot.wrap)
    if keys.version in HIDDEN_VERSIONS:
        parts.append(_hidden_section_bytes(keys, vault))
    parts.append(_encrypt_vault_blob(vault, keys.dek, keys.version))
    return _finalize_vault_bytes(b"".join(parts))


def build_vault_file(
    vault: KobiVault,
    admin_password: str,
    user_passwords: list[tuple[bool, str]],
    *,
    version: int = VERSION,
) -> bytes:
    """Vault dosyası oluşturur veya tüm sarmalayıcıları yeniden üretir."""
    if version not in SUPPORTED_VERSIONS:
        raise VaultCryptoError("crypto.unsupported_version")
    if version in MULTI_VERSIONS:
        if not 0 <= len(user_passwords) <= MAX_USER_SLOTS:
            raise VaultCryptoError("crypto.invalid_user_slots")
    elif len(user_passwords) != LEGACY_SLOT_COUNT:
        raise VaultCryptoError("crypto.invalid_user_slots")
    if not passwords_are_unique(admin_password, user_passwords):
        raise VaultCryptoError("crypto.duplicate_password")

    dek = os.urandom(DEK_SIZE)
    admin_wrap = _wrap_dek(dek, admin_password, version)

    parts = _header_prefix(version, len(user_passwords))
    parts.append(admin_wrap)
    for enabled, password in user_passwords:
        parts.append(struct.pack("B", 1 if enabled else 0))
        if enabled and password:
            parts.append(_wrap_dek(dek, password, version))
        else:
            parts.append(_empty_wrap())

    if version in HIDDEN_VERSIONS:
        # Yönetici-özel AEK: yalnızca yönetici parolasıyla sarılır; gizli
        # sekmeler bununla şifrelenir (alt kullanıcının parolası açamaz).
        aek = os.urandom(DEK_SIZE)
        keys = VaultFileKeys(
            admin_wrap=admin_wrap,
            user_slots=[],
            dek=dek,
            version=version,
            aek_wrap=_wrap_dek(aek, admin_password, version),
            aek=aek,
        )
        parts.append(_hidden_section_bytes(keys, vault))

    parts.append(_encrypt_vault_blob(vault, dek, version))
    return _finalize_vault_bytes(b"".join(parts))


def write_vault_file_with_keys(
    path: Path,
    vault: KobiVault,
    keys: VaultFileKeys,
) -> None:
    """Mevcut sarmalayıcıları koruyarak yalnızca vault gövdesini yeniden şifreler."""
    _atomic_write(path, _serialize_keys(keys, vault))


def update_user_wraps(
    keys: VaultFileKeys,
    user_passwords: list[tuple[bool, str]],
) -> list[UserSlotWrap]:
    """
    Kullanıcı slot sarmalayıcılarını günceller.
    Boş parola = mevcut sarmalayıcı korunur (parola değişmedi).
    """
    if len(user_passwords) > MAX_USER_SLOTS:
        raise VaultCryptoError("crypto.invalid_user_slots")

    updated: list[UserSlotWrap] = []
    for index, (enabled, password) in enumerate(user_passwords):
        old = keys.user_slots[index] if index < len(keys.user_slots) else None
        if not enabled:
            updated.append(UserSlotWrap(enabled=False, wrap=_empty_wrap()))
        elif password:
            updated.append(
                UserSlotWrap(
                    enabled=True,
                    wrap=_wrap_dek(keys.dek, password, keys.version),
                )
            )
        elif old is not None and old.enabled:
            updated.append(UserSlotWrap(enabled=True, wrap=old.wrap))
        else:
            updated.append(UserSlotWrap(enabled=False, wrap=_empty_wrap()))
    return updated


def update_admin_wrap(keys: VaultFileKeys, new_admin_password: str) -> VaultFileKeys:
    """Yönetici sarmalayıcısını yeni parola ile yeniden üretir.

    Gizli sürümlerde AEK sarmalayıcısı da yeni parolayla yenilenir (AEK yalnızca
    yönetici parolasıyla açılır).
    """
    aek_wrap = keys.aek_wrap
    if keys.version in HIDDEN_VERSIONS and keys.aek is not None:
        aek_wrap = _wrap_dek(keys.aek, new_admin_password, keys.version)
    return VaultFileKeys(
        admin_wrap=_wrap_dek(keys.dek, new_admin_password, keys.version),
        user_slots=list(keys.user_slots),
        dek=keys.dek,
        version=keys.version,
        aek_wrap=aek_wrap,
        aek=keys.aek,
        hidden_blob=keys.hidden_blob,
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
    # Slot sayısı 3'ten farklıysa ve dosya hâlâ eski sabit formattaysa,
    # aynı KDF'yi koruyan değişken-slot sürümüne yükselt.
    version = keys.version
    if len(user_slots) != LEGACY_SLOT_COUNT and version not in MULTI_VERSIONS:
        version = _UPGRADE_VERSION[version]
    # Gizli sekme varsa ve dosya henüz gizli-yetenekli değilse, AEK'i olan
    # yönetici oturumunda gizli-sekme sürümüne yükselt (aksi halde gizli veri
    # kaybolurdu). AEK yalnızca yönetici oturumunda bulunur.
    if vault.hidden_tabs() and keys.aek is not None and version not in HIDDEN_VERSIONS:
        version = _hidden_sibling(version)
    admin_wrap = keys.admin_wrap
    aek_wrap = keys.aek_wrap
    if admin_password:
        admin_wrap = _wrap_dek(keys.dek, admin_password, version)
        if version in HIDDEN_VERSIONS and keys.aek is not None:
            aek_wrap = _wrap_dek(keys.aek, admin_password, version)
    new_keys = VaultFileKeys(
        admin_wrap=admin_wrap,
        user_slots=user_slots,
        dek=keys.dek,
        version=version,
        aek_wrap=aek_wrap,
        aek=keys.aek,
        hidden_blob=keys.hidden_blob,
    )
    _atomic_write(path, _serialize_keys(new_keys, vault))
    return new_keys


def try_unlock_vault(data: bytes, password: str) -> UnlockResult:
    version, admin_wrap, user_slots, aek_wrap, hidden_blob, vault_blob = _parse_file(
        data
    )

    try:
        dek = _unwrap_dek(admin_wrap, password, version)
        vault = _decrypt_vault_blob(vault_blob, dek)
        # Yönetici: gizli sekmeleri çöz (varsa) ve vault içine yerleştir.
        if version in HIDDEN_VERSIONS:
            aek = _unwrap_dek(aek_wrap, password, version)
            _decrypt_hidden_into(vault, hidden_blob, aek)
        else:
            # Eski (gizli-yeteneksiz) dosya: yönetici için taze bir AEK üret ki
            # ilk gizli sekme oluşturulunca kayıtta dosya gizli sürüme yükselsin.
            aek = os.urandom(DEK_SIZE)
            aek_wrap = _wrap_dek(aek, password, version)
        keys = VaultFileKeys(
            admin_wrap=admin_wrap,
            user_slots=user_slots,
            dek=dek,
            version=version,
            aek_wrap=aek_wrap,
            aek=aek,
            hidden_blob=hidden_blob,
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
            # Alt kullanıcı: gizli bloğu ÇÖZEMEZ; yalnızca opak biçimde taşır.
            keys = VaultFileKeys(
                admin_wrap=admin_wrap,
                user_slots=user_slots,
                dek=dek,
                version=version,
                aek_wrap=aek_wrap,
                aek=None,
                hidden_blob=hidden_blob,
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
    _atomic_write(
        path,
        build_vault_file(vault, admin_password, user_passwords, version=version),
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


def passwords_are_unique(
    admin_password: str,
    user_passwords: list[tuple[bool, str]],
) -> bool:
    """Yönetici ve etkin, açıkça verilen kullanıcı parolaları benzersiz mi?"""
    passwords = [admin_password]
    passwords.extend(
        password
        for enabled, password in user_passwords
        if enabled and password
    )
    return len(passwords) == len(set(passwords))


def password_matches_user_slot(
    keys: VaultFileKeys,
    password: str,
    slot_index: int,
) -> bool:
    """Parola, belirtilen mevcut kullanıcı sarmalayıcısını açıyor mu?"""
    if not password or not 0 <= slot_index < len(keys.user_slots):
        return False
    slot = keys.user_slots[slot_index]
    if not slot.enabled:
        return False
    try:
        return _unwrap_dek(slot.wrap, password, keys.version) == keys.dek
    except WrongPasswordError:
        return False
