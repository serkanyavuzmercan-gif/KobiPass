"""
Pano kopyalama — otomatik temizleme ile.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QGuiApplication

from kobipass.settings import get_clipboard_clear_ms


class ClipboardGuard(QObject):
    """Kopyalanan metni belirli süre sonra panodan siler."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._token = 0
        self._pending_text = ""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._clear_if_unchanged)

    def copy(self, text: str) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        self._token += 1
        self._pending_text = text
        self._timer.stop()
        if text:
            self._timer.start(get_clipboard_clear_ms())

    def _clear_if_unchanged(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard.text() == self._pending_text:
            clipboard.clear()
        self._pending_text = ""


_guard: ClipboardGuard | None = None


def clipboard_guard() -> ClipboardGuard:
    global _guard
    if _guard is None:
        _guard = ClipboardGuard()
    return _guard


def copy_text(text: str) -> None:
    clipboard_guard().copy(text)
