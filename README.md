# KobiPass — Parola Kasası

Hidroteknik Yazılım ekibi tarafından geliştirilen, PyQt6 tabanlı parola yönetim uygulaması. **Yönetici + 3 kullanıcı** rol modeli, alan bazlı izinler ve değişiklik geçmişi sunar.

## Özellikler

- Kayıt formatı: **İsim — 1. Bilgi — ek bilgi alanları (dinamik)**
- Her `.enc` dosyasında **1 yönetici** + **3 kullanıcı** parolası (boş slot destekli)
- Yönetici: sınırsız yetki, kullanıcı/izin yönetimi, alan etiketleri, değişiklik geçmişi
- Güvenlik gereği **dışa aktarma yoktur** — veriler yalnızca şifreli `.enc` dosyasında yaşar
- Kullanıcılar: ortak izin şablonu; yalnızca izinli alanları görür
- Arama, sonsuz kaydırma, sürükle-bırak sıralama
- Koyu / aydınlık tema, TR/EN dil desteği, karşılama ekranı ve son dosyalar
- Güvenlik: pano otomatik temizleme, boşta / küçültünce kilit, Argon2id (yeni dosyalar)
- Taşınabilir Windows `.exe`

## Güvenlik

| Bileşen | Detay |
|---------|--------|
| Format | `KBPS` v1 (PBKDF2) / v2 (Argon2id) |
| Zarf şifreleme | Rastgele DEK + yönetici/kullanıcı sarmalayıcıları |
| Anahtar türetme | **Argon2id** (yeni) · PBKDF2-HMAC-SHA256 100.000 (eski) |
| Şifreleme | **AES-256-GCM** |
| Bütünlük | Dosya sonu SHA-256 özeti |
| Silinme koruması | Her kayıtta AppData'ya şifreli yedek (son 10) + salt-okunur kilidi + açılışta silinme tespiti ve yedekten geri yükleme |

## Geliştirme

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python scripts\make_assets.py   # logo2.png → logo.png + icon.ico
python main.py
pytest
```

## EXE derleme

```powershell
.\build_exe.ps1
```

Çıktı: `dist\kobiPass.exe` ve `C:\kobiPass\kobiPass.exe`

## Microsoft Store (MSIX) paketi

Store’a yüklemek için Windows’ta PowerShell ile:

```powershell
cd C:\path\to\KobiPass   # repo kökü

# Windows SDK yoksa (makeappx için):
# winget install --id Microsoft.WindowsSDK.10.0.18362 --accept-package-agreements --accept-source-agreements

# Partner Center kimliğini kontrol et (msix\identity.json)
# PackageName + Publisher (CN=...) gerçek Product Identity ile aynı olmalı

# Store paketi üret (4. hane / revision her zaman 0)
.\build_msix.ps1 -Version 1.1.0.0 -SkipSign
```

Çıktı: `dist\KobiPass-1.1.0.0.msix`

**Partner Center’a yükleme**

1. **Packages** altında bu `.msix` dosyasını yükleyin.
2. Yerelde imza yoksa (`-SkipSign`) Store yükleme sırasında imzalar.
3. Her yeni yüklemede sürümü artırın: `1.1.1.0`, `1.2.0.0` … (4. hane her zaman `0`).

Detaylar: [`msix/README.md`](msix/README.md)

## Lisans

Hidroteknik Yazılım — dahili kullanım.
