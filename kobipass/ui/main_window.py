"""
kobiPass ana pencere: rol tabanlı kasa yönetimi.
"""

from __future__ import annotations

import copy
from pathlib import Path

from PyQt6.QtCore import QEvent, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
    read_vault_file,
    verify_password_against_keys,
    write_vault_file,
    write_vault_file_updated,
)
from kobipass.export import export_format_from_path, export_vault_csv, export_vault_json
from kobipass.i18n import crypto_message, i18n, tr
from kobipass.permissions import (
    diff_entries_for_audit,
    effective_permissions,
    view_only_permissions,
)
from kobipass.resources import app_icon
from kobipass.session import AdminSession, Session, UserSession, session_from_unlock
from kobipass.settings import add_recent_file, get_clipboard_clear_ms, get_idle_lock_ms
from kobipass.ui.about_dialog import AboutDialog
from kobipass.ui.add_record_bar import AddRecordBar
from kobipass.ui.audit_log_dialog import AuditLogDialog
from kobipass.ui.dialogs import (
    HelpDialog,
    OpenPasswordDialog,
    SetupVaultDialog,
    UnlockDialog,
    show_error,
    show_info,
)
from kobipass.ui.entry_row import ROW_MIME, EntryRowWidget
from kobipass.ui.landing_page import LandingPage
from kobipass.ui.theme import ThemeManager, theme_manager
from kobipass.ui.title_bar import CustomTitleBar
from kobipass.ui.user_admin_dialog import UserAdminDialog
from kobipass.vault_model import KobiVault, UserPermissions, VaultEntry

_FILTER_PAGE_SIZE = 100
_FILTER_DEBOUNCE_MS = 300


class WorkerThread(QThread):
    """Arama filtrelemesini arka planda çalıştırır."""

    finished = pyqtSignal(list)

    def __init__(self, vault_data: list[VaultEntry], search_term: str) -> None:
        super().__init__()
        self.data = vault_data
        self.term = search_term

    def run(self) -> None:
        term = self.term
        if not term:
            self.finished.emit(list(self.data))
            return
        result = [
            entry
            for entry in self.data
            if term in entry.name.lower()
            or term in entry.info1.lower()
            or any(term in value.lower() for value in entry.more_infos)
        ]
        self.finished.emit(result)


