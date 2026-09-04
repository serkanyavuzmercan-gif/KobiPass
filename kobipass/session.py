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


@dataclass
class UserSession:
    user_slot: int
    user_label: str
    user_password: str
    keys: VaultFileKeys

    @property
    def is_admin(self) -> bool:
        return False


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


def admin_permissions() -> UserPermissions:
    """Yönetici için tam yetki (UI kontrolü için)."""
    return UserPermissions(
        name="write",
        info="write",
        can_add_entry=True,
        can_delete_entry=True,
        can_save=True,
    )
