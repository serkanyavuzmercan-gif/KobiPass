"""Unit tests for vault model, crypto, permissions, and export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kobipass.crypto import (
    AccessDeniedError,
    VERSION_ARGON2,
    VERSION_PBKDF2,
    build_vault_file,
    read_vault_file,
    try_unlock_vault,
    update_admin_wrap,
    verify_password_against_keys,
    write_vault_file,
    write_vault_file_updated,
)
from kobipass.export import export_vault_csv, export_vault_json
from kobipass.permissions import (
    can_edit,
    can_view,
    diff_entries_for_audit,
    is_sensitive_audit_field,
    mask_audit_value,
    view_only_permissions,
)
from kobipass.session import UserSession
from kobipass.vault_model import (
    KobiVault,
    UserPermissions,
    VaultEntry,
    vault_from_json_bytes,
    vault_to_json_bytes,
)


def test_vault_entry_dynamic_fields() -> None:
    entry = VaultEntry(name="A", info1="secret", more_infos=["x", "y"])
    assert entry.info2 == "x"
    assert entry.info3 == "y"
    assert entry.field_value("info2") == "x"
    assert entry.max_info_index() == 3
    restored = VaultEntry.from_dict(entry.to_dict())
    assert restored.more_infos == ["x", "y"]


def test_field_labels_roundtrip() -> None:
    vault = KobiVault(
        entries=[VaultEntry(name="n", info1="p")],
        field_labels={"name": "Başlık", "info1": "Parola"},
    )
    raw = vault_to_json_bytes(vault)
    loaded = vault_from_json_bytes(raw)
    assert loaded.label_for("name") == "Başlık"
    assert loaded.label_for("info1") == "Parola"


def test_per_slot_permissions_roundtrip() -> None:
    p1 = UserPermissions(name="read", info1="write")
    p2 = UserPermissions(name="none", info1="read").with_infos_level("read")
    vault = KobiVault(entries=[VaultEntry(name="n", info1="p")])
    vault.set_slot_permissions([p1, p2, UserPermissions()])
    vault.user_slot_usernames = ["ali", "veli", ""]
    vault.user_slot_labels = ["Ali", "Veli", "Kullanıcı 3"]
    loaded = vault_from_json_bytes(vault_to_json_bytes(vault))
    assert loaded.to_dict()["version"] == 3
    assert loaded.permissions_for_slot(1).info1 == "write"
    assert loaded.permissions_for_slot(2).name == "none"
    assert loaded.permissions_for_slot(2).infos_level == "read"
    assert loaded.user_slot_usernames[0] == "ali"
    legacy = {
        "version": 1,
        "entries": [],
        "user_permissions": UserPermissions(name="hidden_read", info1="none").to_dict(),
        "user_slot_labels": ["A", "B", "C"],
        "audit_log": [],
    }
    legacy_vault = KobiVault.from_dict(legacy)
    assert legacy_vault.permissions_for_slot(3).name == "hidden_read"


def test_build_and_unlock_argon2(tmp_path: Path) -> None:
    vault = KobiVault(entries=[VaultEntry(name="Site", info1="pass")])
    path = tmp_path / "v2.enc"
    write_vault_file(
        path,
        vault,
        "admin-secret",
        [(True, "user-one"), (False, ""), (False, "")],
        version=VERSION_ARGON2,
    )
    unlocked = read_vault_file(path, "admin-secret")
    assert unlocked.role == "admin"
    assert unlocked.keys.version == VERSION_ARGON2
    assert unlocked.vault.entries[0].name == "Site"

    user = read_vault_file(path, "user-one")
    assert user.role == "user"
    assert user.user_slot == 1

    with pytest.raises(AccessDeniedError):
        read_vault_file(path, "wrong")


def test_legacy_pbkdf2_roundtrip(tmp_path: Path) -> None:
    vault = KobiVault(entries=[VaultEntry(name="Legacy", info1="x")])
    blob = build_vault_file(
        vault,
        "admin-legacy",
        [(False, ""), (False, ""), (False, "")],
        version=VERSION_PBKDF2,
    )
    assert blob[4] == VERSION_PBKDF2
    unlocked = try_unlock_vault(blob, "admin-legacy")
    assert unlocked.keys.version == VERSION_PBKDF2
    assert unlocked.vault.entries[0].name == "Legacy"


def test_update_admin_wrap_and_verify(tmp_path: Path) -> None:
    vault = KobiVault(entries=[VaultEntry(name="A", info1="1")])
    path = tmp_path / "admin.enc"
    write_vault_file(
        path,
        vault,
        "old-admin",
        [(False, ""), (False, ""), (False, "")],
    )
    unlocked = read_vault_file(path, "old-admin")
    new_keys = update_admin_wrap(unlocked.keys, "new-admin")
    write_vault_file_updated(path, vault, new_keys)
    assert verify_password_against_keys(new_keys, "new-admin")
    assert not verify_password_against_keys(new_keys, "old-admin")
    again = read_vault_file(path, "new-admin")
    assert again.role == "admin"


def test_write_updated_preserves_version(tmp_path: Path) -> None:
    vault = KobiVault(entries=[VaultEntry(name="A", info1="1")])
    path = tmp_path / "keep.enc"
    write_vault_file(
        path,
        vault,
        "admin",
        [(True, "user"), (False, ""), (False, "")],
        version=VERSION_PBKDF2,
    )
    unlocked = read_vault_file(path, "admin")
    vault.entries.append(VaultEntry(name="B", info1="2"))
    new_keys = write_vault_file_updated(path, vault, unlocked.keys)
    assert new_keys.version == VERSION_PBKDF2
    assert read_vault_file(path, "user").vault.entries[-1].name == "B"


def test_view_only_permissions() -> None:
    perms = UserPermissions(name="write", info1="write", can_add_entry=True)
    locked = view_only_permissions(perms)
    assert locked.name == "read"
    assert locked.info1 == "read"
    assert locked.can_add_entry is False
    assert can_view(locked.info1)
    assert not can_edit(locked.info1)


def test_audit_masks_sensitive_fields(tmp_path: Path) -> None:
    vault = KobiVault(entries=[VaultEntry(name="A", info1="oldpass")])
    path = tmp_path / "audit.enc"
    write_vault_file(
        path,
        vault,
        "admin",
        [(True, "user1"), (False, ""), (False, "")],
    )
    unlocked = read_vault_file(path, "user1")
    session = UserSession(
        user_slot=1,
        user_label="U1",
        user_password="user1",
        keys=unlocked.keys,
    )
    old = [VaultEntry(name="A", info1="oldpass", more_infos=["note"])]
    new = [VaultEntry(name="A", info1="newpass", more_infos=["note2"])]
    perms = UserPermissions(
        name="write",
        info1="write",
        info2="write",
        info3="none",
        info4="none",
    )
    logs = diff_entries_for_audit(old, new, session, perms)
    field_logs = [item for item in logs if item.action == "field_edit"]
    info1_log = next(item for item in field_logs if item.field == "info1")
    assert info1_log.old_value == ""
    assert info1_log.new_value == ""
    assert is_sensitive_audit_field("info1")
    assert "•" in mask_audit_value("secret", "info1")


def test_export_json_and_csv(tmp_path: Path) -> None:
    vault = KobiVault(
        entries=[VaultEntry(name="Mail", info1="pw", more_infos=["url"])],
        field_labels={"name": "Hesap", "info1": "Parola"},
    )
    json_path = tmp_path / "out.json"
    csv_path = tmp_path / "out.csv"
    export_vault_json(vault, json_path)
    export_vault_csv(vault, csv_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["entries"][0]["name"] == "Mail"
    assert payload["field_labels"]["info1"] == "Parola"
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "Hesap" in csv_text
    assert "Mail" in csv_text
