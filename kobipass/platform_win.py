"""Windows frameless pencere: maximize/restore titremesini önler."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QWidget

_GWL_STYLE = -16
_WS_MAXIMIZE = 0x01000000
_SWP_NOANIMATION = 0x0040
_SWP_NOZORDER = 0x0004


def _hwnd(widget: QWidget) -> int:
    wid = widget.winId()
    return int(wid) if wid else 0


def clear_maximized_style(widget: QWidget) -> None:
    """OS maximize bayrağını kaldırır; restore animasyonu tetiklenmez."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = _hwnd(widget)
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, _GWL_STYLE)
        if style & _WS_MAXIMIZE:
            user32.SetWindowLongW(hwnd, _GWL_STYLE, style & ~_WS_MAXIMIZE)
    except Exception:
        pass


def set_window_geometry(widget: QWidget, rect: QRect, *, restoring: bool = False) -> None:
    """Frameless pencerede boyutu tek adımda uygular (Windows animasyonu yok)."""
    if sys.platform != "win32":
        widget.setGeometry(rect)
        return

    try:
        import ctypes

        hwnd = _hwnd(widget)
        if not hwnd:
            widget.setGeometry(rect)
            return

        user32 = ctypes.windll.user32
        if restoring:
            style = user32.GetWindowLongW(hwnd, _GWL_STYLE)
            if style & _WS_MAXIMIZE:
                user32.SetWindowLongW(hwnd, _GWL_STYLE, style & ~_WS_MAXIMIZE)

        flags = _SWP_NOANIMATION | _SWP_NOZORDER
        user32.SetWindowPos(
            hwnd,
            0,
            int(rect.x()),
            int(rect.y()),
            int(rect.width()),
            int(rect.height()),
            flags,
        )
        # Qt'nin geometry() değerini Win32 ile senkron tut (restore sonrası küçülme önlenir).
        widget.setGeometry(rect)
        return
    except Exception:
        pass

    widget.setGeometry(rect)
