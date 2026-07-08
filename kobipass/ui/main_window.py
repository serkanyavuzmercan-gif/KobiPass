"""
kobiPass ana pencere: rol tabanlı kasa yönetimi.
"""

from __future__ import annotations

import copy
from pathlib import Path

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from kobipass.crypto import (
    AccessDeniedError,
    VaultCryptoError,
    build_vault_file,
    read_vault_file,
    write_vault_file,
    write_vault_file_updated,
)
from kobipass.i18n import crypto_message, i18n, tr
from kobipass.permissions import (
    diff_entries_for_audit,
    effective_permissions,
)
from kobipass.resources import app_icon
from kobipass.session import AdminSession, Session, UserSession, session_from_unlock
from kobipass.ui.about_dialog import AboutDialog
from kobipass.ui.add_record_bar import AddRecordBar
from kobipass.ui.audit_log_dialog import AuditLogDialog
from kobipass.ui.dialogs import (
    HelpDialog,
    OpenPasswordDialog,
    SetupVaultDialog,
    show_error,
    show_info,
)
from kobipass.ui.entry_row import EntryRowWidget
from kobipass.ui.landing_page import LandingPage
from kobipass.ui.title_bar import CustomTitleBar
from kobipass.ui.theme import ThemeManager, theme_manager
from kobipass.ui.user_admin_dialog import UserAdminDialog
from kobipass.vault_model import KobiVault, VaultEntry


