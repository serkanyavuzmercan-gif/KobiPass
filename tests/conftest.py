"""Test oturumu yalıtımı.

Testler GERÇEK kullanıcı ortamına dokunmamalı. Bu dosya olmadan:
- kasa kaydeden testler, kullanıcının "son dosyalar" listesine geçici yollar
  yazıyordu (QSettings); geçici klasör silinince uygulamanın açılıştaki
  "silinmiş kasa" kontrolü bu sahte kayıtlara takılıyordu,
- yedekler kullanıcının gerçek yedek klasörüne düşüyordu.
Bunlar hem kullanıcının makinesini kirletiyor hem de testleri, önceki
çalıştırmaların bıraktığı duruma bağımlı (ve kararsız) yapıyordu.

Ortam değişkenleri pytest bu dosyayı içe aktardığında, yani hiçbir test ve
hiçbir kobipass modülü çalışmadan ÖNCE ayarlanır.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile

_SANDBOX = tempfile.mkdtemp(prefix="kobipass-tests-")
os.environ["KOBIPASS_SETTINGS_FILE"] = os.path.join(_SANDBOX, "settings.ini")
os.environ["KOBIPASS_BACKUP_DIR"] = os.path.join(_SANDBOX, "backups")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

atexit.register(shutil.rmtree, _SANDBOX, ignore_errors=True)
