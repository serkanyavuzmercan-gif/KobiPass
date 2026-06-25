"""
kobiPass arayüz ikonları (QPainter — ek bağımlılık yok).
Koyu temaya uygun çizgi ikonlar.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

ICON_COLOR = QColor("#b8bcc4")
PIXMAP_SIZE = 24

# Tek sefer oluşturulur; toggle sırasında yeniden çizim gerekmez
_ICON_EYE: QIcon | None = None
_ICON_EYE_OFF: QIcon | None = None
_ICON_COPY: QIcon | None = None


def _pixmap_from_painter(draw_fn) -> QPixmap:
    pm = QPixmap(PIXMAP_SIZE, PIXMAP_SIZE)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_fn(painter)
    painter.end()
    return pm


def _build_icon_eye() -> QIcon:
    def draw(p: QPainter) -> None:
        pen = QPen(ICON_COLOR, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(4, 9, 16, 8)
        p.setBrush(ICON_COLOR)
        p.drawEllipse(10, 11, 4, 4)

    return QIcon(_pixmap_from_painter(draw))


def _build_icon_eye_off() -> QIcon:
    def draw(p: QPainter) -> None:
        pen = QPen(ICON_COLOR, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(4, 9, 16, 8)
        p.setBrush(ICON_COLOR)
        p.drawEllipse(10, 11, 4, 4)
        p.drawLine(5, 18, 19, 6)

    return QIcon(_pixmap_from_painter(draw))


def _build_icon_copy() -> QIcon:
    def draw(p: QPainter) -> None:
        pen = QPen(ICON_COLOR, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(8, 5, 12, 14, 2, 2)
        p.drawRoundedRect(4, 8, 12, 14, 2, 2)

    return QIcon(_pixmap_from_painter(draw))


def icon_eye() -> QIcon:
    global _ICON_EYE
    if _ICON_EYE is None:
        _ICON_EYE = _build_icon_eye()
    return _ICON_EYE


def icon_eye_off() -> QIcon:
    global _ICON_EYE_OFF
    if _ICON_EYE_OFF is None:
        _ICON_EYE_OFF = _build_icon_eye_off()
    return _ICON_EYE_OFF


def icon_copy() -> QIcon:
    global _ICON_COPY
    if _ICON_COPY is None:
        _ICON_COPY = _build_icon_copy()
    return _ICON_COPY
