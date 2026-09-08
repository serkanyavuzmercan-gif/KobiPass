"""Tek örnek: ikinci başlatmada mevcut pencere öne getirilir.

Tasarım ilkesi: tek örnek koruması bir KOLAYLIKTIR, çalışma şartı değildir.
Soket adı alınamazsa, karşı taraf yanıt vermezse veya dinleme başarısız olursa
uygulama yine de AÇILIR. Aksi hâlde adı kapan herhangi bir yerel süreç
KobiPass'in hiç başlamamasına yol açabilirdi.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QMainWindow

_SERVER_NAME = "MercanSoftware.KobiPass.single_instance"
_RAISE_CMD = b"raise"
# Karşı tarafın gerçekten KobiPass olduğunu doğrulayan yanıt. Bu el sıkışma
# olmadan, sabit ve kimliksiz uç noktaya bağlanabilen HERHANGİ bir süreç
# "zaten çalışıyor" sanılıyor ve uygulama sessizce kapanıyordu; adı önceden
# oluşturan yetkisiz bir süreç KobiPass'i oturum boyunca engelleyebilirdi.
_HELLO_ACK = b"kobipass"


def activate_existing_instance(timeout_ms: int = 500) -> bool:
    """Başka bir KobiPass örneği çalışıyorsa onu öne getirir.

    Yalnızca doğru yanıtı veren bir karşı taraf için True döner; bağlantı
    kurulup yanıt gelmezse (yabancı süreç) False döner ve çağıran normal
    başlatmaya devam eder.
    """
    socket = QLocalSocket()
    try:
        socket.connectToServer(_SERVER_NAME)
        if not socket.waitForConnected(timeout_ms):
            return False
        socket.write(_RAISE_CMD)
        socket.flush()
        socket.waitForBytesWritten(timeout_ms)
        if not socket.waitForReadyRead(timeout_ms):
            return False
        return bytes(socket.readAll()).startswith(_HELLO_ACK)
    finally:
        socket.abort()
        socket.deleteLater()


class SingleInstanceGuard(QObject):
    """İlk örnek için yerel soket dinleyicisi.

    ``active`` False ise koruma kurulamamıştır (ad başka bir süreçte veya
    dinleme başarısız). Bu bir hata değildir; uygulama korumasız çalışır.
    """

    def __init__(self, window: QMainWindow, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        self.active = self._listen()

    def _listen(self) -> bool:
        if self._server.listen(_SERVER_NAME):
            return True
        # Ad meşgul. removeServer'ı KOŞULSUZ çağırmak, Unix'te ÇALIŞAN ilk
        # örneğin soket dosyasını siliyor ve iki örnek birden açılıyordu
        # (ilk örnek listen'a gelene kadar geçen süre gerçek bir yarış
        # penceresidir; --onefile derlemede saniyeler sürer). Önce canlı bir
        # KobiPass var mı diye sor: varsa adı ASLA kaldırma.
        if activate_existing_instance():
            return False
        QLocalServer.removeServer(_SERVER_NAME)
        # İkinci deneme de başarısız olabilir (adı yabancı bir süreç tutuyor).
        # Eskiden burada RuntimeError fırlatılıyordu; --windowed derlemede
        # konsol olmadığı için uygulama hiçbir şey göstermeden ölüyordu.
        return self._server.listen(_SERVER_NAME)

    def _on_new_connection(self) -> None:
        connection = self._server.nextPendingConnection()
        if connection is None:
            return
        connection.waitForReadyRead(1000)
        data = bytes(connection.readAll())
        connection.write(_HELLO_ACK)
        connection.flush()
        connection.waitForBytesWritten(1000)
        connection.disconnectFromServer()
        # Kabul edilen soketler sunucunun çocuğudur; silinmezse süreç boyunca
        # birikirler.
        connection.deleteLater()
        if data.startswith(_RAISE_CMD):
            self._raise_window()

    def _raise_window(self) -> None:
        window = self._window
        if window.isMinimized():
            window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()
