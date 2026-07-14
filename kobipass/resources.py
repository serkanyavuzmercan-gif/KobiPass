"""
KobiPass statik kaynak yolları (logo, ikon).
PyInstaller paketinde sys._MEIPASS altından okunur.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QIcon, QImage, QPixmap


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def asset_path(name: str) -> Path:
    return _project_root() / "assets" / name


def app_icon() -> QIcon:
    """Pencere ve görev çubuğu ikonu — icon.ico öncelikli (exe ile aynı)."""
    icon = QIcon()
    ico = asset_path("icon.ico")
    png = asset_path("logo.png")

    if ico.is_file():
        loaded = QIcon(str(ico))
        if not loaded.isNull():
            return loaded

    if png.is_file():
        pm = QPixmap(str(png))
        if not pm.isNull():
            for size in (16, 24, 32, 48, 64, 128, 256):
                scaled = pm.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon.addPixmap(scaled)
            if not icon.isNull():
                return icon

    return icon


def logo_pixmap(height: int = 40) -> QPixmap:
    """Üst başlık logosu; oran korunur."""
    path = asset_path("logo.png")
    if not path.is_file():
        return QPixmap()
    pm = QPixmap(str(path))
    if pm.isNull():
        return QPixmap()
    return pm.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)


def watermark_mask_pixmap(height: int = 512) -> QPixmap:
    """Yüksek çözünürlüklü logo2'den arka plansız, tek renk filigran maskesi."""
    path = asset_path("logo2.png")
    if not path.is_file():
        return logo_pixmap(height)
    source = QImage(str(path)).convertToFormat(QImage.Format.Format_ARGB32)
    if source.isNull():
        return logo_pixmap(height)

    # Köşe beyazlarını dışarıda bırak; yalnızca açık renkli KP/kilit sembolünü al.
    margin_x = max(1, int(source.width() * 0.11))
    margin_top = max(1, int(source.height() * 0.055))
    margin_bottom = max(1, int(source.height() * 0.08))
    crop_rect = QRect(
        margin_x,
        margin_top,
        source.width() - 2 * margin_x,
        source.height() - margin_top - margin_bottom,
    )
    cropped = source.copy(crop_rect)
    mask = QImage(cropped.size(), QImage.Format.Format_ARGB32)
    mask.fill(Qt.GlobalColor.transparent)

    for y in range(cropped.height()):
        for x in range(cropped.width()):
            color = cropped.pixelColor(x, y)
            r, g, b = color.red(), color.green(), color.blue()
            luminance = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
            saturation = max(r, g, b) - min(r, g, b)
            if luminance <= 96 or saturation >= 72:
                continue
            alpha = max(0, min(255, int((luminance - 96) * 1.6)))
            mask.setPixelColor(x, y, QColor(255, 255, 255, alpha))

    pm = QPixmap.fromImage(mask)
    return pm.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)
