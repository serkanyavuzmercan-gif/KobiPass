"""
kobiPass vault veri modeli ve JSON serileştirme.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

FieldLevel = Literal["none", "read", "hidden_read", "write"]
FIELD_NAMES = ("name", "info1", "info2", "info3", "info4")
USER_SLOT_COUNT = 3
DEFAULT_FIELD_LABELS: dict[str, str] = {
    "name": "",
    "info1": "",
    "info2": "",
    "info3": "",
    "info4": "",
}


def field_label_for(field_name: str, custom: dict[str, str] | None = None) -> str:
    """Özel etiket varsa onu, yoksa boş (i18n katmanı doldurur) döner."""
    if custom and field_name in custom and custom[field_name].strip():
        return custom[field_name].strip()
    return ""


@dataclass
class VaultEntry:
    """Tek bir kasa kaydı — info1 sabit, info2+ dinamik liste."""

    name: str
    info1: str = ""
    more_infos: list[str] = field(default_factory=list)

    @property
    def info2(self) -> str:
        return self.more_infos[0] if len(self.more_infos) > 0 else ""

    @property
    def info3(self) -> str:
        return self.more_infos[1] if len(self.more_infos) > 1 else ""

    @property
    def info4(self) -> str:
        return self.more_infos[2] if len(self.more_infos) > 2 else ""

    def to_dict(self) -> dict[str, str]:
        data: dict[str, str] = {"name": self.name, "info1": self.info1}
        for index, value in enumerate(self.more_infos, start=2):
            data[f"info{index}"] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VaultEntry:
        more: list[str] = []
        index = 2
        while f"info{index}" in data:
            more.append(str(data.get(f"info{index}", "")))
            index += 1
        return cls(
            name=str(data.get("name", "")),
            info1=str(data.get("info1", "")),
            more_infos=more,
        )

    def field_value(self, field_name: str) -> str:
        if field_name == "name":
            return self.name
        if field_name == "info1":
            return self.info1
        if field_name.startswith("info") and field_name[4:].isdigit():
            number = int(field_name[4:])
            if number < 2:
                return ""
            slot = number - 2
            if slot < len(self.more_infos):
                return self.more_infos[slot]
        return ""

    def has_content(self) -> bool:
        if self.name.strip() or self.info1.strip():
            return True
        return any(value.strip() for value in self.more_infos)

    def max_info_index(self) -> int:
        return max(1, 1 + len(self.more_infos))


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
        return {
            "name": self.name,
            "info1": self.info1,
            "info2": self.info2,
            "info3": self.info3,
            "info4": self.info4,
            "can_add_entry": self.can_add_entry,
            "can_delete_entry": self.can_delete_entry,
            "can_save": self.can_save,
        }

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
        if field_name in FIELD_NAMES:
            return getattr(self, field_name, "none")
        if field_name.startswith("info") and field_name[4:].isdigit():
            number = int(field_name[4:])
            if number >= 5:
                return self.info4
        return "none"

    def level_for_info_index(self, info_index: int) -> FieldLevel:
        if info_index <= 1:
            return self.info1
        field_name = f"info{info_index}"
        return self.field_level(field_name)


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
        return {
            "at": self.at,
            "user_slot": self.user_slot,
            "user_label": self.user_label,
            "action": self.action,
            "entry_name": self.entry_name,
            "field": self.field,
            "summary": self.summary,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }

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
    field_labels: dict[str, str] = field(default_factory=dict)
    audit_log: list[AuditEntry] = field(default_factory=list)

    def resolved_field_labels(self) -> dict[str, str]:
        result = dict(DEFAULT_FIELD_LABELS)
        for key, value in self.field_labels.items():
            if isinstance(key, str) and isinstance(value, str) and value.strip():
                result[key] = value.strip()
        return result

    def label_for(self, field_name: str) -> str:
        return field_label_for(field_name, self.field_labels)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 2,
            "entries": [e.to_dict() for e in self.entries],
            "user_permissions": self.user_permissions.to_dict(),
            "user_slot_labels": list(self.user_slot_labels),
            "field_labels": {
                key: value
                for key, value in self.resolved_field_labels().items()
                if value
            },
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
        raw_field_labels = data.get("field_labels", {})
        field_labels: dict[str, str] = {}
        if isinstance(raw_field_labels, dict):
            for key, value in raw_field_labels.items():
                if str(key) in FIELD_NAMES or (
                    str(key).startswith("info") and str(key)[4:].isdigit()
                ):
                    text = str(value).strip()
                    if text:
                        field_labels[str(key)] = text
        audit = [
            AuditEntry.from_dict(item) for item in data.get("audit_log", [])
        ]
        return cls(
            entries=entries,
            user_permissions=perms,
            user_slot_labels=labels,
            field_labels=field_labels,
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
