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
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import MIN_PASSWORD_LENGTH, i18n, tr
from kobipass.resources import app_icon
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
    """Hider'ın info paneli düzeninde yardım: adımlar · uyarı · kartlar · künye."""

    _CARD_COUNT = 5

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowIcon(app_icon())
        self.setModal(False)
        self.setMinimumSize(700, 480)
        self.resize(820, 540)
        self.setObjectName("helpDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self._title = _HelpDragTitle(self, tr("help_title"))
        layout.addWidget(self._title)

        # ── Üst satır: adımlar + uyarı (sol) · künye kartı (sağ) ─────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        self._step_labels: list[QLabel] = []
        for n in (1, 2, 3):
            step_row = QHBoxLayout()
            step_row.setSpacing(8)
            badge = QLabel(str(n))
            badge.setObjectName("helpStepBadge")
            badge.setFixedSize(22, 22)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text = QLabel()
            text.setObjectName("helpStepText")
            text.setWordWrap(True)
            step_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            step_row.addWidget(text, 1)
            left_col.addLayout(step_row)
            self._step_labels.append(text)

        self._warn_box = QLabel()
        self._warn_box.setObjectName("helpWarnBox")
        self._warn_box.setWordWrap(True)
        left_col.addWidget(self._warn_box)
        left_col.addStretch()

        top_row.addLayout(left_col, 3)

        credits = QWidget()
        credits.setObjectName("helpCreditsCard")
        credits.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cred_layout = QVBoxLayout(credits)
        cred_layout.setContentsMargins(14, 12, 14, 12)
        cred_layout.setSpacing(4)

        self._cred_name = QLabel()
        self._cred_name.setObjectName("helpCreditsName")
        self._cred_by = QLabel()
        self._cred_by.setObjectName("helpCreditsBy")
        self._cred_by.setWordWrap(True)
        self._cred_desc = QLabel()
        self._cred_desc.setObjectName("helpCreditsText")
        self._cred_desc.setWordWrap(True)
        self._cred_ver = QLabel()
        self._cred_ver.setObjectName("helpCreditsText")
        self._cred_footer = QLabel()
        self._cred_footer.setObjectName("helpCreditsFooter")
        self._cred_footer.setWordWrap(True)

        cred_layout.addWidget(self._cred_name)
        cred_layout.addWidget(self._cred_by)
        cred_layout.addWidget(self._cred_desc)
        cred_layout.addSpacing(6)
        cred_layout.addWidget(self._cred_ver)
        cred_layout.addStretch()
        cred_layout.addWidget(self._cred_footer)

        top_row.addWidget(credits, 2)
        layout.addLayout(top_row, 1)

        # ── Alt satır: özellik kartları ───────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self._card_titles: list[QLabel] = []
        self._card_texts: list[QLabel] = []
        for _ in range(self._CARD_COUNT):
            card = QWidget()
            card.setObjectName("helpFeatureCard")
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(6)
            c_title = QLabel()
            c_title.setObjectName("helpCardTitle")
            c_title.setWordWrap(True)
            c_text = QLabel()
            c_text.setObjectName("helpCardText")
            c_text.setWordWrap(True)
            card_layout.addWidget(c_title)
            card_layout.addWidget(c_text)
            card_layout.addStretch()
            cards_row.addWidget(card, 1)
            self._card_titles.append(c_title)
            self._card_texts.append(c_text)
        layout.addLayout(cards_row, 1)

        self._close_btn = QPushButton(tr("help_close"))
        self._close_btn.clicked.connect(self.close)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)

        i18n.language_changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self) -> None:
        from kobipass import __version__

        self.setWindowTitle(tr("help_title"))
        self._title.setText(tr("help_title"))
        for idx, lbl in enumerate(self._step_labels, start=1):
            lbl.setText(tr(f"help_step{idx}"))
        self._warn_box.setText(tr("help_warn"))
        for idx in range(self._CARD_COUNT):
            self._card_titles[idx].setText(tr(f"help_card{idx + 1}_title"))
            self._card_texts[idx].setText(tr(f"help_card{idx + 1}_text"))
        self._cred_name.setText("KobiPass")
        self._cred_by.setText(tr("help_credits_by"))
        self._cred_desc.setText(tr("help_credits_desc"))
        self._cred_ver.setText(tr("help_credits_ver", version=__version__))
        self._cred_footer.setText(tr("help_credits_footer"))
        self._close_btn.setText(tr("help_close"))
