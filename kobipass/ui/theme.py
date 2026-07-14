"""
Uygulama teması: koyu / aydınlık mod.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from kobipass.ui.styles import DARK_STYLESHEET, LIGHT_STYLESHEET


class ThemeManager(QObject):
    """Koyu ve aydınlık tema geçişi."""

    theme_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        # Varsayılan koyu mod; kullanıcı düğmeyle aydınlığa geçebilir.
        self._dark = True

    def is_dark(self) -> bool:
        return self._dark

    def toggle(self) -> None:
        self._dark = not self._dark
        self.theme_changed.emit()

    def stylesheet(self) -> str:
        return DARK_STYLESHEET if self._dark else LIGHT_STYLESHEET

theme_manager = ThemeManager()
