"""
Alt kullanıcı kartı — isim/kullanıcı adı/parola + kişiye özel izinler.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.ui.icons import icon_eye, icon_eye_off
from kobipass.vault_model import FieldLevel, UserPermissions


_PERM_LEVELS: list[tuple[str, FieldLevel]] = [
    ("perm_none", "none"),
    ("perm_read", "read"),
    ("perm_hidden_read", "hidden_read"),
    ("perm_write", "write"),
]


def _password_edit(placeholder_key: str) -> QLineEdit:
    edit = QLineEdit()
    edit.setEchoMode(QLineEdit.EchoMode.Password)
    edit.setPlaceholderText(tr(placeholder_key))
    return edit


def _eye_button() -> QToolButton:
    btn = QToolButton()
    btn.setObjectName("fieldEyeBtn")
    btn.setCheckable(True)
    btn.setAutoRaise(True)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setIcon(icon_eye_off())
    btn.setToolTip(tr("show"))
    return btn


def _perm_combo(current: FieldLevel) -> QComboBox:
    combo = QComboBox()
    for label_key, value in _PERM_LEVELS:
        combo.addItem(tr(label_key), value)
    idx = combo.findData(current)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    return combo


class SubUserCard(QWidget):
    """Tek alt kullanıcı kartı (eklenebilir / silinebilir)."""

    remove_requested = pyqtSignal(object)

    def __init__(
        self,
        index: int,
        *,
        username: str = "",
        display_name: str = "",
        permissions: UserPermissions | None = None,
        password_required: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("subUserCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._index = index
        self._password_required = password_required
        self._perms = permissions or UserPermissions()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setObjectName("subUserCardTitle")
        header.addWidget(self._title, stretch=1)
        self._remove_btn = QToolButton()
        self._remove_btn.setObjectName("subUserRemoveBtn")
        self._remove_btn.setText("✕")
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        header.addWidget(self._remove_btn)
        root.addLayout(header)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._username = QLineEdit()
        self._username.setPlaceholderText(tr("user_username_placeholder"))
        self._username.setText(username)

        self._display_name = QLineEdit()
        self._display_name.setPlaceholderText(tr("user_name_placeholder"))
        self._display_name.setText(display_name or tr("user_default_name", n=index + 1))

        self._pwd = _password_edit("pwd_placeholder")
        self._pwd_repeat = _password_edit("pwd_repeat_placeholder")
        self._pwd_eye = _eye_button()
        self._pwd_repeat_eye = _eye_button()
        self._pwd_eye.toggled.connect(
            lambda checked: self._toggle_echo(self._pwd, self._pwd_eye, checked)
        )
        self._pwd_repeat_eye.toggled.connect(
            lambda checked: self._toggle_echo(
                self._pwd_repeat, self._pwd_repeat_eye, checked
            )
        )

        form.addRow(tr("user_username_label"), self._username)
        form.addRow(tr("user_name_label"), self._display_name)
        form.addRow(tr("pwd_label"), self._wrap_with_eye(self._pwd, self._pwd_eye))
        form.addRow(
            tr("pwd_repeat_label"),
            self._wrap_with_eye(self._pwd_repeat, self._pwd_repeat_eye),
        )
        root.addLayout(form)

        perm_row = QHBoxLayout()
        perm_row.setSpacing(16)

        name_box = QVBoxLayout()
        name_box.setSpacing(4)
        self._name_perm_label = QLabel(tr("field_name"))
        self._name_perm = _perm_combo(self._perms.name)
        name_box.addWidget(self._name_perm_label)
        name_box.addWidget(self._name_perm)

        infos_box = QVBoxLayout()
        infos_box.setSpacing(4)
        self._infos_perm_label = QLabel(tr("perm_infos_label"))
        self._infos_perm = _perm_combo(self._perms.infos_level)
        infos_box.addWidget(self._infos_perm_label)
        infos_box.addWidget(self._infos_perm)

        perm_row.addLayout(name_box, stretch=1)
        perm_row.addLayout(infos_box, stretch=1)
        root.addLayout(perm_row)

        self.retranslate()

    @staticmethod
    def _wrap_with_eye(edit: QLineEdit, eye: QToolButton) -> QWidget:
        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(edit, stretch=1)
        layout.addWidget(eye)
        return host

    @staticmethod
    def _toggle_echo(edit: QLineEdit, eye: QToolButton, shown: bool) -> None:
        edit.setEchoMode(
            QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password
        )
        eye.setIcon(icon_eye() if shown else icon_eye_off())
        eye.setToolTip(tr("hide") if shown else tr("show"))

    def set_index(self, index: int) -> None:
        self._index = index
        self.retranslate()

    @property
    def card_index(self) -> int:
        return self._index

    def retranslate(self) -> None:
        self._title.setText(tr("sub_user_card_title", n=self._index + 1))
        self._username.setPlaceholderText(tr("user_username_placeholder"))
        self._display_name.setPlaceholderText(tr("user_name_placeholder"))
        self._pwd.setPlaceholderText(tr("pwd_placeholder"))
        self._pwd_repeat.setPlaceholderText(tr("pwd_repeat_placeholder"))
        self._name_perm_label.setText(tr("field_name"))
        self._infos_perm_label.setText(tr("perm_infos_label"))
        self._remove_btn.setToolTip(tr("sub_user_remove_tip"))
        self._refresh_perm_combo(self._name_perm)
        self._refresh_perm_combo(self._infos_perm)

    def _refresh_perm_combo(self, combo: QComboBox) -> None:
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for label_key, value in _PERM_LEVELS:
            combo.addItem(tr(label_key), value)
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def collect(self) -> dict:
        display_name = self._display_name.text().strip() or tr(
            "user_default_name", n=self._index + 1
        )
        name_level: FieldLevel = self._name_perm.currentData()
        infos_level: FieldLevel = self._infos_perm.currentData()
        perms = UserPermissions(name=name_level).with_infos_level(infos_level)
        return {
            "username": self._username.text().strip(),
            "display_name": display_name,
            "password": self._pwd.text(),
            "password_repeat": self._pwd_repeat.text(),
            "permissions": perms,
            "password_required": self._password_required,
        }
