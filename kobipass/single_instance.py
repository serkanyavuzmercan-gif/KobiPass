"""Tek örnek: ikinci başlatmada mevcut pencere öne getirilir."""

from __future__ import annotations

from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QMainWindow

_SERVER_NAME = "MercanSoftware.KobiPass.single_instance"
_RAISE_CMD = b"raise"


def activate_existing_instance(timeout_ms: int = 500) -> bool:
    """Başka bir örnek çalışıyorsa onu öne getirir."""
    socket = QLocalSocket()
    socket.connectToServer(_SERVER_NAME)
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(_RAISE_CMD)
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True


class SingleInstanceGuard(QObject):
    """İlk örnek için yerel soket dinleyicisi."""

    def __init__(self, window: QMainWindow, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        QLocalServer.removeServer(_SERVER_NAME)
        if not self._server.listen(_SERVER_NAME):
            raise RuntimeError(self._server.errorString())

    def _on_new_connection(self) -> None:
        connection = self._server.nextPendingConnection()
        if connection is None:
            return
        connection.waitForReadyRead(1000)
        connection.readAll()
        connection.disconnectFromServer()
        self._raise_window()

    def _raise_window(self) -> None:
        window = self._window
        if window.isMinimized():
            window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()
