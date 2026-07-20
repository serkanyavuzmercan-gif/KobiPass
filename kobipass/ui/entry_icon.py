"""
Satır logosu kodlama/çözme — küçük kare PNG (base64).

Kullanıcı bir görsel seçtiğinde AGRESİF küçültülür: en-boy korunarak
``ICON_STORE_PX`` karesine sığdırılır (asla büyütülmez) ve PNG olarak base64'e
çevrilir. Böylece dev bir görsel bile ``.enc``'e küçük (~birkaç KB) girer.
"""

from __future__ import annotations

import base64

from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QImage, QPixmap

# Saklanan kare boy: ~22px gösterim için HiDPI'da keskin kalsın diye 2x.
ICON_STORE_PX = 44
# Güvenlik sınırı: kodlanmış logo bundan büyükse reddet (beklenmez; 44px PNG
# ~birkaç KB'dir). Bozuk/aşırı büyük veriye karşı sağlamlık.
MAX_ICON_B64 = 64 * 1024


def encode_icon_file(path: str) -> str:
    """Dosya yolundaki görseli küçük kare base64 PNG'ye çevirir; hata→''."""
    image = QImage(path)
    if image.isNull():
        return ""
    return encode_icon_image(image)


def encode_icon_image(image: QImage) -> str:
    if image.isNull():
        return ""
    longest = max(image.width(), image.height())
    if longest > ICON_STORE_PX:
        image = image.scaled(
            ICON_STORE_PX,
            ICON_STORE_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    # QBuffer'ı kendi iç tamponuyla kullan; harici QByteArray geçirmek (geçici
    # nesne GC'lenip sarkan işaretçi → çökme) riskini önler.
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        buffer.close()
        return ""
    data = buffer.data()
    buffer.close()
    encoded = bytes(data.toBase64()).decode("ascii")
    if len(encoded) > MAX_ICON_B64:
        return ""
    return encoded


def pixmap_from_icon(b64: str, size: int) -> QPixmap:
    """base64 PNG'yi verilen kare boyuta ölçekli QPixmap'e çevirir; hata→boş."""
    if not b64 or len(b64) > MAX_ICON_B64:
        return QPixmap()
    try:
        raw = base64.b64decode(b64.encode("ascii"), validate=True)
    except (ValueError, base64.binascii.Error):
        return QPixmap()
    image = QImage.fromData(raw, "PNG")
    if image.isNull():
        return QPixmap()
    pixmap = QPixmap.fromImage(image)
    if size > 0:
        pixmap = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return pixmap