class MainWindow(QMainWindow):
    """kobiPass ana uygulama penceresi."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app_name"))
        self.setWindowIcon(app_icon())
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self.setMinimumSize(1200, 700)
        self.resize(1280, 760)

        self._current_path: Path | None = None
        self._dirty = False
        self._row_widgets: list[EntryRowWidget] = []
        self._help_dialog: HelpDialog | None = None
        self._about_dialog: AboutDialog | None = None
        self._showing_copy_notice = False
        self._copy_notice_field = ""
        self._copy_notice_has_text = True

        self._vault: KobiVault | None = None
        self._session: Session | None = None
        self._snapshot_entries: list[VaultEntry] = []
        self._pending_user_passwords: list[tuple[bool, str]] | None = None
        self._kilitli_mi = False

        self._build_ui()
        self._copy_notice_timer = QTimer(self)
        self._copy_notice_timer.setSingleShot(True)
        self._copy_notice_timer.timeout.connect(self._end_copy_notice)
        i18n.language_changed.connect(self._retranslate_ui)
        self._retranslate_ui()
        self._apply_session_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._title_bar = CustomTitleBar(self)
        outer.addWidget(self._title_bar)

        self._stacked_widget = QStackedWidget()
        outer.addWidget(self._stacked_widget, stretch=1)

        self._landing_page = LandingPage()
        self._stacked_widget.addWidget(self._landing_page)

        self._vault_view = QWidget()
        root = QVBoxLayout(self._vault_view)
        root.setContentsMargins(10, 8, 16, 10)
        root.setSpacing(8)
        self._stacked_widget.addWidget(self._vault_view)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._btn_open = QPushButton()
        self._btn_open.clicked.connect(self._open_vault)
        toolbar.addWidget(self._btn_open, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_save = QPushButton()
        self._btn_save.setObjectName("primaryBtn")
        self._btn_save.clicked.connect(self._save_vault)
        toolbar.addWidget(self._btn_save, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_users = QPushButton()
        self._btn_users.clicked.connect(self._manage_users)
        toolbar.addWidget(self._btn_users, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_audit = QPushButton()
        self._btn_audit.clicked.connect(self._show_audit)
        toolbar.addWidget(self._btn_audit, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_clear = QPushButton()
        self._btn_clear.setObjectName("clearBtn")
        self._btn_clear.clicked.connect(self._clear_vault)
        toolbar.addWidget(self._btn_clear, 0, Qt.AlignmentFlag.AlignVCenter)

        toolbar.addStretch()

        self._btn_security = QPushButton()
        self._btn_security.setObjectName("headerSecurityBtn")
        self._btn_security.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_security.clicked.connect(self._open_security_dialog)
        toolbar.addWidget(self._btn_security, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_theme = QPushButton(ThemeManager.button_label())
        self._btn_theme.setObjectName("themeBtn")
        self._btn_theme.setFixedWidth(56)
        self._btn_theme.clicked.connect(theme_manager.toggle)
        toolbar.addWidget(self._btn_theme, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_lang = QPushButton("TR/EN")
        self._btn_lang.setObjectName("langBtn")
        self._btn_lang.setFixedWidth(50)
        self._btn_lang.clicked.connect(i18n.toggle)
        toolbar.addWidget(self._btn_lang, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_help = QPushButton()
        self._btn_help.setObjectName("helpBtn")
        self._btn_help.clicked.connect(self._show_help)
        toolbar.addWidget(self._btn_help, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addLayout(toolbar)

        self.security_badge = QPushButton()
        self.security_badge.setObjectName("securityBadge")
        self.security_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.security_badge.clicked.connect(self._open_security_dialog)

        badge_layout = QHBoxLayout()
        badge_layout.addWidget(self.security_badge)
        badge_layout.addStretch()
        badge_layout.setContentsMargins(0, 5, 0, 10)
        root.addLayout(badge_layout)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._entries_host = QWidget()
        self._entries_host.setObjectName("entriesContainer")
        self._entries_host.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )
        self._entries_layout = QVBoxLayout(self._entries_host)
        self._entries_layout.setContentsMargins(0, 0, 0, 0)
        self._entries_layout.setSpacing(4)
        self._entries_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._add_bar = AddRecordBar(self._add_row)
        self._entries_layout.addWidget(self._add_bar)

        self._scroll.setWidget(self._entries_host)
        root.addWidget(self._scroll, stretch=1)

        status = QStatusBar()
        self.setStatusBar(status)
        self._status_left = QLabel()
        status.addWidget(self._status_left, 1)
        self._status_role = QLabel("")
        status.addPermanentWidget(self._status_role)
        self._status_right = QLabel("")
        status.addPermanentWidget(self._status_right)
        self._add_row()

        self._landing_page.btn_open_file.clicked.connect(self._landing_open_file)
        self._landing_page.btn_login.clicked.connect(self._landing_register)
        self._landing_page.btn_security.clicked.connect(self._open_security_dialog)
        self._landing_page.btn_help.clicked.connect(self._show_help)

        self._show_landing_page()

    def _show_landing_page(self) -> None:
        self._stacked_widget.setCurrentWidget(self._landing_page)
        self.statusBar().hide()

    def _show_vault_view(self) -> None:
        self._stacked_widget.setCurrentWidget(self._vault_view)
        self.statusBar().show()

    def _landing_open_file(self) -> None:
        self._open_vault()

    def _landing_register(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        self._current_path = None
        self._session = None
        self._vault = None
        self._snapshot_entries = []
        self._pending_user_passwords = None
        self._save_new_vault([])

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.winId()
        self.setWindowIcon(app_icon())
        self._title_bar.capture_normal_geometry()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self._guvenlik_kilidini_aktif_et()
            elif event.oldState() & Qt.WindowState.WindowMinimized:
                if getattr(self, "_kilitli_mi", False):
                    self._kilit_ekranini_goster()
        super().changeEvent(event)

    def _guvenlik_kilidini_aktif_et(self) -> None:
        if self._session is None:
            return

        self._kilitli_mi = True

        for i in range(self._entries_layout.count()):
            item = self._entries_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, "set_sensitive_shown"):
                    widget.set_sensitive_shown(False)

    def _kilit_ekranini_goster(self) -> None:
        pass

    def _role_label(self) -> str:
        if self._session is None:
            return ""
        if isinstance(self._session, AdminSession):
            return tr("role_admin")
        return tr("role_user", slot=self._session.user_slot)

    def _apply_session_ui(self) -> None:
        is_unlocked = self._session is not None
        is_admin = isinstance(self._session, AdminSession)

        self._btn_users.setVisible(is_admin)
        self._btn_audit.setVisible(is_admin)

        perms = (
            effective_permissions(self._session, self._vault.user_permissions)
            if self._vault and self._session
            else None
        )

        can_add = perms.can_add_entry if perms else True
        can_delete = perms.can_delete_entry if perms else True
        can_save = perms.can_save if perms else True

        self._add_bar.set_visible_bar(can_add)
        self._btn_save.setEnabled(can_save if is_unlocked else True)

        for row in self._row_widgets:
            row.set_can_delete(can_delete)
            if perms:
                row.apply_permissions(perms)

        self._update_tab_order()

        title = tr("app_name")
        if is_unlocked:
            title = f"{title} — {self._role_label()}"
        self.setWindowTitle(title)
        self._update_status()

    def _retranslate_ui(self) -> None:
        self._btn_open.setText(tr("btn_open"))
        self._btn_save.setText(tr("btn_save"))
        self._btn_users.setText(tr("btn_users"))
        self._btn_audit.setText(tr("btn_audit"))
        self._btn_clear.setText(tr("btn_clear"))
        self._btn_lang.setToolTip(tr("btn_lang_tip"))
        self._btn_theme.setToolTip(tr("btn_theme_tip"))
        self._btn_help.setText(tr("btn_help"))
        self._btn_help.setToolTip(tr("btn_help_tip"))
        self._btn_security.setText(tr("btn_security"))
        self._btn_security.setToolTip(tr("security_badge_tip"))
        self.security_badge.setText(tr("security_badge"))
        self.security_badge.setToolTip(tr("security_badge_tip"))
        self._btn_help.style().unpolish(self._btn_help)
        self._btn_help.style().polish(self._btn_help)
        self._btn_help.setFixedWidth(self._btn_help.sizeHint().width())
        self._title_bar.retranslate()
        self._landing_page.retranslate()
        self._add_bar.retranslate()
        for row in self._row_widgets:
            row.retranslate()
        if self._help_dialog is not None:
            self._help_dialog.retranslate()
        if self._about_dialog is not None:
            self._about_dialog.retranslate()
        if self._showing_copy_notice:
            if self._copy_notice_has_text:
                self._status_left.setText(
                    tr("copy_notice", field=self._copy_notice_field)
                )
            else:
                self._status_left.setText(tr("copy_notice_empty"))
        else:
            self._update_status()
        self._apply_session_ui()

    def show_copy_notice(self, field_label: str, has_text: bool) -> None:
        self._copy_notice_field = field_label
        self._copy_notice_has_text = has_text
        self._copy_notice_timer.stop()
        self._showing_copy_notice = True
        self._status_left.setStyleSheet("color: #3ddc84; font-weight: 600;")
        if has_text:
            self._status_left.setText(tr("copy_notice", field=field_label))
        else:
            self._status_left.setText(tr("copy_notice_empty"))
        self._copy_notice_timer.start(2200)

    def _end_copy_notice(self) -> None:
        self._showing_copy_notice = False
        self._status_left.setStyleSheet("")
        self._update_status()

    def _update_status(self) -> None:
        if self._showing_copy_notice:
            return
        filled_count = len(self._collect_entries())
        if filled_count == 0:
            self._status_left.setText(tr("status_no_records"))
        else:
            self._status_left.setText(tr("status_records", count=filled_count))

        path_txt = (
            str(self._current_path) if self._current_path else tr("status_unsaved")
        )
        dirty_txt = tr("status_dirty") if self._dirty else ""
        self._status_right.setText(tr("status_file", path=f"{path_txt}{dirty_txt}"))

        role_txt = self._role_label()
        self._status_role.setText(
            tr("status_role", role=role_txt) if role_txt else ""
        )

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._update_status()

    def _clear_dirty(self) -> None:
        self._dirty = False
        self._update_status()

    def _update_tab_order(self) -> None:
        edits: list = []
        for row in self._row_widgets:
            edits.extend(row.focus_edits())
        for prev, nxt in zip(edits, edits[1:]):
            QWidget.setTabOrder(prev, nxt)

    def _collect_entries(self) -> list[VaultEntry]:
        entries: list[VaultEntry] = []
        for row in self._row_widgets:
            e = row.to_entry()
            if not e.has_content():
                continue
            entries.append(e)
        return entries

    def _sync_vault_entries(self) -> None:
        if self._vault is not None:
            self._vault.entries = self._collect_entries()

    def _add_row(self, entry: VaultEntry | None = None) -> None:
        row = EntryRowWidget()
        row.changed.connect(self._mark_dirty)
        row.remove_requested.connect(self._remove_row)
        if entry:
            row.block_change_signals(True)
            row.load_entry(entry)
            row.block_change_signals(False)

        idx = self._entries_layout.indexOf(self._add_bar)
        self._entries_layout.insertWidget(idx, row)
        self._row_widgets.append(row)
        self._apply_session_ui()
        self._update_tab_order()

    def _remove_row(self, row: EntryRowWidget) -> None:
        if row not in self._row_widgets:
            return
        if len(self._row_widgets) <= 1:
            show_error(self, tr("warn_title"), tr("warn_min_row"))
            return
        self._row_widgets.remove(row)
        self._entries_layout.removeWidget(row)
        row.deleteLater()
        self._mark_dirty()
        self._update_tab_order()

    def _clear_all_rows(self) -> None:
        for row in list(self._row_widgets):
            self._entries_layout.removeWidget(row)
            row.deleteLater()
        self._row_widgets.clear()

    def _load_vault_data(self, vault: KobiVault) -> None:
        self._vault = vault
        self._clear_all_rows()
        if not vault.entries:
            self._add_row()
        else:
            for entry in vault.entries:
                self._add_row(entry)
        self._snapshot_entries = copy.deepcopy(vault.entries)
        self._clear_dirty()
        for row in self._row_widgets:
            row.set_sensitive_shown(False)
        self._apply_session_ui()

    def _open_security_dialog(self) -> None:
        if self._about_dialog is None:
            self._about_dialog = AboutDialog(self)
        self._about_dialog.show()
        self._about_dialog.raise_()
        self._about_dialog.activateWindow()

    def _show_help(self) -> None:
        if self._help_dialog is None:
            self._help_dialog = HelpDialog(self)
        self._help_dialog.show()
        self._help_dialog.raise_()
        self._help_dialog.activateWindow()

    def _manage_users(self) -> None:
        if not isinstance(self._session, AdminSession) or self._vault is None:
            show_error(self, tr("warn_title"), tr("warn_locked"))
            return
        enabled = [slot.enabled for slot in self._session.keys.user_slots]  # type: ignore[union-attr]
        dlg = UserAdminDialog(self._vault, enabled, self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        data = dlg.result_data()
        if not data:
            return
        self._vault.user_permissions = data["permissions"]
        self._pending_user_passwords = data["user_passwords"]
        if isinstance(self._session, AdminSession):
            self._session.user_passwords = data["user_passwords"]
        self._mark_dirty()
        self._apply_session_ui()

    def _show_audit(self) -> None:
        if not isinstance(self._session, AdminSession) or self._vault is None:
            show_error(self, tr("warn_title"), tr("warn_locked"))
            return
        dlg = AuditLogDialog(self._vault, self)
        dlg.exec()

    def _clear_vault(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        self._current_path = None
        self._vault = None
        self._session = None
        self._snapshot_entries = []
        self._pending_user_passwords = None
        self._load_vault_data(KobiVault())
        self._apply_session_ui()
        self._show_landing_page()

    def _confirm_discard(self) -> bool:
        box = QMessageBox(self)
        box.setWindowIcon(app_icon())
        box.setWindowTitle(tr("discard_title"))
        box.setText(tr("discard_text"))
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        yes_btn = box.button(QMessageBox.StandardButton.Yes)
        no_btn = box.button(QMessageBox.StandardButton.No)
        if yes_btn:
            yes_btn.setText(tr("yes"))
        if no_btn:
            no_btn.setText(tr("no"))
        return box.exec() == QMessageBox.StandardButton.Yes

    def _save_vault(self) -> None:
        entries = self._collect_entries()
        if not entries:
            show_error(
                self,
                tr("err_no_records_title"),
                tr("err_no_records_save"),
            )
            return

        if self._session is None:
            self._save_new_vault(entries)
            return

        if isinstance(self._session, UserSession):
            if not self._vault or not self._session.keys:
                return
            if not self._vault.user_permissions.can_save:
                return
            self._sync_vault_entries()
            new_entries = self._collect_entries()
            logs = diff_entries_for_audit(
                self._snapshot_entries,
                new_entries,
                self._session,
                self._vault.user_permissions,
            )
            self._vault.audit_log.extend(logs)
            try:
                new_keys = write_vault_file_updated(
                    self._current_path,  # type: ignore[arg-type]
                    self._vault,
                    self._session.keys,
                )
                self._session.keys = new_keys
            except VaultCryptoError as exc:
                show_error(self, tr("err_save_title"), crypto_message(str(exc)))
                return
            self._snapshot_entries = copy.deepcopy(new_entries)
            self._clear_dirty()
            show_info(
                self,
                tr("saved_title"),
                tr("saved_text", path=str(self._current_path)),
            )
            return

        if isinstance(self._session, AdminSession):
            self._save_admin_vault(entries)

    def _save_new_vault(self, entries: list[VaultEntry]) -> None:
        default_name = "vault.enc"
        start_dir = str(Path.home())
        if self._current_path:
            default_name = self._current_path.name
            start_dir = str(self._current_path.parent)

        path_str, _ = QFileDialog.getSaveFileName(
            self,
            tr("dlg_save_vault"),
            str(Path(start_dir) / default_name),
            f"{tr('filter_enc')};;{tr('filter_all')}",
        )
        if not path_str:
            return

        dlg = SetupVaultDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        data = dlg.result_data()
        if not data:
            return

        vault = KobiVault(
            entries=entries,
            user_permissions=data["permissions"],
        )
        path = Path(path_str)
        try:
            write_vault_file(
                path,
                vault,
                data["admin_password"],
                data["user_passwords"],
            )
            unlock = read_vault_file(path, data["admin_password"])
            self._session = session_from_unlock(
                unlock, data["admin_password"], unlock.vault
            )
            if isinstance(self._session, AdminSession):
                self._session.user_passwords = data["user_passwords"]
        except VaultCryptoError as exc:
            show_error(self, tr("err_save_title"), crypto_message(str(exc)))
            return

        self._current_path = path
        self._load_vault_data(unlock.vault)
        self._show_vault_view()
        show_info(self, tr("saved_title"), tr("saved_text", path=path_str))

    def _save_admin_vault(self, entries: list[VaultEntry]) -> None:
        if not isinstance(self._session, AdminSession) or self._vault is None:
            return

        path = self._current_path
        if path is None:
            self._save_new_vault(entries)
            return

        self._sync_vault_entries()
        self._vault.entries = entries

        try:
            if self._pending_user_passwords is not None and self._session.keys:
                new_keys = write_vault_file_updated(
                    path,
                    self._vault,
                    self._session.keys,
                    self._pending_user_passwords,
                )
                self._session.keys = new_keys
                self._session.user_passwords = self._pending_user_passwords
                self._pending_user_passwords = None
            elif self._session.keys:
                new_keys = write_vault_file_updated(
                    path, self._vault, self._session.keys
                )
                self._session.keys = new_keys
            else:
                write_vault_file(
                    path,
                    self._vault,
                    self._session.admin_password,
                    self._session.user_passwords,
                )
                unlock = read_vault_file(path, self._session.admin_password)
                self._session.keys = unlock.keys
        except VaultCryptoError as exc:
            show_error(self, tr("err_save_title"), crypto_message(str(exc)))
            return

        self._snapshot_entries = copy.deepcopy(entries)
        self._clear_dirty()
        show_info(self, tr("saved_title"), tr("saved_text", path=str(path)))

    def _open_vault(self) -> None:
        if self._dirty and not self._confirm_discard():
            return

        path_str, _ = QFileDialog.getOpenFileName(
            self,
            tr("dlg_open_vault"),
            str(self._current_path.parent if self._current_path else Path.home()),
            f"{tr('filter_enc')};;{tr('filter_all')}",
        )
        if not path_str:
            return
        self._unlock_path(Path(path_str))

    def _unlock_path(self, path: Path) -> None:
        dlg = OpenPasswordDialog(path.name, self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        password = dlg.password()
        if not password:
            return

        try:
            unlock = read_vault_file(path, password)
        except AccessDeniedError:
            show_error(self, tr("denied_title"), tr("denied_text"))
            return
        except VaultCryptoError as exc:
            show_error(self, tr("file_err_title"), crypto_message(str(exc)))
            return

        session = session_from_unlock(unlock, password, unlock.vault)
        if isinstance(session, AdminSession):
            session.keys = unlock.keys

        self._current_path = path
        self._session = session
        self._pending_user_passwords = None
        self._load_vault_data(unlock.vault)
        self._show_vault_view()
        show_info(
            self,
            tr("opened_title"),
            tr("opened_text", count=len(unlock.vault.entries)),
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._dirty:
            box = QMessageBox(self)
            box.setWindowIcon(app_icon())
            box.setWindowTitle(tr("exit_title"))
            box.setText(tr("exit_text"))
            save_btn = box.addButton(tr("exit_save"), QMessageBox.ButtonRole.AcceptRole)
            discard_btn = box.addButton(
                tr("exit_discard"), QMessageBox.ButtonRole.DestructiveRole
            )
            cancel_btn = box.addButton(tr("exit_cancel"), QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(save_btn)
            box.exec()

            clicked = box.clickedButton()
            if clicked == cancel_btn:
                event.ignore()
                return
            if clicked == save_btn:
                self._save_vault()
                if self._dirty:
                    event.ignore()
                    return
        event.accept()
