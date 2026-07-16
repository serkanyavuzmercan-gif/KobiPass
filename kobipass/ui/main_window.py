"""
kobiPass ana pencere: rol tabanlı kasa yönetimi.
"""

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import QEvent, QThread, QTimer, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
    QScreen,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from kobipass.crypto import (
    AccessDeniedError,
    VaultCryptoError,
    VaultFileKeys,
    password_matches_admin,
    password_matches_user_slot,
    read_vault_file,
    write_vault_file,
    write_vault_file_updated,
)
from kobipass.i18n import crypto_message, i18n, localize_default_tab_name, tr
from kobipass.permissions import (
    diff_entries_for_audit,
    effective_permissions,
)
from kobipass.platform_win import enable_native_window_features
from kobipass.resources import app_icon
from kobipass.session import AdminSession, Session, UserSession, session_from_unlock
from kobipass.settings import (
    add_recent_file,
    get_clipboard_clear_ms,
    get_idle_lock_ms,
    get_recent_files,
)
from kobipass.ui.about_dialog import AboutDialog
from kobipass.ui.add_record_bar import AddRecordBar
from kobipass.ui.audit_log_dialog import AuditLogDialog
from kobipass.ui.dialogs import (
    OpenPasswordDialog,
    SetupVaultDialog,
    ask_yes_no,
    show_error,
    show_info,
    show_restriction as show_restriction_dialog,
)
from kobipass.ui.entry_row import ROW_MIME, EntryRowWidget
from kobipass.ui.landing_page import LandingPage
from kobipass.ui.lock_overlay import LockOverlay
from kobipass.ui.security_dialog import SecurityDialog
from kobipass.ui.vault_summary_panel import VaultSummaryPanel
from kobipass.backup import (
    clear_read_only,
    create_backup,
    find_backups,
    restore_backup,
    set_read_only,
)
from kobipass.ui.icons import (
    icon_chevron_left,
    icon_history,
    icon_home,
    icon_info,
    icon_more,
    icon_save,
    icon_search,
    icon_shield,
    icon_sun,
    icon_theme,
    icon_users,
)
from kobipass.ui.tab_bar import VaultTabBar
from kobipass.ui.theme import theme_manager
from kobipass.ui.title_bar import CustomTitleBar
from kobipass.ui.user_admin_dialog import UserAdminDialog
from kobipass.ui.vault_settings_dialog import VaultSettingsDialog
from kobipass.ui.vault_empty_state import (
    VaultBody,
    VaultEmptyState,
    should_show_empty_state,
)
from kobipass.vault_model import (
    KobiVault,
    UserPermissions,
    VaultEntry,
    VaultTab,
    utc_now_iso,
)

_FILTER_PAGE_SIZE = 100
_FILTER_DEBOUNCE_MS = 300


