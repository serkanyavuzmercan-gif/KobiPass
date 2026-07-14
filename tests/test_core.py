"""Unit tests for vault model, crypto, and permissions."""

from __future__ import annotations

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
    assert loaded.to_dict()["version"] == 2


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


def test_no_export_module() -> None:
    """Güvenlik: dışa aktarma özelliği kaldırıldı — geri gelmediğini doğrula."""
    import importlib.util

    assert importlib.util.find_spec("kobipass.export") is None


def test_backup_create_rotate_restore(tmp_path: Path, monkeypatch) -> None:
    """Yedekleme: kopya oluşur, rotasyon çalışır, geri yükleme birebir aynıdır."""
    import os
    import stat as stat_mod

    from kobipass import backup

    monkeypatch.setenv("KOBIPASS_BACKUP_DIR", str(tmp_path / "backups"))

    vault_file = tmp_path / "sirket.enc"
    vault_file.write_bytes(b"KBPS-encrypted-bytes-v1")

    created = backup.create_backup(vault_file)
    assert created is not None and created.is_file()
    assert created.read_bytes() == vault_file.read_bytes()

    # Rotasyon: BACKUP_KEEP üstü eski kopyalar silinir.
    for i in range(backup.BACKUP_KEEP + 4):
        vault_file.write_bytes(f"payload-{i}".encode())
        backup.create_backup(vault_file)
    backups = backup.find_backups(vault_file)
    assert len(backups) == backup.BACKUP_KEEP

    # Silinme + geri yükleme: en yeni yedek asıl konuma döner.
    latest_payload = vault_file.read_bytes()
    os.chmod(vault_file, 0o600)
    vault_file.unlink()
    assert not vault_file.exists()
    backup.restore_backup(backup.find_backups(vault_file)[0], vault_file)
    assert vault_file.read_bytes() == latest_payload

    # Geri yüklenen dosya salt-okunur işaretlenir; kayıt öncesi tekrar açılır.
    # (root altında os.access yanıltır — izin bitini doğrudan kontrol et)
    def _writable(p: Path) -> bool:
        return bool(stat_mod.S_IMODE(p.stat().st_mode) & stat_mod.S_IWUSR)

    assert not _writable(vault_file)
    backup.clear_read_only(vault_file)
    assert _writable(vault_file)


def test_password_generator_and_strength() -> None:
    """Üreteç güçlü/uzun; güç değerlendirme tutarlı."""
    from kobipass.password_tools import (
        generate_password,
        is_weak,
        strength_bucket,
    )

    pw = generate_password(20)
    assert len(pw) == 20
    assert strength_bucket(pw) == "strong"
    assert is_weak("123456")
    assert not is_weak(pw)
    # Sadece rakam seçilince bile en az o kadar uzunluk ve rakam havuzu.
    digits_only = generate_password(12, use_upper=False, use_lower=False, use_symbols=False)
    assert len(digits_only) == 12


def test_password_age_roundtrip() -> None:
    """pw_updated_at kaydedilir/okunur; humanize gün hesaplar."""
    from kobipass.password_tools import age_days
    from kobipass.vault_model import VaultEntry

    e = VaultEntry(name="A", info1="x", pw_updated_at="2026-01-01T00:00:00Z")
    restored = VaultEntry.from_dict(e.to_dict())
    assert restored.pw_updated_at == "2026-01-01T00:00:00Z"
    assert age_days("2026-01-01T00:00:00Z") is not None
    assert age_days("") is None
    # Damgasız kayıt geriye dönük uyumlu (eski dosyalar).
    assert VaultEntry.from_dict({"name": "B", "info1": "y"}).pw_updated_at == ""


def test_password_report_flags_weak_and_reused() -> None:
    from kobipass.ui.password_report_dialog import analyze_vault
    from kobipass.vault_model import KobiVault, VaultEntry

    vault = KobiVault(entries=[
        VaultEntry(name="Strong", info1="Xy9#kLmn20!q"),
        VaultEntry(name="Weak", info1="123456"),
        VaultEntry(name="Dup1", info1="same-pw-x"),
        VaultEntry(name="Dup2", info1="same-pw-x"),
    ])
    findings = analyze_vault(vault)
    names = {f["name"] for f in findings}
    assert "Strong" not in names
    assert "Weak" in names
    assert all(f["reused"] for f in findings if f["name"].startswith("Dup"))


def test_atomic_write_roundtrip(tmp_path: Path) -> None:
    """Atomik yazım sonrası dosya okunur ve geçici .tmp kalmaz."""
    from kobipass.vault_model import KobiVault, VaultEntry

    vault = KobiVault(entries=[VaultEntry(name="A", info1="secret")])
    path = tmp_path / "atomic.enc"
    write_vault_file(path, vault, "admin-pass", [(False, ""), (False, ""), (False, "")])
    assert path.exists()
    assert not list(tmp_path.glob("*.tmp"))
    assert read_vault_file(path, "admin-pass").vault.entries[0].info1 == "secret"
