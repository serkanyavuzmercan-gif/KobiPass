"""
Yönetici: alt kullanıcı kartları + ortak alan izinleri.

Sol: eklemeli alt kullanıcı kartları (isim/parola + kişiye özel genel yetkiler).
Sağ: yönetici parola değişimi + ortak İsim/Bilgiler izinleri (scroll/ekle dışı).
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
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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
from kobipass.ui.icons import icon_eye, icon_eye_off
from kobipass.ui.strength import attach_strength_label
from kobipass.vault_model import PERM_FIELDS, FieldLevel, KobiVault, UserPermissions


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


class UserAdminDialog(QDialog):
    def __init__(
        self,
        vault: KobiVault,
        enabled_flags: list[bool],
        parent: QWidget | None = None,
        *,
        admin_password: str = "",
        keys: VaultFileKeys | None = None,
        require_admin_current: bool = True,
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
        self._require_admin_current = require_admin_current
        self._result: dict | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        info = QLabel(tr("users_info"))
        info.setWordWrap(True)
        outer.addWidget(info)

        columns = QHBoxLayout()
        columns.setSpacing(14)

        # ── SOL: Alt kullanıcı kartları ─────────────────────────────────────
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
        self._add_user_btn.clicked.connect(lambda: self._add_slot_card())
        users_group_layout.addWidget(
            self._add_user_btn, 0, Qt.AlignmentFlag.AlignLeft
        )
        left.addWidget(users_group, 1)
        columns.addLayout(left, 3)

        shared = vault.user_permissions
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

        # ── SAĞ: yönetici + ortak İsim/Bilgiler (kırmızı alan) ───────────────
        right = QVBoxLayout()
        right.setSpacing(10)
        right.setAlignment(Qt.AlignmentFlag.AlignTop)

        admin_group = QGroupBox(tr("admin_change_section"))
        admin_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        admin_form = QFormLayout(admin_group)
        admin_form.setContentsMargins(10, 8, 10, 10)
        admin_form.setVerticalSpacing(6)
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

        # Ortak alan izinleri — kullanıcıya özel değil
        perm_group = QGroupBox(tr("perm_section"))
        perm_group.setObjectName("sharedPermsBox")
        perm_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        perm_form = QFormLayout(perm_group)
        perm_form.setContentsMargins(10, 6, 10, 8)
        perm_form.setHorizontalSpacing(10)
        perm_form.setVerticalSpacing(4)
        perm_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self._perm_combos: dict[str, QComboBox] = {}
        for field_name in PERM_FIELDS:
            combo = _perm_combo(shared.field_level(field_name))
            combo.setMinimumWidth(120)
            self._perm_combos[field_name] = combo
            perm_form.addRow(tr(f"field_{field_name}"), combo)
        right.addWidget(perm_group)
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

    def _add_slot_card(
        self,
        *,
        orig_index: int | None = None,
        enabled: bool = True,
        label: str = "",
        permissions: UserPermissions | None = None,
    ) -> None:
        """Kart: isim/parola + kişiye özel genel yetkiler (İsim/Bilgiler yok)."""
        n = len(self._slot_cards) + 1
        perms = permissions.copy() if permissions else UserPermissions()

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
        strength = attach_strength_label(p1)
        form.addRow("", strength)
        form.addRow(tr("pwd_repeat_label"), p2)
        outer.addLayout(form)

        # Genel yetkiler — bu kullanıcıya özel
        flags_title = QLabel(tr("perm_flags_section"))
        flags_title.setObjectName("cardFlagsTitle")
        outer.addWidget(flags_title)
        flags_row = QHBoxLayout()
        flags_row.setSpacing(14)
        can_add_box = QCheckBox(tr("perm_can_add"))
        can_add_box.setChecked(perms.can_add_entry)
        can_delete_box = QCheckBox(tr("perm_can_delete"))
        can_delete_box.setChecked(perms.can_delete_entry)
        can_save_box = QCheckBox(tr("perm_can_save"))
        can_save_box.setChecked(perms.can_save)
        for box in (can_add_box, can_delete_box, can_save_box):
            flags_row.addWidget(box)
        flags_row.addStretch()
        outer.addLayout(flags_row)

        interactive = [
            label_edit,
            p1,
            p2,
            strength,
            can_add_box,
            can_delete_box,
            can_save_box,
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
            "can_add": can_add_box,
            "can_delete": can_delete_box,
            "can_save": can_save_box,
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
            card["enabled"].setText(tr("user_pwd_label", n=pos))

    def _warn(self, message: str) -> None:
        from kobipass.ui.dialogs import show_error

        show_error(self, tr("warn_title"), message)

    def _shared_field_levels(self) -> tuple[FieldLevel, FieldLevel]:
        return (
            self._perm_combos["name"].currentData(),
            self._perm_combos["info"].currentData(),
        )

    def _collect_card_permissions(self, card: dict) -> UserPermissions:
        name_level, info_level = self._shared_field_levels()
        return UserPermissions(
            name=name_level,
            info=info_level,
            can_add_entry=card["can_add"].isChecked(),
            can_delete_entry=card["can_delete"].isChecked(),
            can_save=card["can_save"].isChecked(),
        )

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

        name_level, info_level = self._shared_field_levels()
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
        slot_permissions: list[UserPermissions] = [
            UserPermissions(name=name_level, info=info_level)
            for _ in range(total)
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
            slot_permissions.append(
                UserPermissions(name=name_level, info=info_level)
            )
        while len(slot_labels) < len(user_passwords):
            slot_labels.append(
                tr("user_default_label", n=len(slot_labels) + 1)
            )

        effective_admin = admin_new or self._admin_password
        admin_changed = bool(admin_new and admin_new != self._admin_password)
        if (
            not passwords_are_unique(effective_admin, user_passwords)
            or self._conflicts_with_preserved_passwords(
                effective_admin,
                user_passwords,
                admin_changed=admin_changed,
            )
        ):
            self._warn(tr("pwd_not_available"))
            return

        shared = UserPermissions(name=name_level, info=info_level)
        first_enabled = next(
            (p for (en, _), p in zip(user_passwords, slot_permissions) if en),
            shared,
        )
        # Ortak alan seviyelerini tüm aktif slotlara yaz
        for index, (enabled, _) in enumerate(user_passwords):
            if not enabled:
                continue
            slot_permissions[index] = UserPermissions(
                name=name_level,
                info=info_level,
                can_add_entry=slot_permissions[index].can_add_entry,
                can_delete_entry=slot_permissions[index].can_delete_entry,
                can_save=slot_permissions[index].can_save,
            )

        new_enabled = [enabled for enabled, _ in user_passwords]
        old_slot_dicts = [
            self._vault.permissions_for_slot(i + 1).to_dict()
            for i in range(max(len(self._vault.user_slot_permissions), total))
        ]
        new_slot_dicts = [p.to_dict() for p in slot_permissions]
        changed = (
            bool(admin_new)
            or self._passwords_changed
            or new_slot_dicts != old_slot_dicts
            or shared.to_dict() != self._vault.user_permissions.to_dict()
            or slot_labels != list(self._vault.user_slot_labels)
            or new_enabled != list(self._enabled_flags)
        )
        self._result = {
            "user_passwords": user_passwords,
            "permissions": first_enabled,
            "slot_permissions": slot_permissions,
            "passwords_changed": self._passwords_changed,
            "user_slot_labels": slot_labels,
            "admin_current": admin_current,
            "admin_new": admin_new if admin_new else None,
            "changed": changed,
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result
