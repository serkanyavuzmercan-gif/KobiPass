"""Windows frameless pencere: maximize/restore titremesini önler."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QWidget

_GWL_STYLE = -16
_WS_MAXIMIZE = 0x01000000


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
    """Frameless pencerede geometriyi tek adımda, DPI-güvenli uygular.

    Qt'nin ``setGeometry``'si mantıksal (ölçekten bağımsız) piksel kullanır ve
    DPI dönüşümünü kendi yapar. Ham ``SetWindowPos`` ise fiziksel piksel bekler;
    Qt'nin mantıksal değerlerini oraya geçirmek %125/%150 ölçeklemede pencereyi
    olması gerekenden küçük bırakıyordu (ekranı kapla tam kaplamıyor, geri al
    daha da küçültüyordu). Bu yüzden doğrudan ``setGeometry`` kullanılır;
    yalnızca gerçek bir OS-maximize durumundan dönerken ``WS_MAXIMIZE`` stili
    temizlenir (restore animasyonu tetiklenmesin)."""
    widget.winId()
    if sys.platform == "win32" and restoring:
        clear_maximized_style(widget)
    widget.setGeometry(rect)