class ClickableLabel(QLabel):
    """Sol tıklamada sinyal veren etiket (durum çubuğundaki 'Yönetici' yazısı)."""

    clicked = pyqtSignal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


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
        # Bırakma göstergesi: satırların arasında beliren ince yatay çizgi.
        # Düzene dahil değildir; sürükleme sırasında elle konumlanır.
        self._marker = QFrame(self)
        self._marker.setObjectName("rowDropMarker")
        self._marker.hide()

    def _show_marker(self, pos) -> None:
        rows = sorted(
            (w for w in self.findChildren(EntryRowWidget) if w.isVisible()),
            key=lambda w: w.y(),
        )
        if not rows:
            self._marker.hide()
            return
        y = pos.y()
        marker_y = rows[-1].geometry().bottom() + 1
        for row in rows:
            if y < row.y() + row.height() / 2:
                marker_y = max(0, row.y() - 2)
                break
        self._marker.setGeometry(6, marker_y, max(2, self.width() - 12), 3)
        self._marker.show()
        self._marker.raise_()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasFormat(ROW_MIME):
            self._show_marker(event.position().toPoint())
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(ROW_MIME):
            self._show_marker(event.position().toPoint())
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._marker.hide()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._marker.hide()
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
        # Boyut ekran oranına göre sabitlenir; köşeden büyütme kapalı.
        self._screen_geom_wired: QScreen | None = None
        self._geometry_ready = False

        self._current_path: Path | None = None
        self._dirty = False
        self._last_saved_at: datetime | None = None
        self._last_access_at: datetime | None = None
        self._row_widgets: list[EntryRowWidget] = []
        self._about_dialog: AboutDialog | None = None
        self._security_dialog: SecurityDialog | None = None
        self._active_tab_id: str | None = None
        self._showing_copy_notice = False
        self._copy_notice_field = ""
        self._copy_notice_has_text = True
        # Frameless pencere kenarından yeniden boyutlandırma.
        self._resize_margin = 6
        self._resize_cursor_active = False

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
        # İlk boyut: primary screen oranına göre (showEvent yeniden hizalar).
        self._title_bar.apply_screen_ratio_geometry(recenter=True)

    def _wire_screen_sizing(self) -> None:
        """Ekran değişince pencereyi yeni ekrana oranlı olarak yeniden hizala."""
        handle = self.windowHandle()
        if handle is not None:
            try:
                handle.screenChanged.disconnect(self._on_window_screen_changed)
            except TypeError:
                pass
            handle.screenChanged.connect(self._on_window_screen_changed)
        self._bind_screen_geometry(self.screen())

    def _bind_screen_geometry(self, screen: QScreen | None) -> None:
        if self._screen_geom_wired is not None:
            try:
                self._screen_geom_wired.availableGeometryChanged.disconnect(
                    self._on_available_geometry_changed
                )
            except TypeError:
                pass
            self._screen_geom_wired = None
        if screen is None:
            return
        screen.availableGeometryChanged.connect(self._on_available_geometry_changed)
        self._screen_geom_wired = screen

    def _on_window_screen_changed(self, screen: QScreen | None) -> None:
        self._bind_screen_geometry(screen)
        self._title_bar.apply_screen_ratio_geometry(recenter=True)

    def _on_available_geometry_changed(self) -> None:
        # Görev çubuğu (otomatik gizle) sık sık bu sinyali tetikler; kullanıcının
        # seçtiği boyut/konumu sıfırlamayalım. Ekranı kaplıysa yeni alana uydur;
        # değilse pencere ekran dışına taşmışsa/sığmıyorsa güvenli boyuta çek.
        if getattr(self._title_bar, "_maximized", False):
            self._title_bar._maximize_to_available()
            return
        avail = self._available_screen_geometry()
        geom = self.geometry()
        too_big = geom.width() > avail.width() or geom.height() > avail.height()
        off_screen = not avail.intersects(geom)
        if too_big or off_screen:
            self._title_bar.apply_screen_ratio_geometry(recenter=True)

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

        # Kilit örtüsü: çalışma alanının üzerini tam kapatır (başlık çubuğu
        # açıkta kalır → kapat/küçült çalışır). Başlangıçta gizli.
        self._lock_overlay = LockOverlay(central)
        self._lock_overlay.unlock_requested.connect(self._on_lock_unlock)
        self._lock_overlay.home_requested.connect(self._on_lock_home)
        self._lock_overlay.hide()

        self._landing_page = LandingPage()
        self._stacked_widget.addWidget(self._landing_page)
        self.landing_page = self._landing_page
        self.stacked_widget = self._stacked_widget

        self._vault_view = QWidget()
        root = QVBoxLayout(self._vault_view)
        root.setContentsMargins(10, 8, 16, 10)
        root.setSpacing(8)
        self._stacked_widget.addWidget(self._vault_view)

        self._command_surface = QFrame()
        self._command_surface.setObjectName("vaultCommandSurface")
        self._command_surface.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        command_layout = QVBoxLayout(self._command_surface)
        command_layout.setContentsMargins(8, 8, 8, 7)
        command_layout.setSpacing(7)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._btn_home = QPushButton()
        self._btn_home.setObjectName("homeBtn")
        self._btn_home.setIcon(icon_home())
        self._btn_home.setFixedWidth(42)
        self._btn_home.setToolTip(tr("btn_home_tip"))
        self._btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_home.clicked.connect(self._go_home)
        toolbar.addWidget(self._btn_home, 0, Qt.AlignmentFlag.AlignVCenter)

        _tb_icon = QColor("#c4ccdb")
        self._btn_save = QPushButton()
        self._btn_save.setObjectName("primaryBtn")
        self._btn_save.setIcon(icon_save(QColor("#ffffff"), size=17))
        self._btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_save.clicked.connect(self._save_vault)
        toolbar.addWidget(self._btn_save, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_users = QPushButton()
        self._btn_users.setIcon(icon_users(_tb_icon, size=17))
        self._btn_users.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_users.clicked.connect(self._manage_users)
        toolbar.addWidget(self._btn_users, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_audit = QPushButton()
        self._btn_audit.setIcon(icon_history(_tb_icon, size=17))
        self._btn_audit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_audit.clicked.connect(self._show_audit)
        toolbar.addWidget(self._btn_audit, 0, Qt.AlignmentFlag.AlignVCenter)


        self._search_bar = QLineEdit()
        self._search_bar.setObjectName("toolbarSearch")
        self._search_bar.addAction(
            icon_search(QColor("#8a90a0"), size=16),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self._search_bar.setPlaceholderText(tr("search_placeholder"))
        self._search_bar.setMinimumWidth(160)
        self._search_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._search_bar.textChanged.connect(self._filter_rows)
        # Search fills leftover width; theme/lang stay right-aligned with fixed spacing.
        toolbar.addWidget(self._search_bar, 1, Qt.AlignmentFlag.AlignVCenter)

        # Tema/dil düğmeleri artık üst başlık çubuğunda.
        command_layout.addLayout(toolbar)

        # Rozet/ipucu satırının yerine Excel benzeri sekme çubuğu.
        self._tab_bar = VaultTabBar()
        self._tab_bar.tab_selected.connect(self._on_tab_selected)
        self._tab_bar.add_requested.connect(self._on_add_tab)
        self._tab_bar.rename_requested.connect(self._on_rename_tab)
        self._tab_bar.toggle_hidden_requested.connect(self._on_toggle_hidden_tab)
        self._tab_bar.delete_requested.connect(self._on_delete_tab)
        self._tab_bar.reordered.connect(self._on_tabs_reordered)

        badge_layout = QHBoxLayout()
        badge_layout.setSpacing(8)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.addWidget(self._tab_bar, 1)
        command_layout.addLayout(badge_layout)

        root.addWidget(self._command_surface)

        self._vault_body = VaultBody()
        self._scroll = self._vault_body.scroll
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll.setAcceptDrops(True)
        self._scroll.viewport().setAcceptDrops(True)

        self._entries_host = EntriesHost()
        self._entries_host.setObjectName("entriesContainer")
        self._entries_host.row_drop.connect(self._handle_row_drop)
        self._entries_host.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )
        self._entries_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._entries_layout = QVBoxLayout(self._entries_host)
        # Yatay boşluk: satırlar/ekle çubuğu kart kenarına yapışmasın, başlıkla
        # (16px) hizalı dursun.
        self._entries_layout.setContentsMargins(16, 6, 16, 10)
        self._entries_layout.setSpacing(4)
        self._entries_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._add_bar = AddRecordBar(self._request_add_row)
        self._entries_layout.addWidget(self._add_bar)

        self._empty_state = VaultEmptyState()
        self._empty_state.add_requested.connect(self._on_empty_state_add)
        self._entries_layout.addWidget(self._empty_state, stretch=1)

        self._scroll.setWidget(self._entries_host)
        self._scroll.verticalScrollBar().valueChanged.connect(self._check_scroll_position)

        records_panel = QFrame()
        records_panel.setObjectName("recordsPanel")
        records_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        records_layout = QVBoxLayout(records_panel)
        records_layout.setContentsMargins(0, 0, 0, 0)
        records_layout.setSpacing(0)

        records_header = QHBoxLayout()
        records_header.setContentsMargins(16, 12, 16, 10)
        records_header.setSpacing(8)
        records_header_icon = QLabel()
        records_header_icon.setPixmap(
            icon_shield(QColor("#8296ff"), size=15).pixmap(15, 15)
        )
        records_header.addWidget(records_header_icon, 0)
        self._records_panel_title = QLabel()
        self._records_panel_title.setObjectName("recordsPanelTitle")
        records_header.addWidget(self._records_panel_title, 0)
        records_header.addStretch(1)
        records_layout.addLayout(records_header)
        records_layout.addWidget(self._vault_body, 1)

        self._summary_panel = VaultSummaryPanel()
        self._summary_panel.collapse_requested.connect(self._collapse_summary)

        # Özet paneli gizliyken sağ kenarda görünen ince 'aç' tutamacı.
        self._summary_reopen_btn = QPushButton()
        self._summary_reopen_btn.setObjectName("summaryReopenBtn")
        self._summary_reopen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._summary_reopen_btn.setIcon(icon_chevron_left(QColor("#8a93a8"), size=15))
        self._summary_reopen_btn.setFixedWidth(22)
        self._summary_reopen_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self._summary_reopen_btn.clicked.connect(self._expand_summary)
        self._summary_reopen_btn.hide()

        body_row = QHBoxLayout()
        body_row.setSpacing(14)
        body_row.addWidget(records_panel, 1)
        body_row.addWidget(self._summary_panel, 0)
        body_row.addWidget(self._summary_reopen_btn, 0)
        root.addLayout(body_row, 1)

        status = QStatusBar()
        status.setObjectName("vaultStatusBar")
        self.setStatusBar(status)
        status_left_wrap = QWidget()
        status_left_layout = QHBoxLayout(status_left_wrap)
        status_left_layout.setContentsMargins(0, 0, 0, 0)
        status_left_layout.setSpacing(6)
        self._status_info_icon = QLabel()
        self._status_info_icon.setPixmap(
            icon_info(QColor("#7a869f"), size=13).pixmap(13, 13)
        )
        self._status_info_icon.setToolTip(tr("status_info_tip"))
        status_left_layout.addWidget(self._status_info_icon, 0)
        self._status_left = QLabel()
        self._status_left.setObjectName("statusCount")
        status_left_layout.addWidget(self._status_left, 0)
        status_left_layout.addStretch(1)
        status.addWidget(status_left_wrap, 1)
        self._status_role = ClickableLabel("")
        self._status_role.setObjectName("statusRole")
        self._status_role.clicked.connect(self._change_admin_password)
        status.addPermanentWidget(self._status_role)
        self._status_file_wrap = QWidget()
        self._status_file_wrap.setObjectName("statusFileWrap")
        self._status_file_wrap.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True
        )
        file_status = QHBoxLayout(self._status_file_wrap)
        # İç boşluğu düzen kenar boşluğuyla ver (QSS padding, düzeni içeri
        # itmediği için dosya adı kenarlığa taşıp kırpılıyordu).
        file_status.setContentsMargins(9, 3, 9, 3)
        file_status.setSpacing(6)
        self._status_file_name = QLabel("")
        self._status_file_name.setObjectName("statusFile")
        self._status_unsaved_dot = QLabel()
        self._status_unsaved_dot.setObjectName("statusUnsavedDot")
        self._status_unsaved_dot.setFixedSize(7, 7)
        self._status_unsaved_label = QLabel()
        self._status_unsaved_label.setObjectName("statusUnsavedLabel")
        file_status.addWidget(self._status_file_name)
        file_status.addWidget(self._status_unsaved_dot)
        file_status.addWidget(self._status_unsaved_label)
        status.addPermanentWidget(self._status_file_wrap)
        self._status_menu_btn = QPushButton()
        self._status_menu_btn.setObjectName("statusMenuBtn")
        self._status_menu_btn.setIcon(icon_more(QColor("#8994ad"), size=16))
        self._status_menu_btn.setFixedSize(26, 22)
        self._status_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._status_menu_btn.clicked.connect(self._show_status_menu)
        status.addPermanentWidget(self._status_menu_btn)
        self._refresh_empty_state()

        self.landing_page.btn_open_file.clicked.connect(self._mevcut_dosyayi_ac)
        self.landing_page.btn_create_file.clicked.connect(
            self._yeni_dosya_olusturma_ekranini_ac
        )
        self._landing_page.recent_file_chosen.connect(self._open_recent_path)

        # Güvenlik/Hakkında düğmeleri artık üst başlık çubuğunda.
        self._title_bar.btn_security.clicked.connect(self._guvenlik_penceresini_ac)
        self._title_bar.btn_about.clicked.connect(self._open_about_dialog)

        self._setup_shortcuts()

        self._show_landing_page()
        # Açılışta silinmiş kasa tespiti — pencere göründükten sonra sor.
        QTimer.singleShot(0, self._check_missing_vaults)

    def _setup_shortcuts(self) -> None:
        """Klavye kısayolları: kaydet, ara, kayıt ekle, kilitle."""
        QShortcut(QKeySequence.StandardKey.Save, self, activated=self._shortcut_save)
        QShortcut(QKeySequence.StandardKey.Find, self, activated=self._shortcut_find)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._shortcut_add_row)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self._shortcut_lock)

    def _shortcut_save(self) -> None:
        if self._session is not None and self._btn_save.isEnabled():
            self._save_vault()

    def _shortcut_find(self) -> None:
        if self._session is not None and not self._kilitli_mi:
            self._search_bar.setFocus()
            self._search_bar.selectAll()

    @staticmethod
    def _can_add_record(perms: UserPermissions | None) -> bool:
        if perms is None:
            return True
        has_writable_field = perms.name == "write" or perms.info == "write"
        return perms.can_add_entry and has_writable_field

    def _show_restriction(self, message_key: str) -> None:
        show_restriction_dialog(self, tr(message_key))

    def _request_add_row(self) -> None:
        if self._kilitli_mi:
            return
        if not self._can_add_record(self._row_permissions()):
            self._show_restriction("restricted_add_record")
            return
        self._add_row()

    def _on_empty_state_add(self) -> None:
        before = len(self._row_widgets)
        self._request_add_row()
        if len(self._row_widgets) > before:
            edits = self._row_widgets[-1].focus_edits()
            if edits:
                edits[0].setFocus()

    def _refresh_empty_state(self) -> None:
        perms = self._row_permissions()
        add_allowed = self._can_add_record(perms)
        if (
            should_show_empty_state(len(self._row_widgets))
            and not self._kilitli_mi
            and add_allowed
        ):
            # Onboarding ekranı yerine doğrudan boş, odaklı bir kayıt satırı
            # sunulur — kullanıcı hiç ara adım görmeden yazmaya başlar.
            self._add_row(refresh_session=False)
            # Otomatik eklenen satır da oturum yetkilerini almalı; aksi halde
            # yönetici bile 'bilgi alanı ekle' (+) yapamaz (satır varsayılan
            # olarak read yetkisiyle gelir).
            self._apply_row_permissions()
            if self._row_widgets:
                edits = self._row_widgets[-1].focus_edits()
                if edits:
                    edits[0].setFocus()
            return
        show = should_show_empty_state(len(self._row_widgets)) and not self._kilitli_mi
        self._empty_state.setVisible(show)
        self._empty_state.set_restricted(not add_allowed)
        # Stretch yalnızca boş durumda — kayıt varken aralıkları sıkıştırmaz.
        self._entries_layout.setStretchFactor(self._empty_state, 1 if show else 0)
        if show:
            self._empty_state.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        else:
            self._empty_state.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
            )
        has_rows = len(self._row_widgets) > 0
        if has_rows:
            self._add_bar.setVisible(not self._kilitli_mi)
            self._add_bar.set_restricted(
                not add_allowed,
                tr("restricted_add_record") if not add_allowed else "",
            )
        else:
            self._add_bar.setVisible(False)

    def _shortcut_add_row(self) -> None:
        if self._kilitli_mi:
            return
        if len(self._row_widgets) == 0:
            self._on_empty_state_add()
            return
        self._request_add_row()

    def _shortcut_lock(self) -> None:
        if self._session is not None and not self._kilitli_mi:
            self._guvenlik_kilidini_aktif_et()
            self._kilit_ekranini_goster()

    def eventFilter(self, obj, event):  # noqa: N802
        etype = event.type()
        if etype in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
        ):
            self._reset_idle_timer()
        if etype in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
            if self._handle_edge_resize(obj, event):
                return True
        return super().eventFilter(obj, event)

    # ── Frameless kenar/köşe yeniden boyutlandırma ───────────────────────────
    def _resize_edges_at(self, pos) -> int:
        """Verilen (pencereye göreli) noktanın hangi kenarlara yakın olduğunu
        Qt.Edge bayrak değerlerinin toplamı (int) olarak döndürür."""
        m = self._resize_margin
        rect = self.rect()
        edges = 0
        if pos.x() <= m:
            edges |= Qt.Edge.LeftEdge.value
        if pos.x() >= rect.width() - m:
            edges |= Qt.Edge.RightEdge.value
        if pos.y() <= m:
            edges |= Qt.Edge.TopEdge.value
        if pos.y() >= rect.height() - m:
            edges |= Qt.Edge.BottomEdge.value
        return edges

    def _cursor_for_edges(self, edges: int):
        left = edges & Qt.Edge.LeftEdge.value
        right = edges & Qt.Edge.RightEdge.value
        top = edges & Qt.Edge.TopEdge.value
        bottom = edges & Qt.Edge.BottomEdge.value
        if (top and left) or (bottom and right):
            return Qt.CursorShape.SizeFDiagCursor
        if (top and right) or (bottom and left):
            return Qt.CursorShape.SizeBDiagCursor
        if left or right:
            return Qt.CursorShape.SizeHorCursor
        if top or bottom:
            return Qt.CursorShape.SizeVerCursor
        return None

    def _set_resize_cursor(self, shape) -> None:
        if shape is None:
            self._clear_resize_cursor()
            return
        if self._resize_cursor_active:
            QApplication.changeOverrideCursor(QCursor(shape))
        else:
            QApplication.setOverrideCursor(QCursor(shape))
            self._resize_cursor_active = True

    def _clear_resize_cursor(self) -> None:
        if self._resize_cursor_active:
            QApplication.restoreOverrideCursor()
            self._resize_cursor_active = False

    def _handle_edge_resize(self, obj, event) -> bool:
        # Yalnızca bu pencereye ait widget'lar için; diyalog/başka pencere değil.
        if not isinstance(obj, QWidget) or obj.window() is not self:
            return False
        # Karşılama/kilit fark etmez; yalnızca ekranı kaplı değilken ve normal
        # pencere durumunda kenar boyutlandırması yapılır.
        if getattr(self._title_bar, "_maximized", False) or self.isMaximized():
            self._clear_resize_cursor()
            return False
        # Köşe tutamacı (QStatusBar size grip) kendi işini yapsın.
        if isinstance(obj, QSizeGrip):
            self._clear_resize_cursor()
            return False
        # Etkileşimli kontrollerin (düğme/metin kutusu) tıklamasını çalma;
        # aksi halde üst kenara yakın oturan başlık düğmeleri (küçült/kapla/
        # kapat) kenar boyutlandırması tarafından yutulur.
        if isinstance(obj, (QAbstractButton, QLineEdit)):
            self._clear_resize_cursor()
            return False
        try:
            global_pos = event.globalPosition().toPoint()
        except AttributeError:
            return False
        pos = self.mapFromGlobal(global_pos)
        if not self.rect().contains(pos):
            self._clear_resize_cursor()
            return False
        edges = self._resize_edges_at(pos)
        if event.type() == QEvent.Type.MouseMove:
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                self._set_resize_cursor(self._cursor_for_edges(edges))
            return False
        # MouseButtonPress
        if (
            event.button() == Qt.MouseButton.LeftButton
            and edges
        ):
            handle = self.windowHandle()
            if handle is not None:
                self._clear_resize_cursor()
                handle.startSystemResize(Qt.Edge(edges))
                return True
        return False

    def _reset_idle_timer(self) -> None:
        self._idle_timer.stop()
        if self._session is not None and not self._kilitli_mi:
            self._idle_timer.start(get_idle_lock_ms())

    def _on_idle_timeout(self) -> None:
        if self._session is not None and not self._kilitli_mi:
            self._guvenlik_kilidini_aktif_et()
            self._kilit_ekranini_goster()

    def _clear_lock_state(self) -> None:
        """Kilit örtüsünü kapatır ve çalışma alanını yeniden etkinleştirir.

        Kilitliyken durum/başlık çubuğundaki düğmeler (Yeni kasa, Ana sayfa…)
        hâlâ tıklanabildiği için, kasa/görünüm değiştiren her yol bu temizliği
        çağırmalı; aksi halde stacked widget 'disabled' kalır ve kullanıcı
        alanlara yazamaz."""
        self._kilitli_mi = False
        if hasattr(self, "_lock_overlay"):
            self._lock_overlay.hide()
        if hasattr(self, "_stacked_widget"):
            self._stacked_widget.setEnabled(True)

    def _show_landing_page(self) -> None:
        self._clear_lock_state()
        self._stacked_widget.setCurrentWidget(self._landing_page)
        self.statusBar().hide()
        self._landing_page.refresh_recent()

    def _show_vault_view(self) -> None:
        self._clear_lock_state()
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
        self._last_saved_at = None
        self._last_access_at = datetime.now()
        self._load_vault_data(KobiVault())
        self._show_vault_view()

    def _guvenlik_penceresini_ac(self) -> None:
        self._open_security_dialog()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.winId()
        self.setWindowIcon(app_icon())
        # Windows Snap / native boyutlandırma için WS stillerini etkinleştir.
        enable_native_window_features(self)
        if not self._geometry_ready:
            self._wire_screen_sizing()
            self._title_bar.apply_screen_ratio_geometry(recenter=True)
            self._geometry_ready = True
        else:
            # show sonrası oran kilidini yenile (restore sonrası vs.)
            self._title_bar.apply_screen_ratio_geometry(recenter=False)
            self._title_bar.capture_normal_geometry()
        self._position_lock_overlay()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_lock_overlay()

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

    def _position_lock_overlay(self) -> None:
        """Örtüyü çalışma alanını (stacked widget) tam kaplayacak konumla."""
        if not hasattr(self, "_lock_overlay"):
            return
        self._lock_overlay.setGeometry(self._stacked_widget.geometry())

    def _kilit_ekranini_goster(self) -> None:
        """Kilit örtüsünü gösterir; opak örtü alttaki kasayı görsel ve fare
        olarak kapatır.

        NOT: Çalışma alanı ARTIK setEnabled(False) ile devre dışı bırakılmıyor.
        Opak, en üste alınmış örtü fareyi zaten yutar; disabled bırakmak,
        kullanıcı başlık/durum çubuğundaki düğmelerle (örtü dışında) başka bir
        görünüme geçtiğinde çalışma alanının 'kilitli/yazılamaz' kalmasına yol
        açıyordu. Örtü açıkken tek çıkış: doğru parola ya da 'Ana ekrana dön'.
        """
        if not self._kilitli_mi or self._session is None:
            return
        if getattr(self._session, "keys", None) is None:
            self._clear_lock_state()
            return
        self._lock_overlay.prepare()
        self._position_lock_overlay()
        self._lock_overlay.show()
        self._lock_overlay.raise_()
        self._lock_overlay.focus_password()

    def _on_lock_unlock(self, password: str) -> None:
        keys = getattr(self._session, "keys", None)
        if keys is None:
            self._on_lock_home()
            return
        # GÜVENLİK: Kilit YALNIZCA oturumun kendi kimliğiyle açılabilir.
        # Yönetici kilidi yalnızca yönetici parolasıyla; alt kullanıcı kilidi
        # yalnızca O kullanıcının slot parolasıyla açılır. Aksi halde,
        # kilitli bir yönetici oturumu bir alt kullanıcı parolasıyla açılıp
        # o kullanıcıya yönetici yetkisi kazandırırdı (yetki yükselmesi).
        if self._lock_password_matches_session(keys, password or ""):
            self._kilitli_mi = False
            self._lock_overlay.hide()
            self._stacked_widget.setEnabled(True)
            self._reset_idle_timer()
            self._update_status()
            self._apply_session_ui()
        else:
            self._lock_overlay.show_error(tr("lock_wrong"))

    def _lock_password_matches_session(
        self, keys: VaultFileKeys, password: str
    ) -> bool:
        """Girilen parola, kilitli oturumun KENDİ kimliğiyle eşleşiyor mu?"""
        if not password:
            return False
        if isinstance(self._session, UserSession):
            return password_matches_user_slot(
                keys, password, self._session.user_slot - 1
            )
        # Yönetici oturumu (veya keys taşıyan tek olası diğer durum).
        if isinstance(self._session, AdminSession):
            return password_matches_admin(keys, password)
        return False

    def _on_lock_home(self) -> None:
        """Kilitliyken 'Ana ekrana dön': oturumu bırakıp karşılamaya döner.

        GÜVENLİK: Normal kilitte (anahtar var) kaydedilmemiş değişiklikler
        ATILAMAZ — önce kilit açılmalı. Böylece kasa kilitliyken masaya gelen
        biri bu düğmeyle sahibinin çalışmasını silemez. Anahtarın olmadığı
        dejenere durumda kilit zaten açılamayacağı için kullanıcıyı
        hapsetmemek adına eski onaylı-atma akışına düşülür."""
        keys = getattr(self._session, "keys", None)
        if self._kilitli_mi and self._dirty and keys is not None:
            self._lock_overlay.show_error(tr("lock_unlock_first"))
            self._lock_overlay.focus_password()
            return
        if self._dirty and not self._confirm_discard():
            return
        self._kilitli_mi = False
        self._lock_overlay.hide()
        self._stacked_widget.setEnabled(True)
        self._session = None
        self._vault = None
        self._current_path = None
        self._snapshot_entries = []
        self._pending_user_passwords = None
        self._pending_admin_password = None
        self._clear_dirty()
        self._show_landing_page()

    def _role_label(self) -> str:
        if isinstance(self._session, UserSession):
            return tr("role_user", slot=self._session.user_slot)
        # Yönetici oturumu VEYA yeni/kaydedilmemiş kasa (onu oluşturan
        # yöneticidir). Karşılama ekranında durum çubuğu gizli olduğundan
        # kasa yokken (self._vault None) boş döneriz.
        if isinstance(self._session, AdminSession) or self._vault is not None:
            return tr("role_admin")
        return ""

    def _row_permissions(self) -> UserPermissions | None:
        """Oturumun etkin izinleri — yönetici şablonu kullanıcılar için AYNEN geçerlidir.

        Eski blanket salt-okunur kilit kaldırıldı: kullanıcı yalnızca yöneticinin
        'Düzenler' verdiği alanları düzenleyebilir; değişiklikler audit'e düşer.
        Herkesi salt-okunur isteyen yönetici şablonda yazma yetkisi vermez.
        """
        if not self._vault:
            return None
        if self._session is None:
            # Yeni / kaydedilmemiş kasa: onu oluşturan kişi yöneticidir ve tam
            # yetkiyle çalışır (alan ekle/sil, kaydet...). Karşılama ekranında
            # durum çubuğu gizli olduğu için bu görünmez, sorun olmaz.
            from kobipass.session import admin_permissions

            return admin_permissions()
        return effective_permissions(self._session, self._vault)

    def _apply_row_permissions(self) -> None:
        perms = self._row_permissions()
        labels = self._vault.resolved_field_labels() if self._vault else {}
        if not perms:
            for row in self._row_widgets:
                row.apply_field_labels(labels)
            return
        for row in self._row_widgets:
            row.apply_permissions(perms, view_only=False)
            row.apply_field_labels(labels)

    def _apply_session_ui(self) -> None:
        is_unlocked = self._session is not None
        is_admin = isinstance(self._session, AdminSession)

        # Yönetici düğmeleri her zaman görünür. Yalnızca alt kullanıcı
        # oturumunda sönük (kısıtlı) görünür; yeni/kaydedilmemiş kasada aktif
        # görünür ama basılınca 'önce kaydet' der (oluşturan yöneticidir).
        is_sub_user = isinstance(self._session, UserSession)
        for btn in (
            self._btn_users,
            self._btn_audit,
        ):
            btn.setVisible(True)
            btn.setProperty("restricted", is_sub_user)
            if is_sub_user:
                btn.setToolTip(tr("admin_needed_user"))
            elif self._session is None:
                btn.setToolTip(tr("admin_needed_new"))
            else:
                btn.setToolTip("")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        perms = self._row_permissions()

        can_delete = perms.can_delete_entry if perms else True
        can_save = perms.can_save if perms else True

        save_restricted = isinstance(self._session, UserSession) and not can_save
        self._btn_save.setEnabled(not self._kilitli_mi)
        self._btn_save.setProperty("restricted", save_restricted)
        self._btn_save.setToolTip(
            tr("restricted_save") if save_restricted else tr("btn_save")
        )
        self._btn_save.style().unpolish(self._btn_save)
        self._btn_save.style().polish(self._btn_save)

        # Satır sıralama: yönetici + kaydı değiştirme yetkisi olan (düzenleme /
        # ekleme / silme) alt kullanıcılar sürükleyerek sıralayabilir; yalnızca
        # görüntüleyen kullanıcı sıralayamaz.
        can_reorder = (
            is_admin or bool(perms and perms.can_mutate())
        ) and not self._kilitli_mi
        self._apply_row_permissions()
        for row in self._row_widgets:
            row.set_can_delete(can_delete and not self._kilitli_mi)
            row.set_can_reorder(can_reorder)

        self._update_tab_order()

        title = tr("app_name")
        if is_unlocked:
            title = f"{title} — {self._role_label()}"
        self.setWindowTitle(title)
        self._refresh_tab_bar()
        self._update_status()
        self._refresh_empty_state()

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
        self._apply_session_ui()
        self._update_tab_order()
        self._refresh_empty_state()

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
        # Sıralama: yönetici + kaydı değiştirme yetkisi olan alt kullanıcılar.
        # (Audit farkı artık KİMLİK bazlı olduğundan yeniden sıralama sahte
        # "değişti" kaydı üretmez; sıra değişimi tek bir kayıtla belirtilir.)
        perms = self._row_permissions()
        can_reorder = isinstance(self._session, AdminSession) or bool(
            perms and perms.can_mutate()
        )
        if self._vault is None or not can_reorder or self._kilitli_mi:
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
        self._apply_session_ui()
        self._refresh_empty_state()

    def _retranslate_ui(self) -> None:
        self._btn_home.setToolTip(tr("btn_home_tip"))
        self._btn_save.setText(tr("btn_save"))
        self._btn_users.setText(tr("btn_users"))
        self._btn_audit.setText(tr("btn_audit"))
        self._search_bar.setPlaceholderText(tr("search_placeholder"))
        self._refresh_tab_bar()
        self._records_panel_title.setText(tr("records_panel_title"))
        self._summary_reopen_btn.setToolTip(tr("summary_expand"))
        self._summary_panel.retranslate()
        self._title_bar.retranslate()
        self._landing_page.retranslate()
        self._lock_overlay.retranslate()
        self._add_bar.retranslate()
        self._empty_state.retranslate()
        for row in self._row_widgets:
            row.retranslate()
        if self._security_dialog is not None:
            self._security_dialog.retranslate()
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

        path_txt = self._current_path.name if self._current_path else tr("status_unsaved")
        self._status_file_wrap.setToolTip(
            str(self._current_path) if self._current_path else ""
        )
        self._status_file_name.setText(path_txt)
        is_unsaved = bool(self._dirty or self._current_path is None)
        self._status_unsaved_dot.setVisible(is_unsaved)
        self._status_unsaved_label.setVisible(is_unsaved)
        if is_unsaved:
            self._status_unsaved_label.setText(tr("status_unsaved_short"))

        role_txt = self._role_label()
        self._status_role.setText(
            tr("status_role", role=role_txt) if role_txt else ""
        )
        self._status_role.setVisible(bool(role_txt))
        # Yalnızca yönetici oturumunda 'Yönetici' yazısı tıklanabilir olsun
        # (buraya tıklayınca kasa parolası değiştirme ekranı açılır).
        is_admin = isinstance(self._session, AdminSession)
        self._status_role.setCursor(
            Qt.CursorShape.PointingHandCursor
            if is_admin
            else Qt.CursorShape.ArrowCursor
        )
        self._status_role.setToolTip(
            tr("admin_pwd_change_tip") if is_admin else ""
        )
        self._status_role.setProperty("clickable", is_admin)
        self._status_role.style().unpolish(self._status_role)
        self._status_role.style().polish(self._status_role)
        self._update_summary_panel()

    def _collapse_summary(self) -> None:
        self._summary_panel.hide()
        self._summary_reopen_btn.show()

    def _expand_summary(self) -> None:
        self._summary_reopen_btn.hide()
        self._summary_panel.show()

    @staticmethod
    def _format_stat_time(when: datetime | None) -> str:
        """İstatistik zamanı: Bugün/Dün HH:MM ya da GG.AA.YYYY; yoksa '—'."""
        if when is None:
            return "—"
        clock = when.strftime("%H:%M")
        today = datetime.now().date()
        delta = (today - when.date()).days
        if delta <= 0:
            return tr("date_today", time=clock)
        if delta == 1:
            return tr("date_yesterday", time=clock)
        return when.strftime("%d.%m.%Y")

    def _update_summary_panel(self) -> None:
        total_rows = len(self._row_widgets)
        total_cells = 0
        for row in self._row_widgets:
            total_cells += row.to_entry().max_info_index()
        if self._dirty or self._last_saved_at is None:
            last_saved_text = tr("summary_not_saved")
        else:
            last_saved_text = self._format_stat_time(self._last_saved_at)
        self._summary_panel.set_stats(
            total_rows=total_rows,
            total_cells=total_cells,
            last_access_text=self._format_stat_time(self._last_access_at),
            last_saved_text=last_saved_text,
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
            result = [entry for entry in entries if entry.has_content()]
            self._stamp_password_ages(result)
            return result

        entries: list[VaultEntry] = []
        for row in self._row_widgets:
            entry = row.to_entry()
            if not entry.has_content():
                continue
            entries.append(entry)
        self._stamp_password_ages(entries)
        return entries

    def _stamp_password_ages(self, entries: list[VaultEntry]) -> None:
        """info1 (parola) yüklü haline göre değiştiyse pw_updated_at'ı günceller.

        Yeniden sıralamaya karşı dayanıklı olsun diye eşleştirme isimle yapılır.
        Yeni kayıtta veya parola değişiminde 'şimdi' damgalanır; değişmediyse
        mevcut damga korunur.
        """
        baseline: dict[str, str] = {}
        for prev in self._snapshot_entries:
            baseline.setdefault(prev.name, prev.info1)
        now = utc_now_iso()
        for entry in entries:
            if not entry.info1:
                continue
            old = baseline.get(entry.name)
            if old is None or old != entry.info1:
                entry.pw_updated_at = now

    def _sync_vault_entries(self) -> None:
        if self._vault is not None:
            self._vault.entries = self._collect_entries()


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
        row.restricted_action.connect(self._show_restriction)
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
        self._refresh_empty_state()

    def _remove_row(self, row: EntryRowWidget) -> None:
        perms = self._row_permissions()
        if (perms is not None and not perms.can_delete_entry) or self._kilitli_mi:
            return
        if row not in self._row_widgets:
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
        self._refresh_empty_state()

    def _clear_all_rows(self) -> None:
        for row in list(self._row_widgets):
            self._entries_layout.removeWidget(row)
            row.deleteLater()
        self._row_widgets.clear()

    def _load_vault_data(self, vault: KobiVault) -> None:
        self._vault = vault
        self._set_active_tab_to_first_visible()
        self._reload_active_tab(reset_dirty=True)
        self._apply_session_ui()
        self._reset_idle_timer()
        self._refresh_empty_state()

    def _reload_active_tab(self, *, reset_dirty: bool) -> None:
        """Aktif sekmenin kayıtlarını satırlara yükler."""
        vault = self._vault
        if vault is None:
            return
        self._display_entries = list(vault.entries)
        self._search_bar.blockSignals(True)
        self._search_bar.clear()
        self._search_bar.blockSignals(False)
        self._clear_all_rows()
        for index, entry in enumerate(vault.entries[:_FILTER_PAGE_SIZE]):
            self._add_row(entry, vault_index=index, refresh_session=False)
        self._snapshot_entries = copy.deepcopy(vault.entries)
        if reset_dirty:
            self._clear_dirty()
        for row in self._row_widgets:
            row.set_sensitive_shown(False)

    # ── Sekme yönetimi ───────────────────────────────────────────────────
    def _visible_tabs(self) -> list[VaultTab]:
        """Bu oturumun görebildiği sekmeler (alt kullanıcıya gizli yok)."""
        if not self._vault:
            return []
        if isinstance(self._session, UserSession):
            return self._vault.normal_tabs()
        return list(self._vault.tabs)

    def _tab_mgmt_allowed(self) -> bool:
        """Sekme ekle/adlandır/gizle/sil yalnızca yöneticiye (alt kullanıcı değil)."""
        return self._vault is not None and not isinstance(
            self._session, UserSession
        )

    def _find_tab(self, tab_id: str) -> VaultTab | None:
        if not self._vault:
            return None
        for tab in self._vault.tabs:
            if tab.id == tab_id:
                return tab
        return None

    def _apply_active_index(self) -> None:
        """_active_tab_id → vault.active_index (entries property bunu izler)."""
        vault = self._vault
        if vault is None or not vault.tabs:
            return
        for index, tab in enumerate(vault.tabs):
            if tab.id == self._active_tab_id:
                vault.active_index = index
                return
        vault.active_index = 0
        self._active_tab_id = vault.tabs[0].id

    def _set_active_tab_to_first_visible(self) -> None:
        vault = self._vault
        if vault is None:
            self._active_tab_id = None
            return
        visible = self._visible_tabs()
        if visible:
            self._active_tab_id = visible[0].id
        elif vault.tabs:
            self._active_tab_id = vault.tabs[0].id
        self._apply_active_index()

    def _refresh_tab_bar(self) -> None:
        if not hasattr(self, "_tab_bar"):
            return
        if self._vault is None:
            self._tab_bar.set_tabs([], "", is_admin=False)
            return
        self._apply_active_index()
        # Sekme adları veri olarak saklanır; varsayılan adları ('Sekme'/'Sheet')
        # aktif dile çevirerek göster (kullanıcının verdiği adlar korunur).
        display = [
            SimpleNamespace(
                id=tab.id,
                name=localize_default_tab_name(tab.name),
                hidden=tab.hidden,
            )
            for tab in self._visible_tabs()
        ]
        self._tab_bar.set_tabs(
            display,
            self._active_tab_id or "",
            is_admin=self._tab_mgmt_allowed(),
        )

    def _on_tab_selected(self, tab_id: str) -> None:
        if self._vault is None or tab_id == self._active_tab_id:
            return
        if self._find_tab(tab_id) is None:
            return
        # Mevcut sekmedeki düzenlemeleri modele işle (kaybolmasın).
        self._sync_vault_entries()
        self._active_tab_id = tab_id
        self._apply_active_index()
        self._reload_active_tab(reset_dirty=False)
        self._apply_session_ui()

    def _next_tab_name(self) -> str:
        existing = {tab.name for tab in self._vault.tabs} if self._vault else set()
        base = tr("tab_default_name")
        if base not in existing:
            return base
        index = 2
        while tr("tab_new_name", n=index) in existing:
            index += 1
        return tr("tab_new_name", n=index)

    def _on_add_tab(self) -> None:
        if not self._tab_mgmt_allowed() or self._kilitli_mi:
            return
        self._sync_vault_entries()
        tab = VaultTab.new(self._next_tab_name())
        self._vault.tabs.append(tab)
        self._active_tab_id = tab.id
        self._apply_active_index()
        self._reload_active_tab(reset_dirty=False)
        self._mark_dirty()
        self._apply_session_ui()
        if self._row_widgets:
            edits = self._row_widgets[0].focus_edits()
            if edits:
                edits[0].setFocus()

    def _on_rename_tab(self, tab_id: str) -> None:
        if not self._tab_mgmt_allowed():
            return
        tab = self._find_tab(tab_id)
        if tab is None:
            return
        text, ok = QInputDialog.getText(
            self,
            tr("tab_rename_title"),
            tr("tab_rename_label"),
            text=localize_default_tab_name(tab.name),
        )
        if ok and text.strip():
            tab.name = text.strip()
            self._mark_dirty()
            self._refresh_tab_bar()

    def _on_toggle_hidden_tab(self, tab_id: str) -> None:
        if not self._tab_mgmt_allowed():
            return
        tab = self._find_tab(tab_id)
        if tab is None:
            return
        # Son görünür sekmeyi gizlemeye izin verme: alt kullanıcıların en az bir
        # normal sekmesi kalmalı (aksi halde boş bir kasa görürler).
        if not tab.hidden and len(self._vault.normal_tabs()) <= 1:
            show_info(self, tr("app_name"), tr("tab_cannot_hide_last"))
            return
        tab.hidden = not tab.hidden
        self._mark_dirty()
        self._apply_session_ui()
        show_info(
            self,
            tr("app_name"),
            tr("tab_made_hidden" if tab.hidden else "tab_made_normal", name=tab.name),
        )

    def _on_delete_tab(self, tab_id: str) -> None:
        if not self._tab_mgmt_allowed():
            return
        if self._vault is None or len(self._vault.tabs) <= 1:
            show_info(self, tr("tab_delete_title"), tr("tab_cannot_delete_last"))
            return
        tab = self._find_tab(tab_id)
        if tab is None:
            return
        # İçinde kayıt olan sekme doğrudan silinemez: kaza ile veri kaybını
        # önlemek için kullanıcı önce tüm kayıtları tek tek kaldırmalı.
        if any(e.has_content() for e in tab.entries):
            show_info(self, tr("tab_delete_title"), tr("tab_delete_needs_empty"))
            return
        # Silinen sekmenin görünür sekmeler içindeki konumu → silince en yakın
        # (aynı konuma kayan sonraki, o da yoksa önceki) sekmeye geç.
        visible_before = [t.id for t in self._visible_tabs()]
        try:
            pos = visible_before.index(tab_id)
        except ValueError:
            pos = 0
        was_active = self._active_tab_id == tab_id
        self._vault.tabs.remove(tab)
        if was_active:
            visible_after = self._visible_tabs()
            if visible_after:
                self._active_tab_id = visible_after[
                    min(pos, len(visible_after) - 1)
                ].id
            elif self._vault.tabs:
                self._active_tab_id = self._vault.tabs[0].id
            self._apply_active_index()
            self._reload_active_tab(reset_dirty=False)
        else:
            self._apply_active_index()
        self._mark_dirty()
        self._apply_session_ui()

    def _on_tabs_reordered(self, new_ids: list) -> None:
        """Yönetici sekmeleri sürükleyerek yeniden sıraladı: modeli buna göre diz."""
        if not self._tab_mgmt_allowed() or self._vault is None:
            return
        id_to_tab = {t.id: t for t in self._vault.tabs}
        reordered = [id_to_tab[i] for i in new_ids if i in id_to_tab]
        # Güvenlik: listede olmayan sekmeler (olmamalı) sona eklensin, kaybolmasın.
        for tab in self._vault.tabs:
            if tab not in reordered:
                reordered.append(tab)
        if [t.id for t in reordered] == [t.id for t in self._vault.tabs]:
            return  # sıra değişmedi
        self._vault.tabs = reordered
        self._apply_active_index()
        self._mark_dirty()
        self._refresh_tab_bar()

    def _open_security_dialog(self) -> None:
        if self._security_dialog is None:
            self._security_dialog = SecurityDialog(self)
        self._security_dialog.show()
        self._security_dialog.raise_()
        self._security_dialog.activateWindow()

    def _open_about_dialog(self) -> None:
        if self._about_dialog is None:
            self._about_dialog = AboutDialog(self)
        self._about_dialog.show()
        self._about_dialog.raise_()
        self._about_dialog.activateWindow()

    def _require_admin(self, restriction_key: str = "restricted_admin_feature") -> bool:
        """Yönetici değilse uygun açıklamayı gösterir ve False döner."""
        if isinstance(self._session, AdminSession) and self._vault is not None:
            return True
        if self._session is None:
            # Yeni / kaydedilmemiş dosya — önce kaydedip izinleri kur.
            show_info(self, tr("info_title"), tr("admin_needed_new"))
        else:
            self._show_restriction(restriction_key)
        return False

    def _manage_users(self) -> None:
        if not self._require_admin("restricted_manage_users"):
            return
        enabled = [slot.enabled for slot in self._session.keys.user_slots]  # type: ignore[union-attr]
        dlg = UserAdminDialog(
            self._vault,
            enabled,
            self,
            admin_password=self._session.admin_password,
            keys=self._session.keys,
        )
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        data = dlg.result_data()
        if not data:
            return

        self._vault.user_permissions = data["permissions"]
        if data.get("slot_permissions") is not None:
            self._vault.set_slot_permissions(data["slot_permissions"])
        self._vault.user_slot_labels = data.get(
            "user_slot_labels", self._vault.user_slot_labels
        )
        self._pending_user_passwords = data["user_passwords"]
        self._session.user_passwords = data["user_passwords"]
        self._mark_dirty()
        self._apply_session_ui()
        if data.get("changed"):
            show_info(self, tr("users_applied_title"), tr("users_applied_text"))

    def _show_status_menu(self) -> None:
        menu = QMenu(self)
        act_reveal = menu.addAction(tr("status_menu_reveal"))
        act_copy = menu.addAction(tr("status_menu_copy_path"))
        act_reveal.setEnabled(self._current_path is not None)
        act_copy.setEnabled(self._current_path is not None)
        chosen = menu.exec(
            self._status_menu_btn.mapToGlobal(
                self._status_menu_btn.rect().topRight()
            )
        )
        if self._current_path is None or chosen is None:
            return
        if chosen == act_reveal:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self._current_path.parent))
            )
        elif chosen == act_copy:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(str(self._current_path))

    def _change_admin_password(self) -> None:
        # 'Yönetici' yazısı yalnızca yönetici oturumunda tıklanabilir; başka
        # oturumda sessizce yok sayılır (etiket zaten tıklanabilir görünmez).
        if not isinstance(self._session, AdminSession) or self._session.keys is None:
            return
        effective_users = (
            self._pending_user_passwords
            if self._pending_user_passwords is not None
            else self._session.user_passwords
        )
        dlg = VaultSettingsDialog(
            self._session.admin_password,
            self._session.keys,
            effective_users,
            self,
        )
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        data = dlg.result_data()
        if not data:
            return
        self._pending_admin_password = data["admin_new"]
        self._session.admin_password = data["admin_new"]
        self._mark_dirty()
        show_info(
            self,
            tr("settings_applied_title"),
            tr("settings_applied_text"),
        )

    def _show_audit(self) -> None:
        if not self._require_admin("restricted_audit"):
            return
        dlg = AuditLogDialog(self._vault, self)
        dlg.exec()

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

    def _protect_vault_file(self, path: Path) -> None:
        """Başarılı kayıt sonrası: şifreli yedek al + salt-okunur kilidi bas."""
        create_backup(path)
        set_read_only(path)

    def _check_missing_vaults(self) -> None:
        """Son kullanılan kasa silinmişse ve yedeği varsa geri yüklemeyi öner."""
        for path_str in get_recent_files():
            path = Path(path_str)
            if path.exists():
                continue
            backups = find_backups(path)
            if not backups:
                continue
            latest = backups[0]
            if not ask_yes_no(
                self,
                tr("backup_missing_title"),
                tr("backup_missing_text", path=str(path), backup=latest.name),
                default_yes=True,
            ):
                continue
            try:
                restore_backup(latest, path)
            except OSError as exc:
                show_error(self, tr("backup_restore_failed_title"), str(exc))
                continue
            show_info(
                self,
                tr("backup_restored_title"),
                tr("backup_restored_text", path=str(path)),
            )
            self._landing_page.refresh_recent()

    def _save_vault(self) -> None:
        if self._kilitli_mi:
            self._kilit_ekranini_goster()
            if self._kilitli_mi:
                return
        if isinstance(self._session, UserSession):
            slot_perms = self._row_permissions()
            if slot_perms is not None and not slot_perms.can_save:
                self._show_restriction("restricted_save")
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
            slot_perms = self._vault.permissions_for_slot(self._session.user_slot)
            if not slot_perms.can_save:
                self._show_restriction("restricted_save")
                return
            self._sync_vault_entries()
            new_entries = self._collect_entries()
            logs = diff_entries_for_audit(
                self._snapshot_entries,
                new_entries,
                self._session,
                slot_perms,
                self._vault,
            )
            self._vault.audit_log.extend(logs)
            try:
                clear_read_only(self._current_path)  # type: ignore[arg-type]
                new_keys = write_vault_file_updated(
                    self._current_path,  # type: ignore[arg-type]
                    self._vault,
                    self._session.keys,
                )
                self._session.keys = new_keys
            except VaultCryptoError as exc:
                show_error(self, tr("err_save_title"), crypto_message(str(exc)))
                return
            except OSError as exc:
                show_error(
                    self, tr("err_save_title"), tr("err_save_io", error=str(exc))
                )
                return
            self._protect_vault_file(self._current_path)  # type: ignore[arg-type]
            self._snapshot_entries = copy.deepcopy(new_entries)
            self._last_saved_at = datetime.now()
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

        vault = KobiVault()
        vault.entries = entries
        if data.get("slot_permissions"):
            vault.set_slot_permissions(data["slot_permissions"])
            vault.user_slot_labels = data.get(
                "user_slot_labels", vault.user_slot_labels
            )
        else:
            vault.user_permissions = data["permissions"]
            vault.set_slot_permissions([data["permissions"].copy()])
        path = Path(path_str)
        try:
            clear_read_only(path)
            write_vault_file(
                path,
                vault,
                data["admin_password"],
                data["user_passwords"],
            )
            self._protect_vault_file(path)
            unlock = read_vault_file(path, data["admin_password"])
            self._session = session_from_unlock(
                unlock, data["admin_password"], unlock.vault
            )
            if isinstance(self._session, AdminSession):
                self._session.user_passwords = data["user_passwords"]
        except VaultCryptoError as exc:
            show_error(self, tr("err_save_title"), crypto_message(str(exc)))
            return
        except OSError as exc:
            show_error(self, tr("err_save_title"), tr("err_save_io", error=str(exc)))
            return

        self._current_path = path
        add_recent_file(path)
        self._last_saved_at = datetime.now()
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
            clear_read_only(path)
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
        except OSError as exc:
            show_error(self, tr("err_save_title"), tr("err_save_io", error=str(exc)))
            return

        self._protect_vault_file(path)
        add_recent_file(path)
        self._snapshot_entries = copy.deepcopy(entries)
        self._last_saved_at = datetime.now()
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
        # Yanlış parola girene karşı nazik önlem: boş parola ekranı tekrar gelir;
        # üst üste 3 hatalı denemede program kapanır (yeniden açılabilir). Güçlü
        # KDF (Argon2/PBKDF2) zaten her denemeyi yavaşlatır; bu sayaç caydırıcı.
        max_attempts = 3
        attempts = 0
        password = None
        unlock = None
        while True:
            dlg = OpenPasswordDialog(path.name, self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return  # kullanıcı vazgeçti
            password = dlg.password()
            if not password:
                return
            try:
                unlock = read_vault_file(path, password)
                break  # doğru parola
            except AccessDeniedError:
                attempts += 1
                remaining = max_attempts - attempts
                if remaining <= 0:
                    show_error(self, tr("denied_title"), tr("denied_lockout"))
                    app = QApplication.instance()
                    if app is not None:
                        app.quit()
                    return
                show_error(
                    self, tr("denied_title"), tr("denied_retry", remaining=remaining)
                )
                continue  # boş parola ekranını yeniden göster
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
        self._last_access_at = datetime.now()
        try:
            self._last_saved_at = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            self._last_saved_at = None
        self._load_vault_data(unlock.vault)
        self._show_vault_view()
        self._landing_page.refresh_recent()
        # 'Açıldı' diyaloğunu bir olay-döngüsü tık'ı geciktir: modal, çalışma
        # alanı yerleşmeden açılırsa arkada yarı-yerleşmiş garip bir görüntü
        # kalıyordu. Önce layout otursun, sonra bilgi çıksın.
        count = len(unlock.vault.entries)
        QTimer.singleShot(
            0,
            lambda: show_info(
                self, tr("opened_title"), tr("opened_text", count=count)
            ),
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        # GÜVENLİK: Kilitliyken kaydedilmemiş değişiklik varken kapatmayı
        # ENGELLE. Aksi halde kasa kilitliyken masaya gelen, kimliği
        # doğrulanmamış biri 'Kaydetmeden çık' ile sahibinin çalışmasını
        # silebilir (ya da rızası olmadan kaydedebilir). Kaydet/çık kararı
        # yalnızca kilidi açan sahibe aittir. (Anahtar yoksa kilit açılamaz;
        # o dejenere durumda kullanıcıyı hapsetmemek için normal akışa düşülür.)
        if (
            self._kilitli_mi
            and self._dirty
            and getattr(self._session, "keys", None) is not None
        ):
            event.ignore()
            self._lock_overlay.show_error(tr("lock_unlock_first"))
            self._lock_overlay.raise_()
            self._lock_overlay.focus_password()
            return
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
