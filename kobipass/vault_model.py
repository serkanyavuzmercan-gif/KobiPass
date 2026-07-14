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
# İzin şablonu alanları: İsim ve tüm bilgi alanları için tek 'Bilgiler'.
PERM_FIELDS = ("name", "info")
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
    # info1 (parola) en son ne zaman değişti — ISO 8601 UTC; boş = bilinmiyor.
    pw_updated_at: str = ""

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
        if self.pw_updated_at:
            data["pw_updated_at"] = self.pw_updated_at
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
            pw_updated_at=str(data.get("pw_updated_at", "")),
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
    """Tek bir alt kullanıcının izinleri.

    Yalnızca iki alan izni: 'İsim' ve 'Bilgiler' (1. bilgi dahil tüm bilgi
    alanları). Ayrıca kayıt ekleme / silme / kaydetme bayrakları.
    """

    name: FieldLevel = "read"
    info: FieldLevel = "read"  # info1, info2, ... hepsi ortak — varsayılan Görür
    can_add_entry: bool = False
    can_delete_entry: bool = False
    can_save: bool = True

    def copy(self) -> UserPermissions:
        return UserPermissions(
            name=self.name,
            info=self.info,
            can_add_entry=self.can_add_entry,
            can_delete_entry=self.can_delete_entry,
            can_save=self.can_save,
        )

    def can_mutate(self) -> bool:
        """Alan düzenleme veya kayıt ekleme/silme yetkisi var mı."""
        return (
            self.name == "write"
            or self.info == "write"
            or self.can_add_entry
            or self.can_delete_entry
        )

    def normalized(self) -> UserPermissions:
        """Kaydetme yetkisi bağımsız bir seçim değildir; doğrudan değişiklik
        yapma yetkisinden türetilir. Düzenleme/ekleme/silme yetkisi olan
        kullanıcı değişikliklerini kaydedebilir; yalnızca görüntüleyen
        kullanıcının kaydedecek bir değişikliği olmadığı için kaydedemez."""
        result = self.copy()
        result.can_save = result.can_mutate()
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "info": self.info,
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

        # Geriye uyumluluk: eski kasalar info1/info_rest tutar → tek 'info'ya indir.
        if "info" in data:
            info = level("info", "read")
        elif "info1" in data:
            info = level("info1", "read")
        else:
            info = level("info_rest", "read")

        return cls(
            name=level("name", "read"),
            info=info,
            can_add_entry=bool(data.get("can_add_entry", False)),
            can_delete_entry=bool(data.get("can_delete_entry", False)),
            can_save=bool(data.get("can_save", True)),
        ).normalized()

    def field_level(self, field_name: str) -> FieldLevel:
        if field_name == "name":
            return self.name
        if field_name == "info" or (
            field_name.startswith("info") and field_name[4:].isdigit()
        ):
            return self.info
        return "none"

    def level_for_info_index(self, info_index: int) -> FieldLevel:
        return self.info


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
    user_slot_permissions: list[UserPermissions] = field(default_factory=list)
    user_slot_labels: list[str] = field(
        default_factory=lambda: [
            f"Alt Kullanıcı {i}" for i in range(1, USER_SLOT_COUNT + 1)
        ]
    )
    field_labels: dict[str, str] = field(default_factory=dict)
    audit_log: list[AuditEntry] = field(default_factory=list)

    def permissions_for_slot(self, slot: int) -> UserPermissions:
        """1-based kullanıcı slot izni; yoksa ortak/legacy şablona düşer."""
        index = slot - 1
        if 0 <= index < len(self.user_slot_permissions):
            return self.user_slot_permissions[index]
        return self.user_permissions

    def set_slot_permissions(self, permissions: list[UserPermissions]) -> None:
        self.user_slot_permissions = [p.normalized() for p in permissions]
        if self.user_slot_permissions:
            self.user_permissions = self.user_slot_permissions[0].copy()

    def resolved_field_labels(self) -> dict[str, str]:
        result = dict(DEFAULT_FIELD_LABELS)
        for key, value in self.field_labels.items():
            if isinstance(key, str) and isinstance(value, str) and value.strip():
                result[key] = value.strip()
        return result

    def label_for(self, field_name: str) -> str:
        return field_label_for(field_name, self.field_labels)

    def to_dict(self) -> dict[str, Any]:
        slot_perms = self.user_slot_permissions or [self.user_permissions]
        return {
            "version": 3,
            "entries": [e.to_dict() for e in self.entries],
            "user_permissions": (
                slot_perms[0].to_dict() if slot_perms else self.user_permissions.to_dict()
            ),
            "user_slot_permissions": [p.to_dict() for p in slot_perms],
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
        legacy_perms = UserPermissions.from_dict(data.get("user_permissions", {}))
        labels = data.get("user_slot_labels")
        if not isinstance(labels, list) or not labels:
            labels = [f"Alt Kullanıcı {i}" for i in range(1, USER_SLOT_COUNT + 1)]
        else:
            labels = [str(x) for x in labels]
        raw_slot_perms = data.get("user_slot_permissions")
        slot_perms: list[UserPermissions] = []
        if isinstance(raw_slot_perms, list) and raw_slot_perms:
            slot_perms = [
                UserPermissions.from_dict(item if isinstance(item, dict) else {})
                for item in raw_slot_perms
            ]
        else:
            # Eski ortak şablon → her etiket için kopyala
            slot_perms = [legacy_perms.copy() for _ in labels] or [legacy_perms.copy()]
        while len(slot_perms) < len(labels):
            slot_perms.append(legacy_perms.copy())
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
            user_permissions=slot_perms[0].copy() if slot_perms else legacy_perms,
            user_slot_permissions=slot_perms,
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
