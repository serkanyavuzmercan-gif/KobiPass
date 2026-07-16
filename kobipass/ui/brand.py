"""KobiPass marka amblemini (KP + asma kilit) vektörel çizer.

Tek renkli, ölçeklenebilir bir amblem üretir; gündüz/gece temasına uygun renk
ve saydamlık dışarıdan verilir. Filigran olarak da kullanılabilir.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap


def _stroke(path: QPainterPath, painter: QPainter, color: QColor, w: float) -> None:
    pen = QPen(color, w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def paint_brand_mark(
    painter: QPainter, rect: QRectF, color: QColor, *, opacity: float = 1.0
) -> None:
    """``rect`` içine oranı koruyarak KP+kilit amblemini çizer."""
    side = min(rect.width(), rect.height())
    if side <= 0:
        return
    s = side / 100.0
    ox = rect.x() + (rect.width() - side) / 2.0
    oy = rect.y() + (rect.height() - side) / 2.0

    def P(x: float, y: float) -> QPointF:
        return QPointF(ox + x * s, oy + y * s)

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setOpacity(opacity)

    stem_w = 9.0 * s
    bowl_w = 8.0 * s

    # "K" — sol taraf: dikey gövde + iki kol.
    k = QPainterPath()
    k.moveTo(P(24, 28))
    k.lineTo(P(24, 72))
    k.moveTo(P(24, 51))
    k.lineTo(P(43, 28))
    k.moveTo(P(24, 51))
    k.lineTo(P(45, 72))
    _stroke(k, painter, color, stem_w)

    # "P" gövdesi (dikey) — kilit/P bowl'un sol kenarı.
    stem = QPainterPath()
    stem.moveTo(P(53, 28))
    stem.lineTo(P(53, 74))
    _stroke(stem, painter, color, stem_w)

    # Asma kilit halkası (shackle) — gövdenin üstünde belirgin ∩.
    shackle = QPainterPath()
    shackle.moveTo(P(59, 43))
    shackle.lineTo(P(59, 36))
    shackle.arcTo(QRectF(P(59, 27).x(), P(59, 27).y(),
                         13 * s, 13 * s), 180, -180)
    shackle.lineTo(P(72, 43))
    _stroke(shackle, painter, color, bowl_w * 0.82)

    # Kilit gövdesi = P'nin bowl'u: yuvarlatılmış kutu.
    body = QRectF(P(52, 42).x(), P(52, 42).y(), 27 * s, 26 * s)
    pen = QPen(color, bowl_w)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(body, 6 * s, 6 * s)

    # Anahtar deliği (keyhole) — gövdenin içinde dolu, ortalı.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    cx, cy = 65.5, 53.0
    r = 3.4
    painter.drawEllipse(P(cx, cy), r * s, r * s)
    slot = QPainterPath()
    slot.moveTo(P(cx - 1.5, cy + 1.2))
    slot.lineTo(P(cx + 1.5, cy + 1.2))
    slot.lineTo(P(cx + 2.6, cy + 8.5))
    slot.lineTo(P(cx - 2.6, cy + 8.5))
    slot.closeSubpath()
    painter.drawPath(slot)

    painter.restore()


def brand_mark_pixmap(size: int, color: QColor, *, opacity: float = 1.0) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    paint_brand_mark(painter, QRectF(0, 0, size, size), color, opacity=opacity)
    painter.end()
    return pm
