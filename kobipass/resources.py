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
