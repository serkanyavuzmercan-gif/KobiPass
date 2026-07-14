"""
Yönetici: alt kullanıcı kartları (kişiye özel izinler) + alan etiketleri.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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
from kobipass.ui.sub_user_card import SubUserCard
from kobipass.vault_model import FIELD_NAMES, KobiVault, USER_SLOT_COUNT, UserPermissions


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
        self.setMinimumWidth(620)
        self.resize(660, 720)
        self._vault = vault
        self._enabled_flags = list(enabled_flags)
        self._passwords_changed = False
        self._require_admin_current = require_admin_current
        self._result: dict | None = None
        self._cards: list[SubUserCard] = []

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(tr("users_info"))
        info.setWordWrap(True)
        layout.addWidget(info)

        # Yönetici — sabit, scroll dışı
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

        for index in range(USER_SLOT_COUNT):
            enabled = (
                self._enabled_flags[index] if index < len(self._enabled_flags) else False
            )
            if not enabled:
                continue
            label = (
                vault.user_slot_labels[index]
                if index < len(vault.user_slot_labels)
                else tr("user_default_name", n=index + 1)
            )
            username = (
                vault.user_slot_usernames[index]
                if index < len(vault.user_slot_usernames)
                else ""
            )
            perms = vault.permissions_for_slot(index + 1)
            self._insert_card(
                username=username,
                display_name=label,
                permissions=perms,
                password_required=False,
            )

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

    def _insert_card(
        self,
        *,
        username: str = "",
        display_name: str = "",
        permissions: UserPermissions | None = None,
        password_required: bool = True,
    ) -> None:
        if len(self._cards) >= USER_SLOT_COUNT:
            return
        card = SubUserCard(
            len(self._cards),
            username=username,
            display_name=display_name,
            permissions=permissions,
            password_required=password_required,
        )
        card.remove_requested.connect(self._remove_card)
        self._cards.append(card)
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self._renumber_cards()
        self._sync_add_button()

    def _add_card(self) -> None:
        self._insert_card(password_required=True)

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
                # Mevcut kullanıcı: parola boş bırakılabilir
                if data["password_required"]:
                    self._error.setText(tr("sub_user_pwd_required", n=index + 1))
                    return
                user_passwords.append((True, ""))

            slot_labels.append(data["display_name"])
            slot_usernames.append(data["username"])
            slot_permissions.append(data["permissions"])

        field_labels = {
            key: edit.text().strip()
            for key, edit in self._field_label_edits.items()
            if edit.text().strip()
        }
        self._result = {
            "user_passwords": user_passwords,
            "permissions": slot_permissions[0] if slot_permissions else UserPermissions(),
            "slot_permissions": slot_permissions,
            "passwords_changed": self._passwords_changed,
            "field_labels": field_labels,
            "user_slot_labels": slot_labels,
            "user_slot_usernames": slot_usernames,
            "admin_current": admin_current,
            "admin_new": admin_new if admin_new else None,
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result
