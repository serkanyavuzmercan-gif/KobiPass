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


def hero_art_pixmap(height: int = 360) -> QPixmap:
    """Karşılama ekranı hero görseli (opsiyonel).

    ``assets/hero_vault.png`` varsa oranı korunarak ölçeklenir; yoksa boş
    QPixmap döner (arayüz görseli göstermez). Böylece tasarım PNG'si sonradan
    eklendiğinde otomatik devreye girer.
    """
    path = asset_path("hero_vault.png")
    if not path.is_file():
        return QPixmap()
    pm = QPixmap(str(path))
    if pm.isNull():
        return QPixmap()
    return pm.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)


def hero_left_pixmap(english: bool = False, light: bool = False) -> QPixmap:
    """Karşılama ekranının sol panelini komple kaplayan görsel (opsiyonel).

    Koyu tema ``assets/hero_left.png``, açık tema ``assets/hero_left2.png``
    kullanır (İngilizce için opsiyonel ``*_en.png`` varyantları). İlgili dosya
    yoksa koyu sürüme, o da yoksa boş QPixmap'e düşer. Landing bu görseli
    "cover" biçiminde ölçekleyip sol paneli kaplar.
    """
    if light:
        names = ["hero_left2_en.png", "hero_left2.png"] if english else ["hero_left2.png"]
        names.append("hero_left.png")  # açık sürüm yoksa koyuya düş
    else:
        names = ["hero_left_en.png", "hero_left.png"] if english else ["hero_left.png"]
    for name in names:
        path = asset_path(name)
        if path.is_file():
            pm = QPixmap(str(path))
            if not pm.isNull():
                return pm
    return QPixmap()


def security_shield_pixmap(width: int = 320) -> QPixmap:
    """Özet panelindeki güvenlik kartı görseli (opsiyonel).

    ``assets/security_shield.png`` varsa oranı korunarak genişliğe göre
    ölçeklenir; yoksa boş QPixmap döner (arayüz çizili kalkana düşer).
    """
    path = asset_path("security_shield.png")
    if not path.is_file():
        return QPixmap()
    pm = QPixmap(str(path))
    if pm.isNull():
        return QPixmap()
    return pm.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)


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
