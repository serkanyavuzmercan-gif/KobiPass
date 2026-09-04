"""
KobiPass statik kaynak yolları (logo, ikon).
PyInstaller paketinde sys._MEIPASS altından okunur.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap


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
