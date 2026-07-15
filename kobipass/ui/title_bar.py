"""
Özel pencere başlığı: sürükleme + simge durumu / ekranı kapla / kapat
(Windows çerçevesi yok). Açılış boyutu ekranın kullanılabilir alanına
oranlıdır; pencere yeniden boyutlandırılabilir.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QWidget,
)

from kobipass.i18n import i18n, tr
from kobipass.platform_win import set_window_geometry
from kobipass.resources import logo_pixmap
from kobipass.ui.icons import (
    icon_globe,
    icon_info,
    icon_shield,
    icon_sun,
    icon_theme,
    icon_win_maximize,
    icon_win_minimize,
    icon_win_restore,
)
from kobipass.ui.theme import theme_manager

# Tasarım referansı: 1280×760 @ 1920×1080 → sabit açılış oranı
WINDOW_WIDTH_RATIO = 1280 / 1920
WINDOW_HEIGHT_RATIO = 760 / 1080

# Yeniden boyutlandırma tabanı (düzen bu boyutun altında bozulmasın) ve
# Qt'nin varsayılan boyut tavanı (sabit-boyut kilidini kaldırmak için).
_MIN_WINDOW_WIDTH = 860
_MIN_WINDOW_HEIGHT = 540
_QWIDGETSIZE_MAX = 16777215


def window_size_for_available(avail: QRect) -> QSize:
    """Kullanılabilir ekran alanına göre sabit oranlı pencere boyutu."""
    width = max(1, int(round(avail.width() * WINDOW_WIDTH_RATIO)))
    height = max(1, int(round(avail.height() * WINDOW_HEIGHT_RATIO)))
    width = min(width, avail.width())
    height = min(height, avail.height())
    return QSize(width, height)


class CustomTitleBar(QWidget):
    """Frameless pencere için üst çubuk ve sağ üst pencere düğmeleri."""

    def __init__(self, window: QMainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._drag_pos: QPoint | None = None
        self._press_global: QPoint | None = None
        self._press_local_y = 0
        self._drag_started = False
        self._manual_drag = False
        self._maximized = False
        self._restore_size: tuple[int, int] | None = None
        self._restore_pos: tuple[int, int] | None = None
        self._toggle_busy = False

        self.setObjectName("customTitleBar")
        # QWidget alt sınıfının QSS arka planını (navy chrome) boyayabilmesi için.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(8)

        brand_wrap = QWidget()
        brand_wrap.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        brand_layout = QHBoxLayout(brand_wrap)
        brand_layout.setContentsMargins(0, 5, 0, 0)
        brand_layout.setSpacing(8)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        _bottom = Qt.AlignmentFlag.AlignBottom

        logo_pm = logo_pixmap(30)
        if not logo_pm.isNull():
            logo_lbl = QLabel()
            logo_lbl.setPixmap(logo_pm)
            logo_lbl.setFixedSize(30, 30)
            logo_lbl.setToolTip(tr("app_name"))
            logo_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            brand_layout.addWidget(logo_lbl, 0, _bottom)

        brand = QLabel(tr("app_name"))
        brand.setObjectName("brandTitle")
        brand.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        brand_layout.addWidget(brand, 0, _bottom)

        self._brand = brand
        self._slogan = QLabel()
        self._slogan.setObjectName("brandSlogan")
        self._slogan.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        brand_layout.addWidget(self._slogan, 0, _bottom)

        layout.addWidget(
            brand_wrap,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )

        drag_area = QWidget()
        drag_area.setObjectName("titleDragArea")
        layout.addWidget(drag_area, stretch=1)

        # Sağ üst yardımcı düğmeler: tema · dil · güvenlik · hakkında.
        _vc = Qt.AlignmentFlag.AlignVCenter
        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("themeBtn")
        self.btn_theme.setFixedWidth(44)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(theme_manager.toggle)
        layout.addWidget(self.btn_theme, 0, _vc)

        self.btn_lang = QPushButton("TR/EN")
        self.btn_lang.setObjectName("langBtn")
        self.btn_lang.setIcon(icon_globe(size=16))
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.clicked.connect(i18n.toggle)
        layout.addWidget(self.btn_lang, 0, _vc)

        self.btn_security = QPushButton()
        self.btn_security.setObjectName("headerSecurityBtn")
        self.btn_security.setIcon(icon_shield())
        self.btn_security.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.btn_security, 0, _vc)

        self.btn_about = QPushButton()
        self.btn_about.setObjectName("helpBtn")
        self.btn_about.setIcon(icon_info())
        self.btn_about.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.btn_about, 0, _vc)

        self._update_theme_icon()
        theme_manager.theme_changed.connect(self._update_theme_icon)

        # Standart pencere düğmeleri: simge durumu · ekranı kapla/geri al · kapat.
        self._btn_min = QPushButton()
        self._btn_min.setObjectName("titleBtnMin")
        self._btn_min.setFixedSize(46, 38)
        self._btn_min.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_min.setIcon(icon_win_minimize(size=14))
        self._btn_min.clicked.connect(self._window.showMinimized)
        layout.addWidget(self._btn_min)

        self._btn_max = QPushButton()
        self._btn_max.setObjectName("titleBtnMax")
        self._btn_max.setFixedSize(46, 38)
        self._btn_max.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_max.clicked.connect(self._on_maximize_clicked)
        layout.addWidget(self._btn_max)

        self._btn_close = QPushButton("\u00d7")
        self._btn_close.setObjectName("titleBtnClose")
        self._btn_close.setFixedSize(46, 38)
        self._btn_close.clicked.connect(self._window.close)
        layout.addWidget(self._btn_close)

        self._refresh_maximize_button()
        self.retranslate()

    @staticmethod
    def _is_near_fullscreen(geom: QRect, avail: QRect, margin: int = 4) -> bool:
        return (
            abs(geom.width() - avail.width()) <= margin
            and abs(geom.height() - avail.height()) <= margin
        )

    def capture_normal_geometry(self) -> None:
        if self._maximized:
            return
        geom = self._window.geometry()
        avail = self._available_screen_geometry()
        if self._is_near_fullscreen(geom, avail):
            return
        self._restore_size = (geom.width(), geom.height())
        self._restore_pos = (geom.x(), geom.y())

    def apply_screen_ratio_geometry(self, *, recenter: bool = True) -> QSize:
        """Açılış boyutunu ekran oranına göre uygular; pencere yeniden
        boyutlandırılabilir kalır (sabit boyut kilidi kaldırıldı).

        ``recenter=True`` (ilk açılış / ekran değişimi) boyutu ve konumu
        uygular; ``recenter=False`` yalnızca boyut sınırlarını tazeler ve
        kullanıcının seçtiği boyutu korur.
        """
        avail = self._available_screen_geometry()
        size = window_size_for_available(avail)
        # Yeniden boyutlandırmayı serbest bırak: alt sınır makul bir taban,
        # üst sınır Qt'nin varsayılan tavanı. Alt sınır açılış boyutunu asla
        # aşmasın (küçük ekranlarda pencere büyümeye zorlanmasın).
        min_w = min(_MIN_WINDOW_WIDTH, size.width())
        min_h = min(_MIN_WINDOW_HEIGHT, size.height())
        self._window.setMaximumSize(_QWIDGETSIZE_MAX, _QWIDGETSIZE_MAX)
        self._window.setMinimumSize(min_w, min_h)
        if recenter:
            target = self._centered_geometry(size.width(), size.height())
            self._window.winId()
            set_window_geometry(self._window, target, restoring=False)
            self._restore_size = (size.width(), size.height())
            self._restore_pos = (target.x(), target.y())
        self._maximized = False
        self._refresh_maximize_button()
        return size

    def center_on_screen(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Pencereyi ekranın ortasına yerleştirir (tam ekran değil)."""
        if width is None or height is None:
            size = window_size_for_available(self._available_screen_geometry())
            width = size.width() if width is None else width
            height = size.height() if height is None else height
        self._window.setMaximumSize(_QWIDGETSIZE_MAX, _QWIDGETSIZE_MAX)
        self._window.setMinimumSize(
            min(_MIN_WINDOW_WIDTH, width), min(_MIN_WINDOW_HEIGHT, height)
        )
        target = self._centered_geometry(width, height)
        self._window.winId()
        set_window_geometry(self._window, target, restoring=False)
        self._restore_size = (width, height)
        self._restore_pos = (target.x(), target.y())
        self._maximized = False
        self._refresh_maximize_button()

    def _update_theme_icon(self) -> None:
        self.btn_theme.setIcon(
            icon_sun() if theme_manager.is_dark() else icon_theme()
        )

    def retranslate(self) -> None:
        self._brand.setText(tr("app_name"))
        self._slogan.setText(tr("slogan"))
        self._btn_min.setToolTip(tr("title_minimize"))
        self._refresh_maximize_button()
        self._btn_close.setToolTip(tr("title_close"))
        self.btn_theme.setToolTip(tr("btn_theme_tip"))
        self.btn_lang.setToolTip(tr("btn_lang_tip"))
        self.btn_security.setText(tr("landing_security"))
        self.btn_security.setToolTip(tr("security_badge_tip"))
        self.btn_about.setText(tr("about_us_title"))
        self.btn_about.setToolTip(tr("btn_about_tip"))

    def _available_screen_geometry(self) -> QRect:
        screen = self._window.screen()
        if screen is not None:
            return screen.availableGeometry()
        app = QApplication.instance()
        if isinstance(app, QApplication) and app.primaryScreen():
            return app.primaryScreen().availableGeometry()
        return self._window.geometry()

    def _centered_geometry(self, width: int, height: int) -> QRect:
        avail = self._available_screen_geometry()
        x = avail.x() + max(0, (avail.width() - width) // 2)
        y = avail.y() + max(0, (avail.height() - height) // 2)
        return QRect(x, y, width, height)

    def _refresh_maximize_button(self) -> None:
        btn = getattr(self, "_btn_max", None)
        if btn is None:
            return
        if self._maximized:
            btn.setIcon(icon_win_restore(size=14))
            btn.setToolTip(tr("title_restore"))
        else:
            btn.setIcon(icon_win_maximize(size=14))
            btn.setToolTip(tr("title_maximize"))

    def _on_maximize_clicked(self) -> None:
        if self._toggle_busy:
            return
        self._toggle_busy = True
        try:
            self._toggle_maximize()
        finally:
            self._toggle_busy = False

    def _toggle_maximize(self) -> None:
        if self._maximized:
            self._restore_normal()
        else:
            self._maximize_to_available()

    def _maximize_to_available(self) -> None:
        """Pencereyi kullanılabilir ekran alanına kaplar (görev çubuğu hariç)."""
        geom = self._window.geometry()
        avail = self._available_screen_geometry()
        if not self._is_near_fullscreen(geom, avail):
            self._restore_size = (geom.width(), geom.height())
            self._restore_pos = (geom.x(), geom.y())
        # Boyut kilidi kalmış olabilir; kaplamadan önce tavanı serbest bırak.
        self._window.setMaximumSize(_QWIDGETSIZE_MAX, _QWIDGETSIZE_MAX)
        self._window.winId()
        set_window_geometry(self._window, avail, restoring=False)
        self._maximized = True
        self._refresh_maximize_button()

    def _restore_normal(self) -> None:
        """Ekranı kaplı pencereyi önceki boyut/konuma geri alır."""
        avail = self._available_screen_geometry()
        if self._restore_size is not None:
            width, height = self._restore_size
        else:
            size = window_size_for_available(avail)
            width, height = size.width(), size.height()
        if self._restore_pos is not None:
            x, y = self._restore_pos
            target = QRect(x, y, width, height)
        else:
            target = self._centered_geometry(width, height)
        self._window.winId()
        set_window_geometry(self._window, target, restoring=True)
        self._maximized = False
        self._refresh_maximize_button()

    def _is_draggable_target(self, pos) -> bool:
        child = self.childAt(pos)
        if child is None:
            return True
        return not isinstance(child, QPushButton)

    def _restore_under_cursor(self, global_pos: QPoint, local_y: int) -> None:
        """Ekranı kaplı pencereyi, imleç başlık çubuğunda kalacak biçimde geri
        al (sürükleyerek geri alma davranışı)."""
        if self._restore_size is not None:
            width, height = self._restore_size
        else:
            size = window_size_for_available(self._available_screen_geometry())
            width, height = size.width(), size.height()
        cur = self._window.geometry()
        ratio_x = (global_pos.x() - cur.x()) / max(1, cur.width())
        new_x = int(global_pos.x() - ratio_x * width)
        new_y = int(global_pos.y() - local_y)
        self._window.setGeometry(QRect(new_x, new_y, width, height))
        self._maximized = False
        self._refresh_maximize_button()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._is_draggable_target(event.pos())
        ):
            # Taşımayı hemen başlatma; gerçek sürükleme olunca başlat ki tık ve
            # çift tık (kapla/geri al) bozulmasın.
            self._press_global = event.globalPosition().toPoint()
            self._press_local_y = int(event.position().y())
            self._drag_started = False
            self._drag_pos = self._press_global - self._window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_global is None or not (
            event.buttons() & Qt.MouseButton.LeftButton
        ):
            super().mouseMoveEvent(event)
            return
        global_pos = event.globalPosition().toPoint()
        if self._drag_started:
            # Native taşımada OS ilgilenir; yalnızca yedek elle taşımayı sürdür.
            if self._manual_drag and self._drag_pos is not None:
                self._window.move(global_pos - self._drag_pos)
                event.accept()
            return
        moved = (global_pos - self._press_global).manhattanLength()
        if moved < QApplication.startDragDistance():
            return
        # Eşik aşıldı → sürükleme başlat.
        self._drag_started = True
        if self._maximized:
            self._restore_under_cursor(global_pos, self._press_local_y)
        handle = self._window.windowHandle()
        if handle is not None:
            # Taşımayı OS'e devret: Windows Aero Snap (kenara/köşeye snap, üstte
            # kapla, snap layout) yalnızca native taşımada çalışır.
            handle.startSystemMove()
            event.accept()
            return
        # Yedek: pencere tanıtıcısı yoksa elle taşı.
        self._manual_drag = True
        self._drag_pos = global_pos - self._window.frameGeometry().topLeft()
        self._window.move(global_pos - self._drag_pos)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._press_global = None
        self._drag_pos = None
        self._drag_started = False
        self._manual_drag = False
        if not self._maximized:
            self.capture_normal_geometry()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # Başlığa çift tıklama ekranı kapla / geri al (düğmelerin üstünde değil).
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._is_draggable_target(event.pos())
        ):
            self._drag_pos = None
            self._on_maximize_clicked()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
