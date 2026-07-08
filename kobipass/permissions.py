"""
kobiPass izin kontrolü ve audit diff.
"""

from __future__ import annotations

from kobipass.i18n import tr
from kobipass.session import Session, UserSession
from kobipass.vault_model import (
    AuditEntry,
    FieldLevel,
    UserPermissions,
    VaultEntry,
    utc_now_iso,
)


def can_view(level: FieldLevel) -> bool:
    return level in ("read", "hidden_read", "write")


def can_edit(level: FieldLevel) -> bool:
    return level == "write"


def can_copy(level: FieldLevel) -> bool:
    return level in ("read", "hidden_read", "write")


def effective_permissions(session: Session, vault_perms: UserPermissions) -> UserPermissions:
    if getattr(session, "is_admin", False):
        from kobipass.session import admin_permissions

        return admin_permissions()
    return vault_perms


def field_label(field_name: str) -> str:
    if field_name == "name":
        return tr("field_name")
    if field_name == "info1":
        return tr("field_info1")
    if field_name.startswith("info") and field_name[4:].isdigit():
        number = int(field_name[4:])
        if number <= 4:
            return tr(f"field_info{number}")
        return tr("field_info_n", n=number)
    return field_name


def _entry_field_names(entry: VaultEntry) -> list[str]:
    names = ["name", "info1"]
    for index in range(2, entry.max_info_index() + 1):
        names.append(f"info{index}")
    return names


def diff_entries_for_audit(
    old_entries: list[VaultEntry],
    new_entries: list[VaultEntry],
    session: UserSession,
    permissions: UserPermissions,
) -> list[AuditEntry]:
    """Kullanıcı kaydında değişen alanları audit kaydına çevirir."""
    logs: list[AuditEntry] = []
    pair_count = max(len(old_entries), len(new_entries))

    for index in range(pair_count):
        old = old_entries[index] if index < len(old_entries) else VaultEntry(name="")
        new = new_entries[index] if index < len(new_entries) else VaultEntry(name="")
        entry_name = new.name or old.name or tr("audit_unknown_entry")

        field_names = set(_entry_field_names(old)) | set(_entry_field_names(new))
        for field_name in sorted(field_names, key=_field_sort_key):
            if field_name == "name":
                level = permissions.name
            elif field_name.startswith("info") and field_name[4:].isdigit():
                level = permissions.level_for_info_index(int(field_name[4:]))
            else:
                continue
            if not can_edit(level):
                continue
            old_val = old.field_value(field_name)
            new_val = new.field_value(field_name)
            if old_val == new_val:
                continue

            label = field_label(field_name)
            if field_name == "info2":
                summary = tr("audit_password_updated")
            else:
                summary = tr("audit_field_updated", field=label)

            logs.append(
                AuditEntry(
                    at=utc_now_iso(),
                    user_slot=session.user_slot,
                    user_label=session.user_label,
                    action="field_edit",
                    entry_name=entry_name,
                    field=field_name,
                    summary=summary,
                    old_value=old_val,
                    new_value=new_val,
                )
            )

    if logs:
        logs.append(
            AuditEntry(
                at=utc_now_iso(),
                user_slot=session.user_slot,
                user_label=session.user_label,
                action="vault_save",
                entry_name="",
                field="",
                summary=tr("audit_vault_saved"),
                old_value="",
                new_value="",
            )
        )
    return logs


def _field_sort_key(field_name: str) -> tuple[int, str]:
    if field_name == "name":
        return (0, field_name)
    if field_name.startswith("info") and field_name[4:].isdigit():
        return (1, f"{int(field_name[4:]):05d}")
    return (2, field_name)
