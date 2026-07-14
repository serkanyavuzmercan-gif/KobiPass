"""
kobiPass arayüz ikonları (QPainter — ek bağımlılık yok).
Koyu temaya uygun çizgi ikonlar.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

ICON_COLOR = QColor("#b8bcc4")
# Her iki temada da okunan orta gri (araç çubuğu) ve marka indigosu (vurgu).
NEUTRAL_COLOR = QColor("#8a90a0")
ACCENT_COLOR = QColor("#4b68f4")
PIXMAP_SIZE = 24

# Tek sefer oluşturulur; toggle sırasında yeniden çizim gerekmez
_ICON_EYE: QIcon | None = None
_ICON_EYE_OFF: QIcon | None = None
_ICON_COPY: QIcon | None = None
_ICON_CACHE: dict[str, QIcon] = {}


def _pixmap_from_painter(draw_fn, size: int = PIXMAP_SIZE) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_fn(painter)
    painter.end()
    return pm


def _line_pen(color: QColor, width: float = 2.0) -> QPen:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


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


def _scaled_icon(key: str, draw_fn, size: int) -> QIcon:
    """İsimle önbelleklenen, ölçekli çizgi ikon."""
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    icon = QIcon(_pixmap_from_painter(draw_fn, size))
    _ICON_CACHE[key] = icon
    return icon


def icon_folder_open(color: QColor = ACCENT_COLOR, size: int = 48) -> QIcon:
    """Açık klasör — 'Dosya Aç'."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(_line_pen(color, 1.8 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # klasör gövdesi + sekme
        p.drawPolygon(
            *[
                _pt(x * s, y * s)
                for x, y in [(3, 8), (3, 5), (9, 5), (11, 8), (21, 8), (21, 10)]
            ]
        )
        # öne açılan kapak
        p.drawPolygon(
            *[
                _pt(x * s, y * s)
                for x, y in [(5, 10), (23, 10), (20, 19), (3, 19), (3, 8)]
            ]
        )

    return _scaled_icon(f"folder_open:{color.name()}:{size}", draw, size)


def icon_file_new(color: QColor = ACCENT_COLOR, size: int = 48) -> QIcon:
    """Artı rozetli belge — 'Yeni Dosya Oluştur'."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        pen = _line_pen(color, 1.8 * s)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # belge gövdesi ve kıvrık köşe
        p.drawPolygon(
            *[
                _pt(x * s, y * s)
                for x, y in [(5, 3), (14, 3), (19, 8), (19, 21), (5, 21)]
            ]
        )
        p.drawPolyline(_pt(14 * s, 3 * s), _pt(14 * s, 8 * s), _pt(19 * s, 8 * s))
        # artı işareti
        plus = _line_pen(color, 2.2 * s)
        p.setPen(plus)
        p.drawLine(_pt(12 * s, 11 * s), _pt(12 * s, 17 * s))
        p.drawLine(_pt(9 * s, 14 * s), _pt(15 * s, 14 * s))

    return _scaled_icon(f"file_new:{color.name()}:{size}", draw, size)


def icon_shield(color: QColor = NEUTRAL_COLOR, size: int = 20) -> QIcon:
    """Onay işaretli kalkan — güvenlik."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(_line_pen(color, 1.8 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(
            *[
                _pt(x * s, y * s)
                for x, y in [(12, 3), (20, 6), (20, 12), (12, 21), (4, 12), (4, 6)]
            ]
        )
        p.drawPolyline(_pt(8.5 * s, 11.5 * s), _pt(11 * s, 14 * s), _pt(15.5 * s, 8.5 * s))

    return _scaled_icon(f"shield:{color.name()}:{size}", draw, size)


