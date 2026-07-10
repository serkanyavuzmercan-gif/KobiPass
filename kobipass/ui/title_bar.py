"""
Özel pencere başlığı: sürükleme + küçült / büyüt / kapat (Windows çerçevesi yok).
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt
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
from kobipass.platform_win import clear_maximized_style, set_window_geometry
from kobipass.resources import logo_pixmap

DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 760


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

        self._btn_min = QPushButton("\u2212")
        self._btn_min.setObjectName("titleBtnMin")
        self._btn_min.setFixedSize(46, 38)
        self._btn_min.clicked.connect(self._window.showMinimized)
        layout.addWidget(self._btn_min)

        self._btn_max = QPushButton("\u25a1")
        self._btn_max.setObjectName("titleBtnMax")
        self._btn_max.setFixedSize(46, 38)
        self._btn_max.clicked.connect(self._on_maximize_clicked)
        layout.addWidget(self._btn_max)

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

    def center_on_screen(
        self,
        width: int = DEFAULT_WINDOW_WIDTH,
        height: int = DEFAULT_WINDOW_HEIGHT,
    ) -> None:
        """Pencereyi ekranın ortasına yerleştirir (tam ekran değil)."""
        target = self._centered_geometry(width, height)
        self._window.winId()
        set_window_geometry(self._window, target, restoring=False)
        self._restore_size = (width, height)
        self._maximized = False
        self._refresh_maximize_button()

    def retranslate(self) -> None:
        self._brand.setText(tr("app_name"))
        self._slogan.setText(tr("slogan"))
        self._btn_min.setToolTip(tr("title_minimize"))
        self._btn_close.setToolTip(tr("title_close"))
        self._refresh_maximize_button()

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
        if self._maximized:
            self._btn_max.setText("\u29c9")
            self._btn_max.setToolTip(tr("title_restore"))
        else:
            self._btn_max.setText("\u25a1")
            self._btn_max.setToolTip(tr("title_maximize"))

    def _on_maximize_clicked(self) -> None:
        if self._toggle_busy:
            return
        self._toggle_busy = True
        try:
            self._toggle_maximize()
        finally:
            self._toggle_busy = False

    def _toggle_maximize(self) -> None:
        w = self._window
        w.winId()

        if self._maximized:
            if self._restore_size:
                w_norm, h_norm = self._restore_size
            else:
                w_norm, h_norm = DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
            target = self._centered_geometry(w_norm, h_norm)
            set_window_geometry(w, target, restoring=True)
            self._restore_size = (target.width(), target.height())
            self._maximized = False
        else:
            target = self._available_screen_geometry()
            set_window_geometry(w, target, restoring=False)
            clear_maximized_style(w)
            self._maximized = True

        self._refresh_maximize_button()

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
        if self._is_draggable_target(event.pos()):
            self._on_maximize_clicked()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
