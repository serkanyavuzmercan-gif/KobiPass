"""
Yönetici: kullanıcı parolaları, alan etiketleri ve ortak izin şablonu.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import MIN_PASSWORD_LENGTH, tr
from kobipass.resources import app_icon
from kobipass.vault_model import FIELD_NAMES, KobiVault, USER_SLOT_COUNT


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
        self.setMinimumWidth(560)
        self._vault = vault
        self._enabled_flags = list(enabled_flags)
        self._passwords_changed = False
        self._require_admin_current = require_admin_current
        self._result: dict | None = None

        layout = QVBoxLayout(self)
        info = QLabel(tr("users_info"))
        info.setWordWrap(True)
        layout.addWidget(info)

        admin_group = QGroupBox(tr("admin_change_section"))
        admin_form = QFormLayout(admin_group)
        admin_info = QLabel(tr("admin_change_info"))
        admin_info.setWordWrap(True)
        admin_form.addRow(admin_info)
        self._admin_current = QLineEdit()
        self._admin_current.setEchoMode(QLineEdit.EchoMode.Password)
        self._admin_new = QLineEdit()
        self._admin_new.setEchoMode(QLineEdit.EchoMode.Password)
        self._admin_new_repeat = QLineEdit()
        self._admin_new_repeat.setEchoMode(QLineEdit.EchoMode.Password)
        admin_form.addRow(tr("admin_pwd_current"), self._admin_current)
        admin_form.addRow(tr("admin_pwd_new"), self._admin_new)
        admin_form.addRow(tr("admin_pwd_new_repeat"), self._admin_new_repeat)
        layout.addWidget(admin_group)

        pwd_group = QGroupBox(tr("users_title"))
        pwd_form = QFormLayout(pwd_group)
        self._enabled_boxes: list[QCheckBox] = []
        self._user_fields: list[tuple[QLineEdit, QLineEdit]] = []
        self._label_edits: list[QLineEdit] = []
        for n in range(USER_SLOT_COUNT):
            enabled = QCheckBox(tr("user_pwd_label", n=n + 1))
            enabled.setChecked(
                self._enabled_flags[n] if n < len(self._enabled_flags) else False
            )
            self._enabled_boxes.append(enabled)
            label_edit = QLineEdit()
            label_edit.setText(
                vault.user_slot_labels[n]
                if n < len(vault.user_slot_labels)
                else f"Kullanıcı {n + 1}"
            )
            self._label_edits.append(label_edit)
            p1 = QLineEdit()
            p1.setEchoMode(QLineEdit.EchoMode.Password)
            p1.setPlaceholderText(tr("pwd_placeholder"))
            p2 = QLineEdit()
            p2.setEchoMode(QLineEdit.EchoMode.Password)
            p2.setPlaceholderText(tr("pwd_repeat_placeholder"))
            self._user_fields.append((p1, p2))
            pwd_form.addRow(enabled)
            pwd_form.addRow(tr("field_name"), label_edit)
            pwd_form.addRow(tr("pwd_label"), p1)
            pwd_form.addRow(tr("pwd_repeat_label"), p2)
        layout.addWidget(pwd_group)

        labels_group = QGroupBox(tr("labels_section"))
        labels_form = QFormLayout(labels_group)
        labels_info = QLabel(tr("labels_info"))
        labels_info.setWordWrap(True)
        labels_form.addRow(labels_info)
        self._field_label_edits: dict[str, QLineEdit] = {}
        current_labels = vault.resolved_field_labels()
        for field_name in FIELD_NAMES:
            edit = QLineEdit()
            edit.setPlaceholderText(tr(f"field_{field_name}"))
            edit.setText(current_labels.get(field_name, ""))
            self._field_label_edits[field_name] = edit
            labels_form.addRow(tr(f"field_{field_name}"), edit)
        layout.addWidget(labels_group)

        perm_group = QGroupBox(tr("perm_section"))
        perm_layout = QGridLayout(perm_group)
        levels = [
            ("perm_none", "none"),
            ("perm_read", "read"),
            ("perm_hidden_read", "hidden_read"),
            ("perm_write", "write"),
        ]
        self._perm_combos: dict[str, QComboBox] = {}
        perms = vault.user_permissions
        for row, field_name in enumerate(FIELD_NAMES, start=1):
            perm_layout.addWidget(QLabel(tr(f"field_{field_name}")), row, 0)
            combo = QComboBox()
            for label_key, value in levels:
                combo.addItem(tr(label_key), value)
            current = perms.field_level(field_name)
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            self._perm_combos[field_name] = combo
            perm_layout.addWidget(combo, row, 1)
        layout.addWidget(perm_group)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #f08080;")
        self._error.setWordWrap(True)
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText(tr("ok"))
        if cancel_btn:
            cancel_btn.setText(tr("cancel"))

    def _on_accept(self) -> None:
        from kobipass.vault_model import UserPermissions

        admin_current = self._admin_current.text()
        admin_new = self._admin_new.text()
        admin_repeat = self._admin_new_repeat.text()
        if admin_new or admin_repeat:
            if self._require_admin_current and not admin_current:
                self._error.setText(tr("pwd_admin_required"))
                return
            if len(admin_new) < MIN_PASSWORD_LENGTH:
                self._error.setText(tr("pwd_too_short", min_len=MIN_PASSWORD_LENGTH))
                return
            if admin_new != admin_repeat:
                self._error.setText(tr("pwd_mismatch"))
                return

        user_passwords: list[tuple[bool, str]] = []
        for index, (enabled_box, (p1, p2)) in enumerate(
            zip(self._enabled_boxes, self._user_fields)
        ):
            enabled = enabled_box.isChecked()
            pwd1 = p1.text()
            pwd2 = p2.text()
            if enabled:
                if pwd1 or pwd2:
                    if len(pwd1) < MIN_PASSWORD_LENGTH:
                        self._error.setText(
                            tr("pwd_too_short", min_len=MIN_PASSWORD_LENGTH)
                        )
                        return
                    if pwd1 != pwd2:
                        self._error.setText(tr("pwd_mismatch"))
                        return
                    user_passwords.append((True, pwd1))
                    self._passwords_changed = True
                else:
                    user_passwords.append((True, ""))
            else:
                user_passwords.append((False, ""))

        perms = UserPermissions(
            name=self._perm_combos["name"].currentData(),
            info1=self._perm_combos["info1"].currentData(),
            info2=self._perm_combos["info2"].currentData(),
            info3=self._perm_combos["info3"].currentData(),
            info4=self._perm_combos["info4"].currentData(),
        )
        field_labels = {
            key: edit.text().strip()
            for key, edit in self._field_label_edits.items()
            if edit.text().strip()
        }
        slot_labels = [
            edit.text().strip() or f"Kullanıcı {index + 1}"
            for index, edit in enumerate(self._label_edits)
        ]
        self._result = {
            "user_passwords": user_passwords,
            "permissions": perms,
            "passwords_changed": self._passwords_changed,
            "field_labels": field_labels,
            "user_slot_labels": slot_labels,
            "admin_current": admin_current,
            "admin_new": admin_new if admin_new else None,
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result