class EntriesHost(QWidget):
    """Kayıt satırları konteyneri — satır sürükle-bırak hedefini taşır."""

    row_drop = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasFormat(ROW_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(ROW_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        if event.mimeData().hasFormat(ROW_MIME):
            self.row_drop.emit(event)
            event.acceptProposedAction()
        else:
            event.ignore()


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
        self._pending_admin_password: str | None = None
        self._kilitli_mi = False
        self._worker: WorkerThread | None = None
        self._filter_request_id = 0
        self._display_entries: list[VaultEntry] | None = None
        self._loading_batch = False

        self._build_ui()
        self._copy_notice_timer = QTimer(self)
        self._copy_notice_timer.setSingleShot(True)
        self._copy_notice_timer.timeout.connect(self._end_copy_notice)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._run_filter)
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._on_idle_timeout)
        i18n.language_changed.connect(self._retranslate_ui)
        self._retranslate_ui()
        self._apply_session_ui()
        self.setAcceptDrops(True)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._reset_idle_timer()

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
        self.landing_page = self._landing_page
        self.stacked_widget = self._stacked_widget

        self._vault_view = QWidget()
        root = QVBoxLayout(self._vault_view)
        root.setContentsMargins(10, 8, 16, 10)
        root.setSpacing(8)
        self._stacked_widget.addWidget(self._vault_view)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._btn_home = QPushButton("🏠")
        self._btn_home.setObjectName("homeBtn")
        self._btn_home.setFixedWidth(42)
        self._btn_home.setToolTip(tr("btn_home_tip"))
        self._btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_home.clicked.connect(self._go_home)
        toolbar.addWidget(self._btn_home, 0, Qt.AlignmentFlag.AlignVCenter)

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

        self._btn_export = QPushButton()
        self._btn_export.clicked.connect(self._export_vault)
        toolbar.addWidget(self._btn_export, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_clear = QPushButton()
        self._btn_clear.setObjectName("clearBtn")
        self._btn_clear.clicked.connect(self._clear_vault)
        toolbar.addWidget(self._btn_clear, 0, Qt.AlignmentFlag.AlignVCenter)

        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText(tr("search_placeholder"))
        self._search_bar.textChanged.connect(self._filter_rows)
        toolbar.addWidget(self._search_bar)

        toolbar.addStretch()

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
        self._scroll.setAcceptDrops(True)
        self._scroll.viewport().setAcceptDrops(True)

        self._entries_host = EntriesHost()
        self._entries_host.setObjectName("entriesContainer")
        self._entries_host.row_drop.connect(self._handle_row_drop)
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
        self._scroll.verticalScrollBar().valueChanged.connect(self._check_scroll_position)
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

        self.landing_page.btn_open_file.clicked.connect(self._mevcut_dosyayi_ac)
        self.landing_page.btn_create_file.clicked.connect(
            self._yeni_dosya_olusturma_ekranini_ac
        )
        self.landing_page.btn_security.clicked.connect(self._guvenlik_penceresini_ac)
        self._landing_page.btn_help.clicked.connect(self._show_help)
        self._landing_page.recent_file_chosen.connect(self._open_recent_path)

        self._show_landing_page()

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
        ):
            self._reset_idle_timer()
        return super().eventFilter(obj, event)

    def _reset_idle_timer(self) -> None:
        self._idle_timer.stop()
        if self._session is not None and not self._kilitli_mi:
            self._idle_timer.start(get_idle_lock_ms())

    def _on_idle_timeout(self) -> None:
        if self._session is not None and not self._kilitli_mi:
            self._guvenlik_kilidini_aktif_et()
            self._kilit_ekranini_goster()

    def _show_landing_page(self) -> None:
        self._stacked_widget.setCurrentWidget(self._landing_page)
        self.statusBar().hide()
        self._landing_page.refresh_recent()

    def _show_vault_view(self) -> None:
        self._stacked_widget.setCurrentWidget(self._vault_view)
        self.statusBar().show()

    def _go_home(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        self._show_landing_page()

    def _mevcut_dosyayi_ac(self) -> None:
        self._open_vault()

    def _open_recent_path(self, path_str: str) -> None:
        if self._dirty and not self._confirm_discard():
            return
        self._unlock_path(Path(path_str))

    def _yeni_dosya_olusturma_ekranini_ac(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        self._current_path = None
        self._session = None
        self._vault = None
        self._snapshot_entries = []
        self._pending_user_passwords = None
        self._pending_admin_password = None
        self._kilitli_mi = False
        self._load_vault_data(KobiVault())
        self._show_vault_view()

    def _guvenlik_penceresini_ac(self) -> None:
        self._open_security_dialog()

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
        self._idle_timer.stop()
        for row in self._row_widgets:
            row.set_sensitive_shown(False)
        self._update_status()

    def _kilit_ekranini_goster(self) -> None:
        if not self._kilitli_mi or self._session is None:
            return
        keys = getattr(self._session, "keys", None)
        if keys is None:
            self._kilitli_mi = False
            return

        while self._kilitli_mi:
            dlg = UnlockDialog(self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                # Kullanıcı iptal ederse kilitli kalır; hassas alanlar gizli.
                self._update_status()
                return
            password = dlg.password() or ""
            if verify_password_against_keys(keys, password):
                self._kilitli_mi = False
                self._reset_idle_timer()
                self._update_status()
                return
            show_error(self, tr("lock_title"), tr("lock_wrong"))

    def _role_label(self) -> str:
        if self._session is None:
            return ""
        if isinstance(self._session, AdminSession):
            return tr("role_admin")
        return tr("role_user", slot=self._session.user_slot)

    def _row_permissions(self) -> tuple[UserPermissions | None, bool]:
        if not self._vault or not self._session:
            return None, False
        perms = effective_permissions(self._session, self._vault)
        view_only = not isinstance(self._session, AdminSession)
        if view_only:
            perms = view_only_permissions(perms)
        return perms, view_only

    def _apply_row_permissions(self) -> None:
        perms, view_only = self._row_permissions()
        labels = self._vault.resolved_field_labels() if self._vault else {}
        if not perms:
            for row in self._row_widgets:
                row.apply_field_labels(labels)
            return
        for row in self._row_widgets:
            row.apply_permissions(perms, view_only=view_only)
            row.apply_field_labels(labels)

    def _apply_session_ui(self) -> None:
        is_unlocked = self._session is not None
        is_admin = isinstance(self._session, AdminSession)

        self._btn_users.setVisible(is_admin)
        self._btn_audit.setVisible(is_admin)
        self._btn_export.setVisible(is_admin)

        perms, view_only = self._row_permissions()

        can_add = perms.can_add_entry if perms else self._session is None
        can_delete = perms.can_delete_entry if perms else True
        can_save = perms.can_save if perms else True

        self._add_bar.setVisible(can_add and not self._kilitli_mi)
        self._btn_save.setEnabled((can_save if is_unlocked else True) and not self._kilitli_mi)

        self._apply_row_permissions()
        for row in self._row_widgets:
            row.set_can_delete(can_delete and not view_only and not self._kilitli_mi)

        self._update_tab_order()

        title = tr("app_name")
        if is_unlocked:
            title = f"{title} — {self._role_label()}"
        self.setWindowTitle(title)
        self._update_status()

    def _filter_rows(self, text: str) -> None:
        if not self._vault:
            return
        self._search_timer.stop()
        self._search_timer.start(_FILTER_DEBOUNCE_MS)

    def _run_filter(self) -> None:
        if not self._vault:
            return
        self._filter_request_id += 1
        request_id = self._filter_request_id
        self._worker = WorkerThread(
            list(self._vault.entries),
            self._search_bar.text().lower().strip(),
        )
        self._worker.finished.connect(
            lambda results, req_id=request_id: self._apply_filter_results(
                results, req_id
            )
        )
        self._worker.start()

    def _apply_filter_results(
        self, filtered_entries: list[VaultEntry], request_id: int
    ) -> None:
        if request_id != self._filter_request_id:
            return
        self._merge_row_edits_into_vault()
        self._display_entries = filtered_entries
        self._clear_all_rows()
        for entry in filtered_entries[:_FILTER_PAGE_SIZE]:
            self._add_row(
                entry,
                vault_index=self._vault_entry_index(entry, 0),
                refresh_session=False,
            )
        if not self._row_widgets:
            self._add_row(refresh_session=False)
        self._apply_session_ui()
        self._update_tab_order()

    def _check_scroll_position(self, value: int) -> None:
        bar = self._scroll.verticalScrollBar()
        if bar.maximum() <= 0:
            return
        if value > bar.maximum() * 0.9:
            self._load_next_batch()

    def _load_next_batch(self) -> None:
        if not self._vault or self._loading_batch:
            return
        source = (
            self._display_entries
            if self._display_entries is not None
            else self._vault.entries
        )
        current_count = len(self._row_widgets)
        next_batch = source[current_count : current_count + _FILTER_PAGE_SIZE]
        if not next_batch:
            return
        self._loading_batch = True
        try:
            for entry in next_batch:
                self._add_row(
                    entry,
                    vault_index=self._vault_entry_index(entry, current_count),
                    refresh_session=False,
                )
                current_count += 1
            self._apply_session_ui()
            self._update_tab_order()
        finally:
            self._loading_batch = False

    def _vault_entry_index(self, entry: VaultEntry, fallback: int) -> int:
        if self._vault is None:
            return fallback
        try:
            return self._vault.entries.index(entry)
        except ValueError:
            return fallback

    def _merge_row_edits_into_vault(self) -> None:
        if self._vault is None:
            return
        for row in self._row_widgets:
            entry = row.to_entry()
            vault_index = row.vault_index
            if vault_index is not None and 0 <= vault_index < len(self._vault.entries):
                self._vault.entries[vault_index] = entry

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasFormat(ROW_MIME):
            event.acceptProposedAction()
            return
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(ROW_MIME) or event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files and files[0].endswith(".enc"):
            self._unlock_path(Path(files[0]))
            event.acceptProposedAction()
            return
        event.ignore()

    def _handle_row_drop(self, event: QDropEvent) -> None:
        if self._vault is None or self._is_view_only_session() or self._kilitli_mi:
            return
        raw = bytes(event.mimeData().data(ROW_MIME)).decode("utf-8")
        try:
            source_index = int(raw)
        except ValueError:
            return

        local_pos = event.position().toPoint()
        target_index = self._row_index_at(local_pos)
        if target_index is None:
            target_index = len(self._vault.entries) - 1
        if source_index == target_index:
            return
        if not (0 <= source_index < len(self._vault.entries)):
            return

        self._merge_row_edits_into_vault()
        entry = self._vault.entries.pop(source_index)
        target_index = max(0, min(target_index, len(self._vault.entries)))
        self._vault.entries.insert(target_index, entry)
        self._display_entries = list(self._vault.entries)
        self._reload_visible_rows()
        self._mark_dirty()

    def _row_index_at(self, local_pos) -> int | None:
        for row in self._row_widgets:
            if row.geometry().contains(local_pos) and row.vault_index is not None:
                return row.vault_index
        return None
    def _reload_visible_rows(self) -> None:
        if self._vault is None:
            return
        source = (
            self._display_entries
            if self._display_entries is not None
            else self._vault.entries
        )
        keep = max(len(self._row_widgets), _FILTER_PAGE_SIZE)
        self._clear_all_rows()
        for entry in source[:keep]:
            self._add_row(
                entry,
                vault_index=self._vault_entry_index(entry, 0),
                refresh_session=False,
            )
        if not self._row_widgets:
            self._add_row(refresh_session=False)
        self._apply_session_ui()

    def _retranslate_ui(self) -> None:
        self._btn_home.setText("🏠")
        self._btn_home.setToolTip(tr("btn_home_tip"))
        self._btn_save.setText(tr("btn_save"))
        self._btn_users.setText(tr("btn_users"))
        self._btn_audit.setText(tr("btn_audit"))
        self._btn_export.setText(tr("btn_export"))
        self._btn_export.setToolTip(tr("btn_export_tip"))
        self._btn_clear.setText(tr("btn_clear"))
        self._btn_lang.setToolTip(tr("btn_lang_tip"))
        self._btn_theme.setToolTip(tr("btn_theme_tip"))
        self._search_bar.setPlaceholderText(tr("search_placeholder"))
        self.security_badge.setText(tr("security_badge"))
        self.security_badge.setToolTip(tr("security_badge_tip"))
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
        seconds = max(1, get_clipboard_clear_ms() // 1000)
        if has_text:
            self._status_left.setText(
                f"{tr('copy_notice', field=field_label)} — "
                f"{tr('status_clipboard_clear', seconds=seconds)}"
            )
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
        if self._kilitli_mi:
            self._status_left.setText(tr("status_locked"))
        else:
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
        self._merge_row_edits_into_vault()
        if self._vault is not None:
            entries = list(self._vault.entries)
            for row in self._row_widgets:
                if row.vault_index is not None:
                    continue
                entry = row.to_entry()
                if entry.has_content():
                    entries.append(entry)
            return [entry for entry in entries if entry.has_content()]

        entries: list[VaultEntry] = []
        for row in self._row_widgets:
            entry = row.to_entry()
            if not entry.has_content():
                continue
            entries.append(entry)
        return entries

    def _sync_vault_entries(self) -> None:
        if self._vault is not None:
            self._vault.entries = self._collect_entries()

    def _is_view_only_session(self) -> bool:
        return self._session is not None and not isinstance(self._session, AdminSession)

    def _add_row(
        self,
        entry: VaultEntry | None = None,
        vault_index: int | None = None,
        *,
        refresh_session: bool = True,
    ) -> None:
        row = EntryRowWidget()
        row.vault_index = vault_index
        row.changed.connect(self._mark_dirty)
        row.remove_requested.connect(self._remove_row)
        if entry:
            row.block_change_signals(True)
            row.load_entry(entry)
            row.block_change_signals(False)

        idx = self._entries_layout.indexOf(self._add_bar)
        self._entries_layout.insertWidget(idx, row)
        self._row_widgets.append(row)
        if refresh_session:
            self._apply_session_ui()
        self._update_tab_order()

    def _remove_row(self, row: EntryRowWidget) -> None:
        if self._is_view_only_session() or self._kilitli_mi:
            return
        if row not in self._row_widgets:
            return
        if len(self._row_widgets) <= 1:
            show_error(self, tr("warn_title"), tr("warn_min_row"))
            return
        removed_index = row.vault_index
        self._row_widgets.remove(row)
        self._entries_layout.removeWidget(row)
        row.deleteLater()
        if (
            self._vault is not None
            and removed_index is not None
            and 0 <= removed_index < len(self._vault.entries)
        ):
            del self._vault.entries[removed_index]
            for other in self._row_widgets:
                if other.vault_index is not None and other.vault_index > removed_index:
                    other.vault_index -= 1
        self._mark_dirty()
        self._update_tab_order()

    def _clear_all_rows(self) -> None:
        for row in list(self._row_widgets):
            self._entries_layout.removeWidget(row)
            row.deleteLater()
        self._row_widgets.clear()

    def _load_vault_data(self, vault: KobiVault) -> None:
        self._vault = vault
        self._display_entries = list(vault.entries)
        self._search_bar.blockSignals(True)
        self._search_bar.clear()
        self._search_bar.blockSignals(False)
        self._clear_all_rows()
        visible_entries = vault.entries[:_FILTER_PAGE_SIZE]
        if not visible_entries:
            self._add_row(refresh_session=False)
        else:
            for index, entry in enumerate(visible_entries):
                self._add_row(entry, vault_index=index, refresh_session=False)
        self._snapshot_entries = copy.deepcopy(vault.entries)
        self._clear_dirty()
        for row in self._row_widgets:
            row.set_sensitive_shown(False)
        self._apply_session_ui()
        self._reset_idle_timer()

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

        if data.get("admin_new"):
            current = data.get("admin_current") or ""
            if current != self._session.admin_password:
                show_error(self, tr("warn_title"), tr("admin_pwd_wrong"))
                return
            self._pending_admin_password = data["admin_new"]
            self._session.admin_password = data["admin_new"]

        self._vault.user_permissions = data["permissions"]
        if data.get("slot_permissions"):
            self._vault.set_slot_permissions(data["slot_permissions"])
        self._vault.field_labels = data.get("field_labels", {})
        self._vault.user_slot_labels = data.get(
            "user_slot_labels", self._vault.user_slot_labels
        )
        self._vault.user_slot_usernames = data.get(
            "user_slot_usernames", self._vault.user_slot_usernames
        )
        self._pending_user_passwords = data["user_passwords"]
        self._session.user_passwords = data["user_passwords"]
        self._mark_dirty()
        self._apply_session_ui()

    def _show_audit(self) -> None:
        if not isinstance(self._session, AdminSession) or self._vault is None:
            show_error(self, tr("warn_title"), tr("warn_locked"))
            return
        dlg = AuditLogDialog(self._vault, self)
        dlg.exec()

    def _export_vault(self) -> None:
        if not isinstance(self._session, AdminSession) or self._vault is None:
            show_error(self, tr("warn_title"), tr("warn_locked"))
            return
        self._sync_vault_entries()
        default = "vault-export.json"
        if self._current_path:
            default = f"{self._current_path.stem}-export.json"
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            tr("dlg_export_vault"),
            str(Path.home() / default),
            tr("filter_export"),
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            if export_format_from_path(path) == "csv":
                export_vault_csv(self._vault, path)
            else:
                export_vault_json(self._vault, path)
        except OSError as exc:
            show_error(self, tr("err_save_title"), str(exc))
            return
        show_info(self, tr("exported_title"), tr("exported_text", path=str(path)))

    def _clear_vault(self) -> None:
        """Kasa ekranından çıkmadan tüm alanları temizler."""
        if self._dirty and not self._confirm_discard():
            return

        self._current_path = None
        self._vault = None
        self._session = None
        self._snapshot_entries = []
        self._pending_user_passwords = None
        self._pending_admin_password = None
        self._kilitli_mi = False
        self._load_vault_data(KobiVault())
        self._apply_session_ui()
        self._show_vault_view()

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
        if box.exec() == QMessageBox.StandardButton.Yes:
            self._clear_dirty()
            return True
        return False

    def _save_vault(self) -> None:
        if self._kilitli_mi:
            self._kilit_ekranini_goster()
            if self._kilitli_mi:
                return
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
            if not self._vault.permissions_for_slot(self._session.user_slot).can_save:
                return
            self._sync_vault_entries()
            new_entries = self._collect_entries()
            logs = diff_entries_for_audit(
                self._snapshot_entries,
                new_entries,
                self._session,
                self._vault.permissions_for_slot(self._session.user_slot),
                self._vault,
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

        vault = KobiVault(entries=entries)
        vault.user_slot_labels = data.get(
            "user_slot_labels", vault.user_slot_labels
        )
        vault.user_slot_usernames = data.get(
            "user_slot_usernames", vault.user_slot_usernames
        )
        if data.get("slot_permissions"):
            vault.set_slot_permissions(data["slot_permissions"])
        else:
            base = data["permissions"]
            vault.set_slot_permissions(
                [UserPermissions.from_dict(base.to_dict()) for _ in range(3)]
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
        add_recent_file(path)
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
            if self._session.keys:
                new_keys = write_vault_file_updated(
                    path,
                    self._vault,
                    self._session.keys,
                    self._pending_user_passwords,
                    admin_password=self._pending_admin_password,
                )
                self._session.keys = new_keys
                if self._pending_user_passwords is not None:
                    self._session.user_passwords = self._pending_user_passwords
                self._pending_user_passwords = None
                self._pending_admin_password = None
            else:
                write_vault_file(
                    path,
                    self._vault,
                    self._session.admin_password,
                    self._session.user_passwords,
                )
                unlock = read_vault_file(path, self._session.admin_password)
                self._session.keys = unlock.keys
                self._pending_user_passwords = None
                self._pending_admin_password = None
        except VaultCryptoError as exc:
            show_error(self, tr("err_save_title"), crypto_message(str(exc)))
            return

        add_recent_file(path)
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
        self._pending_admin_password = None
        self._kilitli_mi = False
        add_recent_file(path)
        self._load_vault_data(unlock.vault)
        self._show_vault_view()
        self._landing_page.refresh_recent()
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