def icon_help(color: QColor = NEUTRAL_COLOR, size: int = 20) -> QIcon:
    """Daire içinde soru işareti — yardım."""
    def draw(p: QPainter) -> None:
        from PyQt6.QtCore import QRectF
        from PyQt6.QtGui import QFont

        s = size / 24.0
        p.setPen(_line_pen(color, 1.8 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(_pt(12 * s, 12 * s), 9 * s, 9 * s)  # merkez (12,12)
        font = QFont()
        font.setBold(True)
        font.setPixelSize(int(12 * s))
        p.setFont(font)
        p.setPen(color)
        p.drawText(
            QRectF(3 * s, 3 * s, 18 * s, 18 * s),
            Qt.AlignmentFlag.AlignCenter,
            "?",
        )

    return _scaled_icon(f"help:{color.name()}:{size}", draw, size)


def icon_sun(color: QColor = NEUTRAL_COLOR, size: int = 20) -> QIcon:
    """Güneş — aydınlık moda geç."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(_pt(12 * s, 12 * s), 4.3 * s, 4.3 * s)
        pen = _line_pen(color, 2.0 * s)
        p.setPen(pen)
        import math

        for k in range(8):
            ang = math.pi * k / 4.0
            x, y = 12 * s, 12 * s
            r1, r2 = 8.2 * s, 10.8 * s
            p.drawLine(
                _pt(x + r1 * math.cos(ang), y + r1 * math.sin(ang)),
                _pt(x + r2 * math.cos(ang), y + r2 * math.sin(ang)),
            )

    return _scaled_icon(f"sun:{color.name()}:{size}", draw, size)


def icon_theme(color: QColor = NEUTRAL_COLOR, size: int = 20) -> QIcon:
    """Hilal (ay) — karanlık moda geç."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(_pt(11 * s, 12.5 * s), 8.5 * s, 8.5 * s)  # merkez
        # üstünden kaydırılmış saydam daire çıkarınca hilal kalır
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.drawEllipse(_pt(16 * s, 8.5 * s), 8 * s, 8 * s)

    return _scaled_icon(f"theme:{color.name()}:{size}", draw, size)


def icon_key(color: QColor = ACCENT_COLOR, size: int = 18) -> QIcon:
    """Anahtar — parola üret."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(_line_pen(color, 2.0 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # halka (anahtarın başı)
        p.drawEllipse(_pt(5 * s, 6 * s), 5.5 * s, 5.5 * s)
        # sap ve dişler
        p.drawLine(_pt(11.5 * s, 12 * s), _pt(20 * s, 20.5 * s))
        p.drawLine(_pt(17 * s, 17.5 * s), _pt(19.5 * s, 15 * s))
        p.drawLine(_pt(14.5 * s, 15 * s), _pt(17 * s, 12.5 * s))

    return _scaled_icon(f"key:{color.name()}:{size}", draw, size)


def icon_more(color: QColor = NEUTRAL_COLOR, size: int = 18) -> QIcon:
    """Yatay üç nokta — satır menüsü."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        for cx in (6, 12, 18):
            p.drawEllipse(_pt((cx - 1.6) * s, 10.4 * s), 1.6 * s, 1.6 * s)

    return _scaled_icon(f"more:{color.name()}:{size}", draw, size)


def icon_refresh(color: QColor = ACCENT_COLOR, size: int = 18) -> QIcon:
    """Dairesel ok — parola üret/yenile."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(_line_pen(color, 2.0 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # neredeyse tam çember (üstte açık)
        p.drawArc(int(5 * s), int(5 * s), int(14 * s), int(14 * s), 60 * 16, 280 * 16)
        # ok ucu (sağ üstte)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPolygon(
            _pt(18.5 * s, 4 * s), _pt(18.5 * s, 10 * s), _pt(13.5 * s, 7 * s)
        )

    return _scaled_icon(f"refresh:{color.name()}:{size}", draw, size)


def icon_report(color: QColor = NEUTRAL_COLOR, size: int = 20) -> QIcon:
    """Uyarı üçgeni — zayıf/tekrar parola raporu."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(_line_pen(color, 1.8 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(_pt(12 * s, 4 * s), _pt(21 * s, 20 * s), _pt(3 * s, 20 * s))
        pen = _line_pen(color, 2.0 * s)
        p.setPen(pen)
        p.drawLine(_pt(12 * s, 10 * s), _pt(12 * s, 15 * s))
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(_pt(11.1 * s, 16.8 * s), 1.0 * s, 1.0 * s)

    return _scaled_icon(f"report:{color.name()}:{size}", draw, size)


def icon_home(color: QColor = NEUTRAL_COLOR, size: int = 20) -> QIcon:
    """Ev — karşılama ekranına dön."""
    def draw(p: QPainter) -> None:
        s = size / 24.0
        p.setPen(_line_pen(color, 1.8 * s))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolyline(
            _pt(4 * s, 11 * s), _pt(12 * s, 4 * s), _pt(20 * s, 11 * s)
        )
        p.drawPolyline(
            _pt(6 * s, 10 * s), _pt(6 * s, 20 * s), _pt(18 * s, 20 * s), _pt(18 * s, 10 * s)
        )
        p.drawPolyline(
            _pt(10 * s, 20 * s), _pt(10 * s, 14 * s), _pt(14 * s, 14 * s), _pt(14 * s, 20 * s)
        )

    return _scaled_icon(f"home:{color.name()}:{size}", draw, size)


def _pt(x: float, y: float):
    from PyQt6.QtCore import QPointF

    return QPointF(x, y)


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
