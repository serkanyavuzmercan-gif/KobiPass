"""
kobiPass vault veri modeli ve JSON serileştirme.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

FieldLevel = Literal["none", "read", "hidden_read", "write"]
FIELD_NAMES = ("name", "info1", "info2", "info3", "info4")
USER_SLOT_COUNT = 3


@dataclass
class VaultEntry:
    """Tek bir kasa kaydı."""

    name: str
    info1: str = ""
    info2: str = ""
    info3: str = ""
    info4: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VaultEntry:
        return cls(
            name=str(data.get("name", "")),
            info1=str(data.get("info1", "")),
            info2=str(data.get("info2", "")),
            info3=str(data.get("info3", "")),
            info4=str(data.get("info4", "")),
        )

    def field_value(self, field_name: str) -> str:
        return str(getattr(self, field_name, ""))


@dataclass
class UserPermissions:
    """Tüm kullanıcılar için ortak izin şablonu."""

    name: FieldLevel = "read"
    info1: FieldLevel = "write"
    info2: FieldLevel = "hidden_read"
    info3: FieldLevel = "none"
    info4: FieldLevel = "none"
    can_add_entry: bool = False
    can_delete_entry: bool = False
    can_save: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserPermissions:
        def level(key: str, default: FieldLevel) -> FieldLevel:
            value = str(data.get(key, default))
            if value in ("none", "read", "hidden_read", "write"):
                return value  # type: ignore[return-value]
            return default

        return cls(
            name=level("name", "read"),
            info1=level("info1", "write"),
            info2=level("info2", "hidden_read"),
            info3=level("info3", "none"),
            info4=level("info4", "none"),
            can_add_entry=bool(data.get("can_add_entry", False)),
            can_delete_entry=bool(data.get("can_delete_entry", False)),
            can_save=bool(data.get("can_save", True)),
        )

    def field_level(self, field_name: str) -> FieldLevel:
        return getattr(self, field_name, "none")


@dataclass
class AuditEntry:
    """Kullanıcı değişiklik kaydı."""

    at: str
    user_slot: int
    user_label: str
    action: str
    entry_name: str
    field: str
    summary: str
    old_value: str = ""
    new_value: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEntry:
        return cls(
            at=str(data.get("at", "")),
            user_slot=int(data.get("user_slot", 0)),
            user_label=str(data.get("user_label", "")),
            action=str(data.get("action", "")),
            entry_name=str(data.get("entry_name", "")),
            field=str(data.get("field", "")),
            summary=str(data.get("summary", "")),
            old_value=str(data.get("old_value", "")),
            new_value=str(data.get("new_value", "")),
        )


@dataclass
class KobiVault:
    """Şifrelenmiş vault gövdesinin JSON içeriği."""

    entries: list[VaultEntry] = field(default_factory=list)
    user_permissions: UserPermissions = field(default_factory=UserPermissions)
    user_slot_labels: list[str] = field(
        default_factory=lambda: [f"Kullanıcı {i}" for i in range(1, USER_SLOT_COUNT + 1)]
    )
    audit_log: list[AuditEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "entries": [e.to_dict() for e in self.entries],
            "user_permissions": self.user_permissions.to_dict(),
            "user_slot_labels": list(self.user_slot_labels),
            "audit_log": [a.to_dict() for a in self.audit_log],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KobiVault:
        entries = [VaultEntry.from_dict(item) for item in data.get("entries", [])]
        perms = UserPermissions.from_dict(data.get("user_permissions", {}))
        labels = data.get("user_slot_labels")
        if not isinstance(labels, list) or len(labels) != USER_SLOT_COUNT:
            labels = [f"Kullanıcı {i}" for i in range(1, USER_SLOT_COUNT + 1)]
        else:
            labels = [str(x) for x in labels]
        audit = [
            AuditEntry.from_dict(item) for item in data.get("audit_log", [])
        ]
        return cls(
            entries=entries,
            user_permissions=perms,
            user_slot_labels=labels,
            audit_log=audit,
        )


def vault_to_json_bytes(vault: KobiVault) -> bytes:
    return json.dumps(vault.to_dict(), ensure_ascii=False).encode("utf-8")


def vault_from_json_bytes(data: bytes) -> KobiVault:
    raw = json.loads(data.decode("utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Geçersiz vault formatı")
    return KobiVault.from_dict(raw)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
