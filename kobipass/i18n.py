"""
kobiPass arayüz çevirileri (TR / EN).
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

MIN_PASSWORD_LENGTH = 6

_STRINGS: dict[str, dict[str, str]] = {
    "tr": {
        "app_name": "KobiPass",
        "slogan": "parola kasası — yönetici ve kullanıcı rolleri",
        "role_admin": "Yönetici",
        "role_user": "Kullanıcı {slot}",
        "btn_open": "Dosya Aç",
        "btn_save": "Kaydet",
        "btn_clear": "Temizle",
        "btn_users": "Kullanıcılar & İzinler",
        "btn_audit": "Değişiklik Geçmişi",
        "btn_help": "Yardım",
        "btn_help_tip": "Kullanım ve şifreleme bilgisi",
        "btn_lang_tip": "Dili değiştir (Türkçe / English)",
        "btn_theme_tip": "Temayı değiştir (Karanlık / Aydınlık)",
        "hint_format": (
            "Kaydet ile .enc dosyası oluşturulur: 1 yönetici + en fazla 3 kullanıcı parolası "
            "belirlenir. Dosya Aç ile parolanızı girin; rol otomatik belirlenir."
        ),
        "status_no_records": "Kayıt yok",
        "status_records": "Kayıt: {count}",
        "status_unsaved": "Kaydedilmemiş",
        "status_file": "Dosya: {path}",
        "status_dirty": " • Değişiklik var",
        "status_role": "Oturum: {role}",
        "field_name": "İsim",
        "field_info1": "1. Bilgi",
        "field_info2": "2. Bilgi",
        "field_info3": "3. Bilgi",
        "field_info4": "4. Bilgi",
        "field_info_n": "{n}. Bilgi",
        "add_field_tip": "Yeni bilgi alanı ekle",
        "remove_field_tip": "Son eklenen bilgi alanını kaldır",
        "copy_tooltip": "{field} — panoya kopyala",
        "copied_tooltip": "Kopyalandı: {field}",
        "copy_notice": "Panoya kopyalandı: {field}",
        "copy_notice_empty": "Panoya kopyalandı",
        "eye_show": "Bilgileri göster (isim hariç)",
        "eye_hide": "Bilgileri gizle (isim hariç)",
        "btn_delete": "Sil",
        "btn_add_record": "+ Kayıt Ekle",
        "add_record_tip": "Yeni kayıt satırı ekle",
        "title_minimize": "Küçült",
        "title_maximize": "Büyüt",
        "title_restore": "Önceki boyuta getir",
        "title_close": "Kapat",
        "warn_title": "Uyarı",
        "warn_min_row": "En az bir kayıt satırı kalmalıdır.",
        "warn_locked": "Önce bir kasa dosyası açın veya kaydedin.",
        "discard_title": "Kaydedilmemiş değişiklikler",
        "discard_text": "Kaydedilmemiş değişiklikler var. Devam etmek istiyor musunuz?",
        "exit_title": "Çıkış",
        "exit_text": "Kaydedilmemiş değişiklikler var. Ne yapmak istersiniz?",
        "exit_save": "Kaydet",
        "exit_discard": "Kaydetmeden çık",
        "exit_cancel": "İptal",
        "err_no_records_title": "Kayıt yok",
        "err_no_records_save": "Kaydetmek için en az bir dolu kayıt girin.",
        "dlg_save_vault": "Kasa Dosyasını Kaydet",
        "dlg_open_vault": "Kasa Dosyası Aç",
        "filter_enc": "Şifreli Kasa (*.enc)",
        "filter_all": "Tüm Dosyalar (*.*)",
        "err_save_title": "Kayıt hatası",
        "saved_title": "Kaydedildi",
        "saved_text": "Kasa dosyası kaydedildi:\n{path}",
        "denied_title": "Erişim reddedildi",
        "denied_text": "Parola hatalı veya dosya bozuk. İçerik gösterilmiyor.",
        "file_err_title": "Dosya hatası",
        "opened_title": "Açıldı",
        "opened_text": "{count} kayıt yüklendi.",
        "setup_pwd_title": "Kasa Kurulumu",
        "setup_pwd_info": (
            "Yönetici parolası zorunludur (min. {min_len} karakter).\n"
            "En fazla 3 kullanıcı parolası tanımlayabilirsiniz; boş bırakılan slot devre dışı kalır."
        ),
        "admin_pwd_label": "Yönetici parolası:",
        "admin_pwd_repeat": "Yönetici tekrar:",
        "user_pwd_label": "Kullanıcı {n} parolası:",
        "user_pwd_repeat": "Kullanıcı {n} tekrar:",
        "perm_section": "Kullanıcı izinleri (tüm kullanıcılar için ortak)",
        "perm_none": "Göremez",
        "perm_read": "Görür",
        "perm_hidden_read": "Maskeli görür",
        "perm_write": "Düzenler",
        "pwd_label": "Parola:",
        "pwd_repeat_label": "Tekrar:",
        "pwd_placeholder": "Parola",
        "pwd_repeat_placeholder": "Parola tekrar",
        "show": "Göster",
        "hide": "Gizle",
        "pwd_too_short": "Parola en az {min_len} karakter olmalıdır.",
        "pwd_mismatch": "Parolalar eşleşmiyor.",
        "pwd_admin_required": "Yönetici parolası zorunludur.",
        "open_pwd_title": "Kasa Parolası",
        "open_pwd_label": "Dosya: {file}\nYönetici veya kullanıcı parolanızı girin:",
        "users_title": "Kullanıcılar & İzinler",
        "users_info": "Kullanıcı parolalarını ve ortak izin şablonunu düzenleyin. Kaydet ile kasaya yazılır.",
        "audit_title": "Değişiklik Geçmişi",
        "audit_empty": "Henüz kullanıcı değişikliği kaydı yok.",
        "audit_col_at": "Tarih",
        "audit_col_user": "Kullanıcı",
        "audit_col_entry": "Kayıt",
        "audit_col_field": "Alan",
        "audit_col_old": "Önceki",
        "audit_col_new": "Sonraki",
        "audit_col_summary": "Özet",
        "audit_empty_value": "(boş)",
        "audit_password_updated": "Şifre alanı güncellendi",
        "audit_field_updated": "{field} güncellendi",
        "audit_vault_saved": "Kasa kaydedildi",
        "audit_unknown_entry": "(yeni kayıt)",
        "help_title": "Yardım — KobiPass",
        "help_close": "Kapat",
        "about_title": "Güvenlik Protokolü ve Hakkında",
        "about_tab_security": "Güvenlik Protokolü",
        "about_tab_credits": "Açık Kaynak & Lisanslar",
        "security_badge": "🔒 AES-256 ile Korunuyor",
        "security_badge_tip": "Güvenlik Protokolünü ve Lisansları Gör",
        "btn_security": "🛡️ Güvenlik",
        "ok": "Tamam",
        "cancel": "İptal",
        "yes": "Evet",
        "no": "Hayır",
        "crypto.invalid_salt": "Geçersiz salt uzunluğu",
        "crypto.file_too_short": "Dosya çok kısa veya bozuk",
        "crypto.invalid_file": "Geçersiz KobiPass dosyası",
        "crypto.unsupported_version": "Desteklenmeyen dosya sürümü",
        "crypto.wrong_password": "Parola hatalı veya dosya bozuk",
        "crypto.corrupt_vault": "Kasa verisi bozuk",
        "crypto.invalid_wrap": "Geçersiz sarmalayıcı",
        "crypto.wrap_failed": "Sarmalayıcı oluşturulamadı",
        "crypto.invalid_dek": "Geçersiz veri anahtarı",
        "crypto.invalid_user_slots": "Geçersiz kullanıcı slot sayısı",
    },
    "en": {
        "app_name": "KobiPass",
        "slogan": "SMB password vault — admin and user roles",
        "role_admin": "Administrator",
        "role_user": "User {slot}",
        "btn_open": "Open File",
        "btn_save": "Save",
        "btn_clear": "Clear",
        "btn_users": "Users & Permissions",
        "btn_audit": "Change History",
        "btn_help": "Help",
        "btn_help_tip": "Usage and encryption information",
        "btn_lang_tip": "Switch language (Türkçe / English)",
        "btn_theme_tip": "Switch theme (Dark / Light)",
        "hint_format": (
            "Save creates a .enc file with 1 admin and up to 3 user passwords. "
            "Open File unlocks the vault; your role is detected automatically."
        ),
        "status_no_records": "No records",
        "status_records": "Records: {count}",
        "status_unsaved": "Unsaved",
        "status_file": "File: {path}",
        "status_dirty": " • Unsaved changes",
        "status_role": "Session: {role}",
        "field_name": "Name",
        "field_info1": "Info 1",
        "field_info2": "Info 2",
        "field_info3": "Info 3",
        "field_info4": "Info 4",
        "field_info_n": "Info {n}",
        "add_field_tip": "Add another info field",
        "remove_field_tip": "Remove the last added info field",
        "copy_tooltip": "{field} — copy to clipboard",
        "copied_tooltip": "Copied: {field}",
        "copy_notice": "Copied to clipboard: {field}",
        "copy_notice_empty": "Copied to clipboard",
        "eye_show": "Show fields (except name)",
        "eye_hide": "Hide fields (except name)",
        "btn_delete": "Delete",
        "btn_add_record": "+ Add Record",
        "add_record_tip": "Add a new record row",
        "title_minimize": "Minimize",
        "title_maximize": "Maximize",
        "title_restore": "Restore down",
        "title_close": "Close",
        "warn_title": "Warning",
        "warn_min_row": "At least one record row must remain.",
        "warn_locked": "Open or save a vault file first.",
        "discard_title": "Unsaved changes",
        "discard_text": "You have unsaved changes. Do you want to continue?",
        "exit_title": "Exit",
        "exit_text": "You have unsaved changes. What would you like to do?",
        "exit_save": "Save",
        "exit_discard": "Exit without saving",
        "exit_cancel": "Cancel",
        "err_no_records_title": "No records",
        "err_no_records_save": "Enter at least one filled record to save.",
        "dlg_save_vault": "Save Vault File",
        "dlg_open_vault": "Open Vault File",
        "filter_enc": "Encrypted Vault (*.enc)",
        "filter_all": "All Files (*.*)",
        "err_save_title": "Save error",
        "saved_title": "Saved",
        "saved_text": "Vault file saved:\n{path}",
        "denied_title": "Access denied",
        "denied_text": "Wrong password or corrupted file. Content is not shown.",
        "file_err_title": "File error",
        "opened_title": "Opened",
        "opened_text": "{count} record(s) loaded.",
        "setup_pwd_title": "Vault Setup",
        "setup_pwd_info": (
            "Admin password is required (min. {min_len} characters).\n"
            "You may define up to 3 user passwords; empty slots stay disabled."
        ),
        "admin_pwd_label": "Admin password:",
        "admin_pwd_repeat": "Admin repeat:",
        "user_pwd_label": "User {n} password:",
        "user_pwd_repeat": "User {n} repeat:",
        "perm_section": "User permissions (shared by all users)",
        "perm_none": "Hidden",
        "perm_read": "View",
        "perm_hidden_read": "Masked view",
        "perm_write": "Edit",
        "pwd_label": "Password:",
        "pwd_repeat_label": "Repeat:",
        "pwd_placeholder": "Password",
        "pwd_repeat_placeholder": "Repeat password",
        "show": "Show",
        "hide": "Hide",
        "pwd_too_short": "Password must be at least {min_len} characters.",
        "pwd_mismatch": "Passwords do not match.",
        "pwd_admin_required": "Admin password is required.",
        "open_pwd_title": "Vault Password",
        "open_pwd_label": "File: {file}\nEnter your admin or user password:",
        "users_title": "Users & Permissions",
        "users_info": "Edit user passwords and the shared permission template. Save vault to apply.",
        "audit_title": "Change History",
        "audit_empty": "No user change records yet.",
        "audit_col_at": "Date",
        "audit_col_user": "User",
        "audit_col_entry": "Record",
        "audit_col_field": "Field",
        "audit_col_old": "Previous",
        "audit_col_new": "New",
        "audit_col_summary": "Summary",
        "audit_empty_value": "(empty)",
        "audit_password_updated": "Password field updated",
        "audit_field_updated": "{field} updated",
        "audit_vault_saved": "Vault saved",
        "audit_unknown_entry": "(new record)",
        "help_title": "Help — KobiPass",
        "help_close": "Close",
        "about_title": "Security Protocol & About",
        "about_tab_security": "Security Protocol",
        "about_tab_credits": "Open Source & Licenses",
        "security_badge": "🔒 Protected with AES-256",
        "security_badge_tip": "View security protocol and licenses",
        "btn_security": "🛡️ Security",
        "ok": "OK",
        "cancel": "Cancel",
        "yes": "Yes",
        "no": "No",
        "crypto.invalid_salt": "Invalid salt length",
        "crypto.file_too_short": "File is too short or corrupted",
        "crypto.invalid_file": "Invalid KobiPass file",
        "crypto.unsupported_version": "Unsupported file version",
        "crypto.wrong_password": "Wrong password or corrupted file",
        "crypto.corrupt_vault": "Vault data is corrupted",
        "crypto.invalid_wrap": "Invalid key wrap",
        "crypto.wrap_failed": "Failed to create key wrap",
        "crypto.invalid_dek": "Invalid data encryption key",
        "crypto.invalid_user_slots": "Invalid user slot count",
    },
}


class I18n(QObject):
    """Uygulama dili yöneticisi."""

    language_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._lang = "tr"

    @property
    def lang(self) -> str:
        return self._lang

    def is_tr(self) -> bool:
        return self._lang == "tr"

    def toggle(self) -> None:
        self._lang = "en" if self._lang == "tr" else "tr"
        self.language_changed.emit()

    def t(self, key: str, **kwargs: object) -> str:
        table = _STRINGS.get(self._lang, _STRINGS["tr"])
        text = table.get(key, _STRINGS["tr"].get(key, key))
        if kwargs:
            return text.format(**kwargs)
        return text


i18n = I18n()


def tr(key: str, **kwargs: object) -> str:
    return i18n.t(key, **kwargs)


def crypto_message(key_or_text: str) -> str:
    if key_or_text.startswith("crypto."):
        return tr(key_or_text)
    return key_or_text
