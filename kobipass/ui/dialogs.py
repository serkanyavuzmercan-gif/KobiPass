"""
kobiPass dialog pencereleri.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.crypto import MAX_USER_SLOTS, passwords_are_unique
from kobipass.i18n import MIN_PASSWORD_LENGTH, i18n, tr
from kobipass.resources import app_icon
from kobipass.ui.strength import attach_strength_label
from kobipass.ui.user_admin_dialog import (
    _NAME_PERM_LEVELS,
    _action_permission_block,
    _field_permission_block,
    _password_edit,
)
from kobipass.vault_model import UserPermissions


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
    """İlk kayıt: sol alt kullanıcı kartları, sağ üst yönetici parola/tekrar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("setup_pwd_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setObjectName("userAdminDialog")
        self.setMinimumSize(900, 560)
        self.resize(920, 600)
        self._result: dict | None = None
        self._slot_cards: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        info = QLabel(tr("setup_pwd_info", min_len=MIN_PASSWORD_LENGTH))
        info.setWordWrap(True)
        outer.addWidget(info)

        columns = QHBoxLayout()
        columns.setSpacing(14)

        # ── SOL: Alt kullanıcı kartları (izinler diyaloğu ile aynı) ──────────
        left = QVBoxLayout()
        left.setSpacing(8)

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
        slots_scroll.setMinimumHeight(280)
        slots_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        slots_scroll.viewport().setStyleSheet("background: transparent;")
        users_group_layout.addWidget(slots_scroll, 1)

        self._add_user_btn = QPushButton(tr("add_user_btn"))
        self._add_user_btn.setObjectName("addRecordBtn")
        self._add_user_btn.clicked.connect(self._add_slot_card)
        users_group_layout.addWidget(
            self._add_user_btn, 0, Qt.AlignmentFlag.AlignLeft
        )
        left.addWidget(users_group, 1)
        columns.addLayout(left, 3)

        # ── SAĞ: yönetici parola/tekrar (üstte ilk) + ortak İsim/Bilgiler ───
        right = QVBoxLayout()
        right.setSpacing(10)
        right.setAlignment(Qt.AlignmentFlag.AlignTop)

        admin_group = QGroupBox(tr("admin_setup_section"))
        admin_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        admin_form = QFormLayout(admin_group)
        admin_form.setContentsMargins(10, 8, 10, 10)
        admin_form.setVerticalSpacing(6)
        self._admin1 = _password_edit(tr("pwd_placeholder"))
        self._admin2 = _password_edit(tr("pwd_repeat_placeholder"))
        admin_form.addRow(tr("admin_pwd_label"), self._admin1)
        admin_form.addRow("", attach_strength_label(self._admin1))
        admin_form.addRow(tr("admin_pwd_repeat"), self._admin2)
        right.addWidget(admin_group)

        right.addStretch(1)
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

    def _warn(self, message: str) -> None:
        show_error(self, tr("warn_title"), message)

    def _add_slot_card(self) -> None:
        if len(self._slot_cards) >= MAX_USER_SLOTS:
            self._warn(tr("max_users_reached", max=MAX_USER_SLOTS))
            return

        n = len(self._slot_cards) + 1
        card = QFrame()
        card.setObjectName("userSlotCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(6)

        header = QHBoxLayout()
        enabled_box = QCheckBox(tr("user_card_title", n=n))
        enabled_box.setChecked(True)
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
        label_edit.setText(tr("user_default_label", n=n))
        p1 = _password_edit(tr("pwd_placeholder"))
        p2 = _password_edit(tr("pwd_repeat_placeholder"))
        form.addRow(tr("user_name_label"), label_edit)
        form.addRow(tr("new_user_password_label"), p1)
        strength = attach_strength_label(p1)
        form.addRow("", strength)
        form.addRow(tr("pwd_repeat_label"), p2)
        outer.addLayout(form)

        defaults = UserPermissions()
        permissions_panel = QWidget()
        permissions_panel.setObjectName("cardPermissionsPanel")
        permissions_layout = QVBoxLayout(permissions_panel)
        permissions_layout.setContentsMargins(0, 4, 0, 0)
        permissions_layout.setSpacing(8)

        fields_title = QLabel(tr("perm_fields_section"))
        fields_title.setObjectName("cardFlagsTitle")
        permissions_layout.addWidget(fields_title)
        fields_row = QHBoxLayout()
        fields_row.setSpacing(8)
        name_block, perm_name = _field_permission_block(
            "perm_name_label", "perm_name_desc", defaults.name, _NAME_PERM_LEVELS
        )
        info_block, perm_info = _field_permission_block(
            "perm_info_label", "perm_info_desc", defaults.info
        )
        fields_row.addWidget(name_block, 1)
        fields_row.addWidget(info_block, 1)
        permissions_layout.addLayout(fields_row)

        actions_title = QLabel(tr("perm_actions_section"))
        actions_title.setObjectName("cardFlagsTitle")
        permissions_layout.addWidget(actions_title)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        add_block, can_add_box = _action_permission_block(
            "perm_can_add", "perm_can_add_desc", defaults.can_add_entry
        )
        delete_block, can_delete_box = _action_permission_block(
            "perm_can_delete",
            "perm_can_delete_desc",
            defaults.can_delete_entry,
        )
        actions_row.addWidget(add_block, 1)
        actions_row.addWidget(delete_block, 1)
        permissions_layout.addLayout(actions_row)
        save_note = QLabel(tr("perm_save_auto"))
        save_note.setObjectName("permissionDescription")
        save_note.setWordWrap(True)
        permissions_layout.addWidget(save_note)
        outer.addWidget(permissions_panel)

        interactive = [
            label_edit,
            p1,
            p2,
            strength,
            permissions_panel,
        ]

        def apply(checked: bool) -> None:
            for w in interactive:
                w.setEnabled(checked)

        enabled_box.toggled.connect(apply)
        apply(enabled_box.isChecked())

        entry = {
            "enabled": enabled_box,
            "label": label_edit,
            "p1": p1,
            "p2": p2,
            "perm_name": perm_name,
            "perm_info": perm_info,
            "can_add": can_add_box,
            "can_delete": can_delete_box,
            "card": card,
        }
        remove_btn.clicked.connect(lambda: self._remove_slot_card(entry))
        self._slots_layout.addWidget(card)
        self._slot_cards.append(entry)

    def _remove_slot_card(self, entry: dict) -> None:
        if entry not in self._slot_cards:
            return
        self._slot_cards.remove(entry)
        entry["card"].setParent(None)
        entry["card"].deleteLater()
        for pos, card in enumerate(self._slot_cards, start=1):
            card["enabled"].setText(tr("user_card_title", n=pos))

    def _on_accept(self) -> None:
        err = _validate_password_pair(
            self._admin1.text(), self._admin2.text(), required=True
        )
        if err:
            self._warn(err)
            return

        user_passwords: list[tuple[bool, str]] = []
        slot_labels: list[str] = []
        slot_permissions: list[UserPermissions] = []

        for pos, card in enumerate(self._slot_cards, start=1):
            if not card["enabled"].isChecked():
                continue
            pwd1 = card["p1"].text()
            pwd2 = card["p2"].text()
            slot_err = _validate_password_pair(pwd1, pwd2, required=True)
            if slot_err:
                self._warn(slot_err)
                return
            label = card["label"].text().strip() or tr("user_default_label", n=pos)
            user_passwords.append((True, pwd1))
            slot_labels.append(label)
            slot_permissions.append(
                UserPermissions(
                    name=card["perm_name"].currentData(),
                    info=card["perm_info"].currentData(),
                    can_add_entry=card["can_add"].isChecked(),
                    can_delete_entry=card["can_delete"].isChecked(),
                ).normalized()
            )

        if not passwords_are_unique(self._admin1.text(), user_passwords):
            self._warn(tr("pwd_not_available"))
            return

        first_enabled = (
            slot_permissions[0] if slot_permissions else UserPermissions()
        )
        self._result = {
            "admin_password": self._admin1.text(),
            "user_passwords": user_passwords,
            "permissions": first_enabled,
            "slot_permissions": slot_permissions,
            "user_slot_labels": slot_labels,
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


class RestrictionDialog(QDialog):
    """Satırları oynatmadan yetki kısıtını açıklayan küçük premium pencere."""

    def __init__(self, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("premiumRestrictionDialog")
        self.setWindowTitle(tr("restricted_notice_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setFixedWidth(480)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(16)

        content = QHBoxLayout()
        content.setSpacing(13)
        icon = QLabel("!")
        icon.setObjectName("restrictionDialogIcon")
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(5)
        title = QLabel(tr("restricted_notice_title"))
        title.setObjectName("restrictionDialogTitle")
        text.addWidget(title)
        detail = QLabel(message)
        detail.setObjectName("restrictionDialogText")
        detail.setWordWrap(True)
        text.addWidget(detail)
        content.addLayout(text, 1)
        outer.addLayout(content)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton(tr("ok"))
        close.setObjectName("restrictionDialogButton")
        close.setMinimumWidth(100)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        outer.addLayout(buttons)


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
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    ok_btn = box.button(QMessageBox.StandardButton.Ok)
    if ok_btn:
        ok_btn.setText(tr("ok"))
    box.exec()


def show_error(parent: QWidget | None, title: str, message: str) -> None:
    _message_box(parent, QMessageBox.Icon.Critical, title, message)


def show_info(parent: QWidget | None, title: str, message: str) -> None:
    _message_box(parent, QMessageBox.Icon.Information, title, message)


def show_restriction(parent: QWidget | None, message: str) -> None:
    RestrictionDialog(message, parent).exec()

