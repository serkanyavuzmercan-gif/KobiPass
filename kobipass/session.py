"""
kobiPass oturum modeli — yönetici ve kullanıcı rolleri.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kobipass.crypto import UnlockResult, VaultFileKeys
from kobipass.vault_model import KobiVault, UserPermissions


@dataclass
class AdminSession:
    admin_password: str
    user_passwords: list[tuple[bool, str]] = field(default_factory=list)
    keys: VaultFileKeys | None = None

    @property
    def is_admin(self) -> bool:
        return True

    @property
    def user_slot(self) -> int | None:
        return None

    def display_role(self) -> str:
        return "admin"


@dataclass
class UserSession:
    user_slot: int
    user_label: str
    user_password: str
    keys: VaultFileKeys

    @property
    def is_admin(self) -> bool:
        return False

    def display_role(self) -> str:
        return f"user_{self.user_slot}"


Session = AdminSession | UserSession


def session_from_unlock(
    result: UnlockResult,
    password: str,
    vault: KobiVault,
) -> Session:
    if result.role == "admin":
        user_passwords = [
            (slot.enabled, "") for slot in result.keys.user_slots
        ]
        return AdminSession(
            admin_password=password,
            user_passwords=user_passwords,
            keys=result.keys,
        )

    label = (
        vault.user_slot_labels[result.user_slot - 1]
        if result.user_slot
        else f"Kullanıcı {result.user_slot}"
    )
    return UserSession(
        user_slot=result.user_slot or 1,
        user_label=label,
        user_password=password,
        keys=result.keys,
    )


def full_admin_passwords(
    session: AdminSession,
    enabled_flags: list[bool],
    new_passwords: list[str],
) -> list[tuple[bool, str]]:
    """Kayıt için kullanıcı slot parolalarını birleştirir."""
    result: list[tuple[bool, str]] = []
    for index in range(3):
        enabled = enabled_flags[index] if index < len(enabled_flags) else False
        pwd = new_passwords[index] if index < len(new_passwords) else ""
        if enabled and not pwd and session.user_passwords:
            old_enabled, old_pwd = session.user_passwords[index]
            if old_enabled and old_pwd:
                pwd = old_pwd
        result.append((enabled, pwd))
    return result


def admin_permissions() -> UserPermissions:
    """Yönetici için tam yetki (UI kontrolü için)."""
    return UserPermissions(
        name="write",
        info1="write",
        info2="write",
        info3="write",
        info4="write",
        can_add_entry=True,
        can_delete_entry=True,
        can_save=True,
    )
