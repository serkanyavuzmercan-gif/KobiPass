"""
kobiPass izin kontrolü ve audit diff.
"""

from __future__ import annotations

from kobipass.i18n import tr
from kobipass.session import Session, UserSession
from kobipass.vault_model import (
    AuditEntry,
    FieldLevel,
    KobiVault,
    UserPermissions,
    VaultEntry,
    utc_now_iso,
)

SENSITIVE_AUDIT_FIELDS = frozenset({"info1"})


def can_view(level: FieldLevel) -> bool:
    return level in ("read", "hidden_read", "write")


def can_edit(level: FieldLevel) -> bool:
    return level == "write"


def can_copy(level: FieldLevel) -> bool:
    """Alanın değeri panoya alınabilir mi?

    'hidden_read' (Maskeli görüntüleyebilir) BİLEREK dışarıda: o seviyede
    parola asla açığa çıkarılmaz — göz düğmesi kapalıdır ve echo modu zorla
    maskede tutulur. Kopyala düğmesi etkin bırakılınca aynı satırdaki iki
    düğme birbirini çürütüyor, tek tıkla açık metin panoya gidiyordu.
    """
    return level in ("read", "write")


def effective_permissions(session: Session, vault: KobiVault) -> UserPermissions:
    if getattr(session, "is_admin", False):
        from kobipass.session import admin_permissions

        return admin_permissions()
    slot = getattr(session, "user_slot", None) or 1
    return vault.permissions_for_slot(int(slot))


def field_label(field_name: str, vault: KobiVault | None = None) -> str:
    if vault is not None:
        custom = vault.label_for(field_name)
        if custom:
            return custom
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


def is_sensitive_audit_field(field_name: str) -> bool:
    return field_name in SENSITIVE_AUDIT_FIELDS or field_name == "info1"


def mask_audit_value(value: str, field_name: str) -> str:
    if not value:
        return tr("audit_empty_value")
    if is_sensitive_audit_field(field_name):
        return tr("audit_masked_value")
    return value


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
    vault: KobiVault | None = None,
    *,
    tab_id: str | None = None,
    include_save_marker: bool = True,
) -> list[AuditEntry]:
    """Kullanıcı kaydında değişen alanları audit kaydına çevirir.

    Kayıtlar İNDEKSE göre değil KİMLİĞE (uid) göre eşleştirilir; böylece bir
    yeniden sıralama, taşınan her satırı sahte 'değişti' saymaz. Yalnızca
    gerçek alan düzenlemeleri, eklemeler ve silmeler kaydedilir; sıra değişimi
    ayrı ve tek bir 'sıra değiştirildi' kaydıyla belirtilir.

    ``tab_id`` üretilen her kayda damgalanır. Şifreleme katmanı buna bakarak
    GİZLİ sekmelerin audit kayıtlarını AEK bloğuna, normal sekmelerinkini ana
    (DEK) gövdeye yazar; damga olmadan gizli kayıt adları ve bilgi alanları
    alt kullanıcının okuyabildiği gövdeye sızıyordu.
    """
    logs: list[AuditEntry] = []
    old_by_uid = {e.uid: e for e in old_entries}
    new_by_uid = {e.uid: e for e in new_entries}
    empty = VaultEntry(name="")
    if tab_id is None:
        tab_id = vault.active_tab().id if vault is not None else ""

    def display_name(*candidates: str) -> str:
        """Kayıt adı: adı GÖREMEYEN kullanıcının geçmişinde de görünmesin."""
        if not can_view(permissions.name):
            return tr("audit_hidden_entry")
        for value in candidates:
            if value:
                return value
        return tr("audit_unknown_entry")

    def record(action: str, entry_name: str, summary: str) -> None:
        logs.append(
            AuditEntry(
                at=utc_now_iso(),
                user_slot=session.user_slot or 0,
                user_label=session.user_label,
                action=action,
                entry_name=entry_name,
                field="",
                summary=summary,
                old_value="",
                new_value="",
                tab_id=tab_id or "",
            )
        )

    def diff_pair(old: VaultEntry, new: VaultEntry) -> None:
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

            label = field_label(field_name, vault)
            if is_sensitive_audit_field(field_name):
                summary = tr("audit_password_updated")
                stored_old = ""
                stored_new = ""
            else:
                summary = tr("audit_field_updated", field=label)
                stored_old = old_val
                stored_new = new_val

            logs.append(
                AuditEntry(
                    at=utc_now_iso(),
                    user_slot=session.user_slot or 0,
                    user_label=session.user_label,
                    action="field_edit",
                    entry_name=entry_name,
                    field=field_name,
                    summary=summary,
                    old_value=stored_old,
                    new_value=stored_new,
                    tab_id=tab_id or "",
                )
            )

    # Eklenen + düzenlenen kayıtlar (yeni listedeki sırayla).
    for new in new_entries:
        previous = old_by_uid.get(new.uid)
        diff_pair(previous if previous is not None else empty, new)
        # Kaydın kendisinin EKLENMESİ ayrı bir olaydır. Eskiden yalnızca alan
        # farkları üretiliyordu; alan yazma yetkisi olmayan ama ekleme yetkisi
        # olan kullanıcının eklediği kayıt geçmişte HİÇ görünmüyordu.
        if previous is None and permissions.can_add_entry:
            record("entry_add", display_name(new.name), tr("audit_entry_added"))
    # Silinen kayıtlar (eski listede olup yenide olmayan).
    for old in old_entries:
        if old.uid not in new_by_uid:
            diff_pair(old, empty)
            # Aynı boşluk silmede daha ağırdı: can_delete_entry=True ama tüm
            # alanlar salt-okunur olan kullanıcı kaydı kasadan siliyor, geçmişe
            # tek satır bile düşmüyordu (vault_save kaydı bile üretilmiyordu).
            if permissions.can_delete_entry:
                record(
                    "entry_delete", display_name(old.name), tr("audit_entry_deleted")
                )

    # Sıra değişimi: yalnızca her iki listede de bulunan kayıtların göreli
    # sırası değiştiyse tek bir kayıt düş.
    old_order = [e.uid for e in old_entries if e.uid in new_by_uid]
    new_order = [e.uid for e in new_entries if e.uid in old_by_uid]
    if old_order and old_order != new_order:
        record("reorder", "", tr("audit_reordered"))

    # Çok sekmeli kayıtta her sekme için ayrı fark alınır; "Kasa kaydedildi"
    # satırı tek olsun diye çağıran taraf onu kapatabilir.
    if logs and include_save_marker:
        record("vault_save", "", tr("audit_vault_saved"))
    return logs


def _field_sort_key(field_name: str) -> tuple[int, str]:
    if field_name == "name":
        return (0, field_name)
    if field_name.startswith("info") and field_name[4:].isdigit():
        return (1, f"{int(field_name[4:]):05d}")
    return (2, field_name)
