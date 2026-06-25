"""
kobiPass dialog pencereleri.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import MIN_PASSWORD_LENGTH, i18n, tr
from kobipass.resources import app_icon
from kobipass.ui.help_content import help_html
from kobipass.vault_model import FIELD_NAMES, FieldLevel, UserPermissions, USER_SLOT_COUNT


def _validate_password_pair(
    p1: str,
    p2: str,
    required: bool,
    min_len: int = MIN_PASSWORD_LENGTH,
) -> str | None:
    if not p1 and not p2:
        return None if not required else tr("pwd_admin_required")
    if len(p1) < min_len:
        return tr("pwd_too_short", min_len=min_len)
    if p1 != p2:
        return tr("pwd_mismatch")
    return None


class SetupVaultDialog(QDialog):
    """İlk kayıt: yönetici + kullanıcı parolaları ve izin şablonu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("setup_pwd_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumWidth(520)
        self._result: dict | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(tr("setup_pwd_info", min_len=MIN_PASSWORD_LENGTH))
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self._pwd_edits: list[QLineEdit] = []

        self._admin1 = QLineEdit()
        self._admin1.setEchoMode(QLineEdit.EchoMode.Password)
        self._admin1.setPlaceholderText(tr("pwd_placeholder"))
        self._admin2 = QLineEdit()
        self._admin2.setEchoMode(QLineEdit.EchoMode.Password)
        self._admin2.setPlaceholderText(tr("pwd_repeat_placeholder"))
        self._pwd_edits.extend((self._admin1, self._admin2))
        form.addRow(tr("admin_pwd_label"), self._admin1)
        form.addRow(tr("admin_pwd_repeat"), self._admin2)

        self._user_fields: list[tuple[QLineEdit, QLineEdit]] = []
        for n in range(1, USER_SLOT_COUNT + 1):
            p1 = QLineEdit()
            p1.setEchoMode(QLineEdit.EchoMode.Password)
            p1.setPlaceholderText(tr("pwd_placeholder"))
            p2 = QLineEdit()
            p2.setEchoMode(QLineEdit.EchoMode.Password)
            p2.setPlaceholderText(tr("pwd_repeat_placeholder"))
            self._pwd_edits.extend((p1, p2))
            form.addRow(tr("user_pwd_label", n=n), p1)
            form.addRow(tr("user_pwd_repeat", n=n), p2)
            self._user_fields.append((p1, p2))

        self._toggle = QPushButton(tr("show"))
        self._toggle.setCheckable(True)
        self._toggle.toggled.connect(self._on_toggle_visibility)
        form.addRow("", self._toggle)

        layout.addLayout(form)

        perm_group = QGroupBox(tr("perm_section"))
        perm_layout = QGridLayout(perm_group)
        perm_layout.addWidget(QLabel(""), 0, 0)
        levels = [
            ("perm_none", "none"),
            ("perm_read", "read"),
            ("perm_hidden_read", "hidden_read"),
            ("perm_write", "write"),
        ]
        self._perm_combos: dict[str, QComboBox] = {}
        defaults: dict[str, FieldLevel] = {
            "name": "read",
            "info1": "write",
            "info2": "hidden_read",
            "info3": "none",
            "info4": "none",
        }
        for row, field_name in enumerate(FIELD_NAMES, start=1):
            perm_layout.addWidget(QLabel(tr(f"field_{field_name}")), row, 0)
            combo = QComboBox()
            for label_key, value in levels:
                combo.addItem(tr(label_key), value)
            idx = combo.findData(defaults.get(field_name, "none"))
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

    def _on_toggle_visibility(self, checked: bool) -> None:
        mode = (
            QLineEdit.EchoMode.Normal
            if checked
            else QLineEdit.EchoMode.Password
        )
        for edit in self._pwd_edits:
            edit.setEchoMode(mode)
        self._toggle.setText(tr("hide") if checked else tr("show"))

    def _on_accept(self) -> None:
        err = _validate_password_pair(
            self._admin1.text(), self._admin2.text(), required=True
        )
        if err:
            self._error.setText(err)
            return

        user_passwords: list[tuple[bool, str]] = []
        for p1, p2 in self._user_fields:
            pwd1 = p1.text()
            pwd2 = p2.text()
            if not pwd1 and not pwd2:
                user_passwords.append((False, ""))
                continue
            slot_err = _validate_password_pair(pwd1, pwd2, required=True)
            if slot_err:
                self._error.setText(slot_err)
                return
            user_passwords.append((True, pwd1))

        perms = UserPermissions(
            name=self._perm_combos["name"].currentData(),
            info1=self._perm_combos["info1"].currentData(),
            info2=self._perm_combos["info2"].currentData(),
            info3=self._perm_combos["info3"].currentData(),
            info4=self._perm_combos["info4"].currentData(),
        )
        self._result = {
            "admin_password": self._admin1.text(),
            "user_passwords": user_passwords,
            "permissions": perms,
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result


class OpenPasswordDialog(QDialog):
    """Mevcut .enc dosyasını açmak için parola girişi."""

    def __init__(self, file_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("open_pwd_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumWidth(400)
        self._password: str | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        label = QLabel(tr("open_pwd_label", file=file_name))
        label.setWordWrap(True)
        layout.addWidget(label)

        self._pwd = QLineEdit()
        self._pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd.setPlaceholderText(tr("pwd_placeholder"))
        self._pwd.returnPressed.connect(self._on_accept)
        layout.addWidget(self._pwd)

        row = QHBoxLayout()
        self._toggle = QPushButton(tr("show"))
        self._toggle.setCheckable(True)
        self._toggle.toggled.connect(self._on_toggle_visibility)
        row.addWidget(self._toggle)
        row.addStretch()
        layout.addLayout(row)

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

    def _on_toggle_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Password if not checked else QLineEdit.EchoMode.Normal
        self._pwd.setEchoMode(mode)
        self._toggle.setText(tr("hide") if checked else tr("show"))

    def _on_accept(self) -> None:
        text = self._pwd.text()
        if not text:
            return
        self._password = text
        self.accept()

    def password(self) -> str | None:
        return self._password


def _message_box(
    parent: QWidget | None,
    icon: QMessageBox.Icon,
    title: str,
    message: str,
) -> None:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(message)
    box.setWindowIcon(app_icon())
    box.exec()


def show_error(parent: QWidget | None, title: str, message: str) -> None:
    _message_box(parent, QMessageBox.Icon.Critical, title, message)


def show_info(parent: QWidget | None, title: str, message: str) -> None:
    _message_box(parent, QMessageBox.Icon.Information, title, message)


class _HelpDragTitle(QLabel):
    def __init__(self, window: QDialog, text: str) -> None:
        super().__init__(text)
        self._window = window
        self._drag_pos: QPoint | None = None
        self.setObjectName("helpDialogTitle")
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint()
                - self._window.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)


class HelpDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowIcon(app_icon())
        self.setModal(False)
        self.setMinimumSize(520, 480)
        self.resize(560, 520)
        self.setObjectName("helpDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self._title = _HelpDragTitle(self, tr("help_title"))
        layout.addWidget(self._title)

        self._browser = QTextBrowser()
        self._browser.setObjectName("helpBrowser")
        self._browser.setOpenExternalLinks(False)
        self._browser.setFrameShape(QTextBrowser.Shape.NoFrame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._browser)
        layout.addWidget(scroll, stretch=1)

        self._close_btn = QPushButton(tr("help_close"))
        self._close_btn.clicked.connect(self.close)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)

        i18n.language_changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(tr("help_title"))
        self._title.setText(tr("help_title"))
        self._browser.setHtml(help_html())
        self._close_btn.setText(tr("help_close"))
