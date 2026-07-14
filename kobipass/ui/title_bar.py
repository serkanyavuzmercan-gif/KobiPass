"""
Özel pencere başlığı: sürükleme + kapat (Windows çerçevesi yok).
Pencere boyutu ekranın kullanılabilir alanına oranlıdır; köşeden büyütme yok.
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

from kobipass.i18n import tr
from kobipass.platform_win import set_window_geometry
from kobipass.resources import logo_pixmap

# Tasarım referansı: 1280×760 @ 1920×1080 → sabit açılış oranı
WINDOW_WIDTH_RATIO = 1280 / 1920
WINDOW_HEIGHT_RATIO = 760 / 1080


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
        self._maximized = False
        self._restore_size: tuple[int, int] | None = None
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

        # Yalnızca kapat düğmesi — simge durumuna küçült / ekranı kapla yok.
        self._btn_close = QPushButton("\u00d7")
        self._btn_close.setObjectName("titleBtnClose")
        self._btn_close.setFixedSize(46, 38)
        self._btn_close.clicked.connect(self._window.close)
        layout.addWidget(self._btn_close)

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

    def apply_screen_ratio_geometry(self, *, recenter: bool = True) -> QSize:
        """Ekran oranına göre sabit boyut uygular; köşeden büyütmeyi kilitler."""
        avail = self._available_screen_geometry()
        size = window_size_for_available(avail)
        self._window.setFixedSize(size)
        if recenter:
            target = self._centered_geometry(size.width(), size.height())
            self._window.winId()
            set_window_geometry(self._window, target, restoring=False)
        self._restore_size = (size.width(), size.height())
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
        self._window.setFixedSize(width, height)
        target = self._centered_geometry(width, height)
        self._window.winId()
        set_window_geometry(self._window, target, restoring=False)
        self._restore_size = (width, height)
        self._maximized = False
        self._refresh_maximize_button()

    def retranslate(self) -> None:
        self._brand.setText(tr("app_name"))
        self._slogan.setText(tr("slogan"))
        self._btn_close.setToolTip(tr("title_close"))

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
        # Büyüt/geri al düğmesi kaldırıldı — yalnızca kapat düğmesi var.
        return

    def _on_maximize_clicked(self) -> None:
        if self._toggle_busy:
            return
        self._toggle_busy = True
        try:
            self._toggle_maximize()
        finally:
            self._toggle_busy = False

    def _toggle_maximize(self) -> None:
        # Ekranı kapla / geri al kaldırıldı — oranlı sabit boyut korunur.
        self.apply_screen_ratio_geometry(recenter=True)

    def _is_draggable_target(self, pos) -> bool:
        child = self.childAt(pos)
        if child is None:
            return True
        return not isinstance(child, QPushButton)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._is_draggable_target(event.pos())
            and not self._maximized
        ):
            global_pos = event.globalPosition().toPoint()
            self._drag_pos = global_pos - self._window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self._maximized
        ):
            global_pos = event.globalPosition().toPoint()
            self._window.move(global_pos - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        if not self._maximized:
            self.capture_normal_geometry()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # Ekranı kapla kaldırıldı — çift tıklama bir şey yapmaz.
        super().mouseDoubleClickEvent(event)
