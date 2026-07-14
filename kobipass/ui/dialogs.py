"""
kobiPass dialog pencereleri.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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
from kobipass.ui.sub_user_card import SubUserCard
from kobipass.vault_model import USER_SLOT_COUNT, UserPermissions


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
    """İlk kayıt: yönetici sabit; alt kullanıcılar eklemeli kartlar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("setup_pwd_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumWidth(620)
        self.resize(660, 720)
        self._result: dict | None = None
        self._cards: list[SubUserCard] = []

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(tr("setup_pwd_info", min_len=MIN_PASSWORD_LENGTH))
        info.setWordWrap(True)
        layout.addWidget(info)

        admin_group = QGroupBox(tr("admin_section"))
        admin_form = QFormLayout(admin_group)
        self._admin1 = QLineEdit()
        self._admin1.setEchoMode(QLineEdit.EchoMode.Password)
        self._admin1.setPlaceholderText(tr("pwd_placeholder"))
        self._admin2 = QLineEdit()
        self._admin2.setEchoMode(QLineEdit.EchoMode.Password)
        self._admin2.setPlaceholderText(tr("pwd_repeat_placeholder"))
        admin_form.addRow(tr("admin_pwd_label"), self._admin1)
        admin_form.addRow(tr("admin_pwd_repeat"), self._admin2)
        layout.addWidget(admin_group)

        users_header = QHBoxLayout()
        users_title = QLabel(tr("sub_users_section"))
        users_title.setObjectName("sectionTitle")
        users_header.addWidget(users_title)
        users_header.addStretch()
        self._add_btn = QPushButton(tr("btn_add_sub_user"))
        self._add_btn.setObjectName("primaryBtn")
        self._add_btn.clicked.connect(self._add_card)
        users_header.addWidget(self._add_btn)
        layout.addLayout(users_header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cards_host = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_host)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()
        self._scroll.setWidget(self._cards_host)
        layout.addWidget(self._scroll, stretch=1)

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

        self._sync_add_button()

    def _insert_card(self) -> None:
        if len(self._cards) >= USER_SLOT_COUNT:
            return
        card = SubUserCard(len(self._cards), password_required=True)
        card.remove_requested.connect(self._remove_card)
        self._cards.append(card)
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self._renumber_cards()
        self._sync_add_button()

    def _add_card(self) -> None:
        self._insert_card()

    def _remove_card(self, card: SubUserCard) -> None:
        if card not in self._cards:
            return
        self._cards.remove(card)
        self._cards_layout.removeWidget(card)
        card.deleteLater()
        self._renumber_cards()
        self._sync_add_button()

    def _renumber_cards(self) -> None:
        for index, card in enumerate(self._cards):
            card.set_index(index)

    def _sync_add_button(self) -> None:
        remaining = USER_SLOT_COUNT - len(self._cards)
        self._add_btn.setEnabled(remaining > 0)
        self._add_btn.setText(
            tr("btn_add_sub_user")
            if remaining > 0
            else tr("btn_add_sub_user_full", max=USER_SLOT_COUNT)
        )

    def _on_accept(self) -> None:
        err = _validate_password_pair(
            self._admin1.text(), self._admin2.text(), required=True
        )
        if err:
            self._error.setText(err)
            return

        collected = [card.collect() for card in self._cards]
        user_passwords: list[tuple[bool, str]] = []
        slot_labels: list[str] = []
        slot_usernames: list[str] = []
        slot_permissions: list[UserPermissions] = []

        for index in range(USER_SLOT_COUNT):
            if index >= len(collected):
                user_passwords.append((False, ""))
                slot_labels.append(tr("user_default_name", n=index + 1))
                slot_usernames.append("")
                slot_permissions.append(UserPermissions())
                continue

            data = collected[index]
            pwd1 = data["password"]
            pwd2 = data["password_repeat"]
            slot_err = _validate_password_pair(pwd1, pwd2, required=True)
            if slot_err:
                self._error.setText(slot_err)
                return
            user_passwords.append((True, pwd1))
            slot_labels.append(data["display_name"])
            slot_usernames.append(data["username"])
            slot_permissions.append(data["permissions"])

        self._result = {
            "admin_password": self._admin1.text(),
            "user_passwords": user_passwords,
            "permissions": slot_permissions[0] if slot_permissions else UserPermissions(),
            "slot_permissions": slot_permissions,
            "user_slot_labels": slot_labels,
            "user_slot_usernames": slot_usernames,
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


class UnlockDialog(QDialog):
    """Kilitli oturumu yeniden açmak için parola ister."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("lock_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumWidth(400)
        self._password: str | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        label = QLabel(tr("lock_text"))
        label.setWordWrap(True)
        layout.addWidget(label)

        self._pwd = QLineEdit()
        self._pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd.setPlaceholderText(tr("pwd_placeholder"))
        self._pwd.returnPressed.connect(self._on_accept)
        layout.addWidget(self._pwd)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #f08080;")
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
            ok_btn.setText(tr("lock_unlock"))
        if cancel_btn:
            cancel_btn.setText(tr("cancel"))

    def show_error(self, message: str) -> None:
        self._error.setText(message)

    def _on_accept(self) -> None:
        text = self._pwd.text()
        if not text:
            self.show_error(tr("lock_wrong"))
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
