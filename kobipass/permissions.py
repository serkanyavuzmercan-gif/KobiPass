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
    is_password_audit_field,
    is_sensitive_audit_field,
    utc_now_iso,
)

__all__ = [
    "can_view",
    "can_edit",
    "can_copy",
    "diff_entries_for_audit",
    "effective_permissions",
    "field_label",
    "is_password_audit_field",
    "is_sensitive_audit_field",
    "mask_audit_value",
]


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


def mask_audit_value(value: str, field_name: str) -> str:
    if not value:
        return tr("audit_empty_value")
    if is_sensitive_audit_field(field_name):
        return tr("audit_masked_value")
    return value


def _detect_field_shift(old: VaultEntry, new: VaultEntry) -> tuple[str, int] | None:
    """Tek bir bilgi HÜCRESİNİN eklendiğini/silindiğini saptar.

    Bir hücre silinince sonraki tüm hücreler SOLA KAYAR. Konum bazlı fark bunu
    "VERİ2 şu oldu, VERİ3 boşaldı" gibi bir zincir olarak raporluyordu:
    kullanıcı böyle bir düzenleme yapmadığı için geçmiş yanıltıcı görünüyor,
    üstelik kayan değerler geçmişe yazılıyordu. Kaymayı tanıyıp TEK bir
    "hücre silindi/eklendi" kaydı düşürüyoruz.

    Döndürür: ("field_delete" | "field_add", 0 tabanlı hücre konumu) ya da None.
    """
    old_vals = old.info_values()
    new_vals = new.info_values()
    if len(new_vals) == len(old_vals) - 1:
        for k in range(len(old_vals)):
            if old_vals[:k] == new_vals[:k] and old_vals[k + 1 :] == new_vals[k:]:
                return ("field_delete", k)
    elif len(new_vals) == len(old_vals) + 1:
        for k in range(len(new_vals)):
            if new_vals[:k] == old_vals[:k] and new_vals[k + 1 :] == old_vals[k:]:
                return ("field_add", k)
    return None


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

    def record(action: str, entry_name: str, summary: str, field: str = "") -> None:
        logs.append(
            AuditEntry(
                at=utc_now_iso(),
                user_slot=session.user_slot or 0,
                user_label=session.user_label,
                action=action,
                entry_name=entry_name,
                field=field,
                summary=summary,
                old_value="",
                new_value="",
                tab_id=tab_id or "",
            )
        )

    def diff_pair(old: VaultEntry, new: VaultEntry) -> None:
        entry_name = display_name(new.name, old.name)
        # Hücre ekleme/silme: konum bazlı zincir yerine TEK kayıt.
        shift = _detect_field_shift(old, new)
        shifted_from = None
        if shift is not None and can_edit(permissions.info):
            action, position = shift
            cell = f"info{position + 1}"
            record(
                action,
                entry_name,
                tr(
                    "audit_field_added" if action == "field_add" else "audit_field_removed",
                    field=field_label(cell, vault),
                ),
                field=cell,
            )
            shifted_from = position

        field_names = set(_entry_field_names(old)) | set(_entry_field_names(new))
        for field_name in sorted(field_names, key=_field_sort_key):
            # Kaymadan ETKİLENEN konumlar zaten tek kayıtla anlatıldı.
            if (
                shifted_from is not None
                and field_name.startswith("info")
                and field_name[4:].isdigit()
                and int(field_name[4:]) - 1 >= shifted_from
            ):
                continue
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
                # Değer SAKLANMAZ. Arayüzde her değer hücresi maskelidir;
                # geçmişin onları çıplak taşıması hem tutarsız hem sızıntıydı.
                # Özet yalnızca gerçekten parola olan alanda "Şifre alanı" der.
                summary = (
                    tr("audit_password_updated")
                    if is_password_audit_field(field_name)
                    else tr("audit_field_updated", field=label)
                )
                stored_old = ""
                stored_new = ""
            elif field_name == "name":
                # Kayıt adı özel: "Kayıt" sütunu zaten yeni adı gösterdiği için
                # "<etiket> güncellendi" demek dairesel ve kafa karıştırıcıydı
                # (özellikle isim sütununa özel bir etiket verilmişse).
                summary = tr("audit_name_changed")
                stored_old = old_val
                stored_new = new_val
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
