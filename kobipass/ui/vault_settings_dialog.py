"""Kasa düzeyindeki hassas ayarlar — kullanıcı yetkilerinden ayrı."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from kobipass.crypto import (
    VaultFileKeys,
    password_matches_user_slot,
    passwords_are_unique,
)
from kobipass.i18n import MIN_PASSWORD_LENGTH, tr
from kobipass.resources import app_icon
from kobipass.ui.strength import attach_strength_label
from kobipass.ui.user_admin_dialog import _password_edit


class VaultSettingsDialog(QDialog):
    def __init__(
        self,
        admin_password: str,
        keys: VaultFileKeys,
        user_passwords: list[tuple[bool, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("userAdminDialog")
        self.setWindowTitle(tr("vault_settings_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumWidth(560)
        self._admin_password = admin_password
        self._keys = keys
        self._user_passwords = list(user_passwords)
        self._result: dict | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        title = QLabel(tr("vault_settings_heading"))
        title.setObjectName("settingsHeading")
        outer.addWidget(title)
        info = QLabel(tr("vault_settings_info"))
        info.setObjectName("settingsDescription")
        info.setWordWrap(True)
        outer.addWidget(info)

        group = QGroupBox(tr("admin_change_section"))
        form = QFormLayout(group)
        form.setContentsMargins(12, 10, 12, 12)
        form.setVerticalSpacing(8)
        self._current = _password_edit()
        self._new = _password_edit()
        self._repeat = _password_edit()
        form.addRow(tr("admin_pwd_current"), self._current)
        form.addRow(tr("admin_pwd_new"), self._new)
        form.addRow("", attach_strength_label(self._new))
        form.addRow(tr("admin_pwd_new_repeat"), self._repeat)
        outer.addWidget(group)

        self._error = QLabel()
        self._error.setObjectName("settingsError")
        self._error.setWordWrap(True)
        outer.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText(tr("apply"))
        if cancel_btn:
            cancel_btn.setText(tr("cancel"))
        outer.addWidget(buttons)

    def _matches_preserved_user(self, password: str) -> bool:
        for index, slot in enumerate(self._keys.user_slots):
            enabled = slot.enabled
            replacement = ""
            if index < len(self._user_passwords):
                enabled, replacement = self._user_passwords[index]
            if enabled and not replacement and password_matches_user_slot(
                self._keys, password, index
            ):
                return True
        return False

    def _on_accept(self) -> None:
        current = self._current.text()
        new = self._new.text()
        repeat = self._repeat.text()
        if current != self._admin_password:
            self._error.setText(tr("admin_pwd_wrong"))
            return
        if len(new) < MIN_PASSWORD_LENGTH:
            self._error.setText(
                tr("pwd_too_short", min_len=MIN_PASSWORD_LENGTH)
            )
            return
        if new != repeat:
            self._error.setText(tr("pwd_mismatch"))
            return
        if (
            not passwords_are_unique(new, self._user_passwords)
            or self._matches_preserved_user(new)
        ):
            self._error.setText(tr("pwd_not_available"))
            return
        self._result = {"admin_new": new}
        self.accept()

    def result_data(self) -> dict | None:
        return self._result
