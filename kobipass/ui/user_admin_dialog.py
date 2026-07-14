"""Alt kullanıcıların kimlik, parola ve tüm yetkilerini kart bazında yönetir."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kobipass.crypto import (
    MAX_USER_SLOTS,
    VaultFileKeys,
    password_matches_user_slot,
    passwords_are_unique,
)
from kobipass.i18n import MIN_PASSWORD_LENGTH, tr
from kobipass.resources import app_icon
from kobipass.ui.icons import icon_eye, icon_eye_off
from kobipass.ui.strength import attach_strength_label
from kobipass.vault_model import FieldLevel, KobiVault, UserPermissions


_PERM_LEVELS: list[tuple[str, FieldLevel]] = [
    ("perm_none", "none"),
    ("perm_read", "read"),
    ("perm_hidden_read", "hidden_read"),
    ("perm_write", "write"),
]


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


def _perm_combo(current: FieldLevel) -> QComboBox:
    combo = QComboBox()
    for label_key, value in _PERM_LEVELS:
        combo.addItem(tr(label_key), value)
    idx = combo.findData(current)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    return combo


def _field_permission_block(
    title_key: str,
    description_key: str,
    current: FieldLevel,
) -> tuple[QWidget, QComboBox]:
    block = QWidget()
    block.setObjectName("permissionBlock")
    layout = QVBoxLayout(block)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(5)
    top = QHBoxLayout()
    title = QLabel(tr(title_key))
    title.setObjectName("permissionTitle")
    combo = _perm_combo(current)
    combo.setMinimumWidth(190)
    top.addWidget(title)
    top.addStretch()
    top.addWidget(combo)
    description = QLabel(tr(description_key))
    description.setObjectName("permissionDescription")
    description.setWordWrap(True)
    layout.addLayout(top)
    layout.addWidget(description)
    return block, combo


def _action_permission_block(
    label_key: str,
    description_key: str,
    checked: bool,
) -> tuple[QWidget, QCheckBox]:
    block = QWidget()
    block.setObjectName("permissionActionBlock")
    layout = QVBoxLayout(block)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(4)
    checkbox = QCheckBox(tr(label_key))
    checkbox.setChecked(checked)
    description = QLabel(tr(description_key))
    description.setObjectName("permissionDescription")
    description.setWordWrap(True)
    layout.addWidget(checkbox)
    layout.addWidget(description)
    layout.addStretch()
    return block, checkbox


class UserAdminDialog(QDialog):
    def __init__(
        self,
        vault: KobiVault,
        enabled_flags: list[bool],
        parent: QWidget | None = None,
        *,
        admin_password: str = "",
        keys: VaultFileKeys | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("users_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setObjectName("userAdminDialog")
        self.setMinimumSize(900, 560)
        self.resize(920, 600)
        self._vault = vault
        self._enabled_flags = list(enabled_flags)
        self._passwords_changed = False
        self._admin_password = admin_password
        self._keys = keys
        self._result: dict | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        info = QLabel(tr("users_info"))
        info.setWordWrap(True)
        outer.addWidget(info)

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
        self._add_user_btn.clicked.connect(lambda: self._add_slot_card())
        users_group_layout.addWidget(
            self._add_user_btn, 0, Qt.AlignmentFlag.AlignLeft
        )
        outer.addWidget(users_group, 1)

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
            perms = vault.permissions_for_slot(n + 1)
            self._add_slot_card(orig_index=n, enabled=True, label=label, permissions=perms)

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
        self,
        *,
        orig_index: int | None = None,
        enabled: bool = True,
        label: str = "",
        permissions: UserPermissions | None = None,
    ) -> None:
        if orig_index is None:
            new_count = sum(
                1 for card in self._slot_cards
                if card["orig_index"] is None
            )
            if self._original_count + new_count >= MAX_USER_SLOTS:
                self._warn(tr("max_users_reached", max=MAX_USER_SLOTS))
                return
        n = len(self._slot_cards) + 1
        perms = permissions.copy() if permissions else UserPermissions()
        is_new = orig_index is None

        card = QFrame()
        card.setObjectName("userSlotCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(6)

        header = QHBoxLayout()
        enabled_box = QCheckBox(tr("user_card_title", n=n))
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
        form.addRow(tr("user_name_label"), label_edit)
        outer.addLayout(form)

        password_toggle = QPushButton(tr("change_user_password"))
        password_toggle.setObjectName("secondaryActionBtn")
        password_toggle.setVisible(not is_new)
        outer.addWidget(
            password_toggle, 0, Qt.AlignmentFlag.AlignLeft
        )

        password_panel = QWidget()
        password_panel.setObjectName("passwordChangePanel")
        password_form = QFormLayout(password_panel)
        password_form.setContentsMargins(10, 8, 10, 8)
        password_form.setVerticalSpacing(6)
        p1 = _password_edit(tr("pwd_placeholder"))
        p2 = _password_edit(tr("pwd_repeat_placeholder"))
        password_form.addRow(
            tr("new_user_password_label") if is_new else tr("pwd_label"),
            p1,
        )
        strength = attach_strength_label(p1)
        password_form.addRow("", strength)
        password_form.addRow(tr("pwd_repeat_label"), p2)
        password_panel.setVisible(is_new)
        outer.addWidget(password_panel)

        def toggle_password_panel() -> None:
            visible = not password_panel.isVisible()
            password_panel.setVisible(visible)
            password_toggle.setText(
                tr("cancel_password_change")
                if visible
                else tr("change_user_password")
            )
            if not visible:
                p1.clear()
                p2.clear()

        password_toggle.clicked.connect(toggle_password_panel)

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
            "perm_name_label", "perm_name_desc", perms.name
        )
        info_block, perm_info = _field_permission_block(
            "perm_info_label", "perm_info_desc", perms.info
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
            "perm_can_add", "perm_can_add_desc", perms.can_add_entry
        )
        delete_block, can_delete_box = _action_permission_block(
            "perm_can_delete", "perm_can_delete_desc", perms.can_delete_entry
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
            password_toggle,
            password_panel,
            permissions_panel,
        ]

        def apply(checked: bool) -> None:
            for w in interactive:
                w.setEnabled(checked)

        enabled_box.toggled.connect(apply)
        apply(enabled_box.isChecked())

        entry = {
            "orig_index": orig_index,
            "enabled": enabled_box,
            "label": label_edit,
            "p1": p1,
            "p2": p2,
            "password_panel": password_panel,
            "password_toggle": password_toggle,
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

    def _warn(self, message: str) -> None:
        from kobipass.ui.dialogs import show_error

        show_error(self, tr("warn_title"), message)

    def _collect_card_permissions(self, card: dict) -> UserPermissions:
        # can_save türetilir (normalized): düzenleme/ekleme/silme yetkisi olan
        # kaydedebilir, salt görüntüleyen kaydedemez.
        return UserPermissions(
            name=card["perm_name"].currentData(),
            info=card["perm_info"].currentData(),
            can_add_entry=card["can_add"].isChecked(),
            can_delete_entry=card["can_delete"].isChecked(),
        ).normalized()

    def _conflicts_with_preserved_passwords(
        self,
        effective_admin: str,
        user_passwords: list[tuple[bool, str]],
        *,
        admin_changed: bool,
    ) -> bool:
        """Yeni parolaları, şifreli olarak korunan mevcut slotlarla karşılaştır."""
        if self._keys is None:
            return False
        for index, (enabled, password) in enumerate(user_passwords):
            if not enabled:
                continue
            if not password:
                if (
                    admin_changed
                    and password_matches_user_slot(
                        self._keys, effective_admin, index
                    )
                ):
                    return True
                continue
            for other_index in range(len(self._keys.user_slots)):
                if other_index == index:
                    continue
                # Devre dışı bırakılan veya bu işlemde değiştirilen eski parola finalde yok.
                if other_index < len(user_passwords):
                    other_enabled, other_new = user_passwords[other_index]
                    if not other_enabled or other_new:
                        continue
                if password_matches_user_slot(
                    self._keys, password, other_index
                ):
                    return True
        return False

    def _on_accept(self) -> None:
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
        slot_permissions = [
            self._vault.permissions_for_slot(i + 1).copy()
            for i in range(total)
        ]

        new_passwords: list[tuple[bool, str]] = []
        new_labels: list[str] = []
        new_permissions: list[UserPermissions] = []

        for pos, card in enumerate(self._slot_cards, start=1):
            enabled = card["enabled"].isChecked()
            pwd1 = card["p1"].text()
            pwd2 = card["p2"].text()
            label = card["label"].text().strip() or tr("user_default_label", n=pos)
            perms = self._collect_card_permissions(card)
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
                slot_permissions[oi] = perms
            else:
                if not (pwd1 or pwd2):
                    continue
                new_passwords.append(entry_pw)
                new_labels.append(label)
                new_permissions.append(perms)

        user_passwords.extend(new_passwords)
        slot_labels.extend(new_labels)
        slot_permissions.extend(new_permissions)

        while len(slot_permissions) < len(user_passwords):
            slot_permissions.append(UserPermissions())
        while len(slot_labels) < len(user_passwords):
            slot_labels.append(
                tr("user_default_label", n=len(slot_labels) + 1)
            )

        if (
            not passwords_are_unique(self._admin_password, user_passwords)
            or self._conflicts_with_preserved_passwords(
                self._admin_password,
                user_passwords,
                admin_changed=False,
            )
        ):
            self._warn(tr("pwd_not_available"))
            return

        first_enabled = next(
            (p for (en, _), p in zip(user_passwords, slot_permissions) if en),
            self._vault.user_permissions.copy(),
        )

        new_enabled = [enabled for enabled, _ in user_passwords]
        old_slot_dicts = [
            self._vault.permissions_for_slot(i + 1).to_dict()
            for i in range(max(len(self._vault.user_slot_permissions), total))
        ]
        new_slot_dicts = [p.to_dict() for p in slot_permissions]
        changed = (
            self._passwords_changed
            or new_slot_dicts != old_slot_dicts
            or slot_labels != list(self._vault.user_slot_labels)
            or new_enabled != list(self._enabled_flags)
        )
        self._result = {
            "user_passwords": user_passwords,
            "permissions": first_enabled,
            "slot_permissions": slot_permissions,
            "passwords_changed": self._passwords_changed,
            "user_slot_labels": slot_labels,
            "changed": changed,
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result
