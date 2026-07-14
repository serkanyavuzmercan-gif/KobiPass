"""
Yönetici: kullanıcı parolaları, alan etiketleri ve ortak izin şablonu.

İki sütunlu düzen — solda yönetici parolası + kullanıcı kartları,
sağda izin tablosu + genel yetkiler + alan etiketleri. Tüm parola
kutularında görünür/gizli göz düğmesi vardır.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import MIN_PASSWORD_LENGTH, tr
from kobipass.resources import app_icon
from kobipass.ui.icons import icon_eye, icon_eye_off
from kobipass.ui.strength import attach_strength_label
from kobipass.vault_model import KobiVault, PERM_FIELDS


def _password_edit(placeholder: str = "") -> QLineEdit:
    """Sağ kenarında göz düğmesi olan parola kutusu."""
    edit = QLineEdit()
    edit.setEchoMode(QLineEdit.EchoMode.Password)
    if placeholder:
        edit.setPlaceholderText(placeholder)

    action = edit.addAction(icon_eye_off(), QLineEdit.ActionPosition.TrailingPosition)
    action.setToolTip(tr("show"))

    def toggle() -> None:
        hidden = edit.echoMode() == QLineEdit.EchoMode.Password
        edit.setEchoMode(
            QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password
        )
        action.setIcon(icon_eye() if hidden else icon_eye_off())
        action.setToolTip(tr("hide") if hidden else tr("show"))

    action.triggered.connect(toggle)
    return edit


class UserAdminDialog(QDialog):
    def __init__(
        self,
        vault: KobiVault,
        enabled_flags: list[bool],
        parent: QWidget | None = None,
        *,
        require_admin_current: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("users_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setObjectName("userAdminDialog")
        self.setMinimumSize(900, 600)
        self.resize(940, 640)
        self._vault = vault
        self._enabled_flags = list(enabled_flags)
        self._passwords_changed = False
        self._require_admin_current = require_admin_current
        self._result: dict | None = None

        outer = QVBoxLayout(self)
        outer.setSpacing(10)

        info = QLabel(tr("users_info"))
        info.setWordWrap(True)
        outer.addWidget(info)

        perms = vault.user_permissions
        columns = QHBoxLayout()
        columns.setSpacing(14)

        # ── SOL sütun: Alt Kullanıcılar (kartlar + ekle) + Genel yetkiler ────
        left = QVBoxLayout()
        left.setSpacing(10)

        users_group = QGroupBox(tr("users_section"))
        users_group_layout = QVBoxLayout(users_group)
        users_group_layout.setContentsMargins(10, 8, 10, 10)
        users_group_layout.setSpacing(8)

        self._slots_host = QWidget()
        self._slots_host.setObjectName("slotsHost")
        self._slots_layout = QVBoxLayout(self._slots_host)
        self._slots_layout.setContentsMargins(0, 0, 0, 0)
        self._slots_layout.setSpacing(10)
        self._slots_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        slots_scroll = QScrollArea()
        slots_scroll.setWidgetResizable(True)
        slots_scroll.setFrameShape(QFrame.Shape.NoFrame)
        slots_scroll.setWidget(self._slots_host)
        slots_scroll.setMinimumHeight(300)  # ~3 kart; fazlası kaydırılır
        # Viewport'un varsayılan beyaz zeminini kaldır (Windows'ta görünüyordu).
        slots_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        slots_scroll.viewport().setStyleSheet("background: transparent;")
        users_group_layout.addWidget(slots_scroll, 1)

        self._add_user_btn = QPushButton(tr("add_user_btn"))
        self._add_user_btn.setObjectName("addRecordBtn")
        self._add_user_btn.clicked.connect(lambda: self._add_slot_card())
        users_group_layout.addWidget(
            self._add_user_btn, 0, Qt.AlignmentFlag.AlignLeft
        )
        left.addWidget(users_group, 1)

        # Genel yetkiler — alt kullanıcı odaklı, kartların altında.
        flags_group = QGroupBox(tr("perm_flags_section"))
        flags_layout = QVBoxLayout(flags_group)
        self._can_add_box = QCheckBox(tr("perm_can_add"))
        self._can_add_box.setChecked(perms.can_add_entry)
        self._can_delete_box = QCheckBox(tr("perm_can_delete"))
        self._can_delete_box.setChecked(perms.can_delete_entry)
        self._can_save_box = QCheckBox(tr("perm_can_save"))
        self._can_save_box.setChecked(perms.can_save)
        for box in (self._can_add_box, self._can_delete_box, self._can_save_box):
            flags_layout.addWidget(box)
        left.addWidget(flags_group)

        columns.addLayout(left, 3)

        # Başta yalnızca MEVCUT (etkin) alt kullanıcılar görünür; hiç yoksa
        # sadece "Alt Kullanıcı Ekle" butonu kalır. Devre dışı slotlar gizli.
        self._slot_cards: list[dict] = []
        self._original_count = len(self._enabled_flags)
        for n in range(self._original_count):
            if not self._enabled_flags[n]:
                continue
            label = (
                vault.user_slot_labels[n]
                if n < len(vault.user_slot_labels)
                else ""
            )
            self._add_slot_card(orig_index=n, enabled=True, label=label)

        # ── SAĞ sütun: yönetici parolası + alan izinleri (İsim / Bilgiler) ───
        right = QVBoxLayout()
        right.setSpacing(10)

        admin_group = QGroupBox(tr("admin_change_section"))
        admin_form = QFormLayout(admin_group)
        admin_info = QLabel(tr("admin_change_info"))
        admin_info.setWordWrap(True)
        admin_form.addRow(admin_info)
        self._admin_current = _password_edit()
        self._admin_new = _password_edit()
        self._admin_new_repeat = _password_edit()
        admin_form.addRow(tr("admin_pwd_current"), self._admin_current)
        admin_form.addRow(tr("admin_pwd_new"), self._admin_new)
        admin_form.addRow("", attach_strength_label(self._admin_new))
        admin_form.addRow(tr("admin_pwd_new_repeat"), self._admin_new_repeat)
        right.addWidget(admin_group)

        perm_group = QGroupBox(tr("perm_section"))
        perm_layout = QGridLayout(perm_group)
        perm_layout.setColumnStretch(1, 1)
        levels = [
            ("perm_none", "none"),
            ("perm_read", "read"),
            ("perm_hidden_read", "hidden_read"),
            ("perm_write", "write"),
        ]
        self._perm_combos: dict[str, QComboBox] = {}
        for row, field_name in enumerate(PERM_FIELDS):
            perm_layout.addWidget(QLabel(tr(f"field_{field_name}")), row, 0)
            combo = QComboBox()
            for label_key, value in levels:
                combo.addItem(tr(label_key), value)
            idx = combo.findData(perms.field_level(field_name))
            if idx >= 0:
                combo.setCurrentIndex(idx)
            self._perm_combos[field_name] = combo
            perm_layout.addWidget(combo, row, 1)
        right.addWidget(perm_group)

        right.addStretch()
        columns.addLayout(right, 2)
        outer.addLayout(columns, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText(tr("ok"))
        if cancel_btn:
            cancel_btn.setText(tr("cancel"))

    def _add_slot_card(
        self, *, orig_index: int | None = None, enabled: bool = True, label: str = ""
    ) -> None:
        """Bir 'Alt Kullanıcı' kartı ekler. orig_index: mevcut slotun konumu
        (None = yeni kullanıcı, kaydederken sona eklenir)."""
        n = len(self._slot_cards) + 1  # görünen sıra numarası
        card = QFrame()
        card.setObjectName("userSlotCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(6)

        header = QHBoxLayout()
        enabled_box = QCheckBox(tr("user_pwd_label", n=n))
        enabled_box.setChecked(enabled)
        header.addWidget(enabled_box)
        header.addStretch()
        remove_btn = QPushButton("×")
        remove_btn.setObjectName("slotRemoveBtn")
        remove_btn.setFixedSize(26, 26)
        remove_btn.setToolTip(tr("remove_user_tip"))
        header.addWidget(remove_btn)
        outer.addLayout(header)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(6)
        label_edit = QLineEdit()
        label_edit.setText(label or tr("user_default_label", n=n))
        p1 = _password_edit(tr("pwd_placeholder"))
        p2 = _password_edit(tr("pwd_repeat_placeholder"))
        form.addRow(tr("field_name"), label_edit)
        form.addRow(tr("pwd_label"), p1)
        form.addRow(tr("pwd_repeat_label"), p2)
        outer.addLayout(form)

        def apply(checked: bool) -> None:
            for w in (label_edit, p1, p2):
                w.setEnabled(checked)

        enabled_box.toggled.connect(apply)
        apply(enabled_box.isChecked())

        entry = {
            "orig_index": orig_index,
            "enabled": enabled_box,
            "label": label_edit,
            "p1": p1,
            "p2": p2,
            "card": card,
        }
        remove_btn.clicked.connect(lambda: self._remove_slot_card(entry))

        self._slots_layout.addWidget(card)
        self._slot_cards.append(entry)

    def _remove_slot_card(self, entry: dict) -> None:
        """Kartı kaldırır; mevcut alt kullanıcıysa kaydederken devre dışı kalır."""
        if entry not in self._slot_cards:
            return
        self._slot_cards.remove(entry)
        entry["card"].setParent(None)
        entry["card"].deleteLater()
        # Kalan kartların başlık numaralarını güncelle.
        for pos, card in enumerate(self._slot_cards, start=1):
            card["enabled"].setText(tr("user_pwd_label", n=pos))

    def _warn(self, message: str) -> None:
        """Uyarıyı sayfanın altında değil, ekranda popup olarak gösterir."""
        from kobipass.ui.dialogs import show_error

        show_error(self, tr("warn_title"), message)

    def _on_accept(self) -> None:
        from kobipass.vault_model import UserPermissions

        admin_current = self._admin_current.text()
        admin_new = self._admin_new.text()
        admin_repeat = self._admin_new_repeat.text()
        if admin_new or admin_repeat:
            if self._require_admin_current and not admin_current:
                self._warn(tr("pwd_admin_required"))
                return
            if len(admin_new) < MIN_PASSWORD_LENGTH:
                self._warn(tr("pwd_too_short", min_len=MIN_PASSWORD_LENGTH))
                return
            if admin_new != admin_repeat:
                self._warn(tr("pwd_mismatch"))
                return

        # Mevcut slot indekslerini koru: boş parola = eski sarmalayıcı korunur.
        # Taban liste (tüm eski slotlar devre dışı); kartlar yerlerine yazılır.
        total = self._original_count
        user_passwords: list[tuple[bool, str]] = [(False, "")] * total
        slot_labels: list[str] = [
            (
                self._vault.user_slot_labels[i]
                if i < len(self._vault.user_slot_labels)
                else tr("user_default_label", n=i + 1)
            )
            for i in range(total)
        ]
        new_passwords: list[tuple[bool, str]] = []
        new_labels: list[str] = []

        for pos, card in enumerate(self._slot_cards, start=1):
            enabled = card["enabled"].isChecked()
            pwd1 = card["p1"].text()
            pwd2 = card["p2"].text()
            label = card["label"].text().strip() or tr("user_default_label", n=pos)
            if enabled and (pwd1 or pwd2):
                if len(pwd1) < MIN_PASSWORD_LENGTH:
                    self._warn(tr("pwd_too_short", min_len=MIN_PASSWORD_LENGTH))
                    return
                if pwd1 != pwd2:
                    self._warn(tr("pwd_mismatch"))
                    return
                entry_pw = (True, pwd1)
                self._passwords_changed = True
            elif enabled:
                entry_pw = (True, "")
            else:
                entry_pw = (False, "")

            oi = card["orig_index"]
            if oi is not None and 0 <= oi < total:
                user_passwords[oi] = entry_pw
                slot_labels[oi] = label
            else:
                # Yeni kart: parola girilmediyse boş slot oluşturma.
                if not (pwd1 or pwd2):
                    continue
                new_passwords.append(entry_pw)
                new_labels.append(label)

        user_passwords.extend(new_passwords)
        slot_labels.extend(new_labels)

        perms = UserPermissions(
            name=self._perm_combos["name"].currentData(),
            info=self._perm_combos["info"].currentData(),
            can_add_entry=self._can_add_box.isChecked(),
            can_delete_entry=self._can_delete_box.isChecked(),
            can_save=self._can_save_box.isChecked(),
        )
        new_enabled = [enabled for enabled, _ in user_passwords]
        changed = (
            bool(admin_new)
            or self._passwords_changed
            or perms.to_dict() != self._vault.user_permissions.to_dict()
            or slot_labels != list(self._vault.user_slot_labels)
            or new_enabled != list(self._enabled_flags)
        )
        self._result = {
            "user_passwords": user_passwords,
            "permissions": perms,
            "passwords_changed": self._passwords_changed,
            "user_slot_labels": slot_labels,
            "admin_current": admin_current,
            "admin_new": admin_new if admin_new else None,
            "changed": changed,
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result
