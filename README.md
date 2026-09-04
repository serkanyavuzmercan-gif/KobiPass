# KobiPass — Parola Kasası

Hidroteknik Yazılım ekibi tarafından geliştirilen, PyQt6 tabanlı parola yönetim uygulaması. **1 yönetici + en fazla 64 alt kullanıcı** rol modeli, kullanıcı başına izinler, **yönetici-özel gizli sekmeler** ve değişiklik geçmişi sunar.

> **Sistem gereksinimi:** Windows 10 (1809 / build 10.0.17763) veya üzeri, 64-bit.
> Qt 6 ve Python 3.9+ Windows 7/8'i desteklemez (`api-ms-win-core-path-l1-1-0.dll`
> eksik hatası bundandır). Windows 7 makineleri Windows 10/11'e yükseltilmelidir.

## Özellikler

- Kayıt formatı: **İsim — 1. Bilgi — ek bilgi alanları (dinamik)**
- **Sekmeler:** her kasa Excel benzeri birden çok sekme tutar
- **Gizli sekme:** yönetici-özel sekmeler ayrı bir anahtarla (AEK) şifrelenir — alt kullanıcılar bunları ne görür **ne de çözebilir**
- Her `.enc` dosyasında **1 yönetici** + **en fazla 64 alt kullanıcı** parolası (boş slot destekli)
- Yönetici: sınırsız yetki, kullanıcı/izin yönetimi, alan etiketleri, değişiklik geçmişi
- Güvenlik gereği **dışa aktarma yoktur** — veriler yalnızca şifreli `.enc` dosyasında yaşar
- **CSV içe aktarma** (tek yön): Excel/CSV parolalarını aktif sekmeye taşır; `;`/`,` ayracı ve `utf-8`/`cp1254` otomatik saptanır, önizleme + onay
- Kullanıcılar: **her slot için ayrı izin**; yalnızca izinli alanları görür/düzenler
- Arama, sonsuz kaydırma, sürükle-bırak sıralama
- Koyu / aydınlık tema, TR/EN dil desteği, karşılama ekranı ve son dosyalar
- Güvenlik: pano otomatik temizleme, boşta / küçültünce kilit, Argon2id (yeni dosyalar)
- Taşınabilir Windows `.exe`

## Güvenlik

| Bileşen | Detay |
|---------|--------|
| Format | `KBPS` v1–v6 (geriye uyumlu); yeni kasalar **v5** = Argon2id + değişken slot + gizli sekme bölmesi |
| Zarf şifreleme | Rastgele DEK + yönetici/kullanıcı sarmalayıcıları |
| Gizli sekme | Ayrı **AEK** (yönetici-özel anahtar) ile şifreli bölme; yalnızca yönetici parolasıyla açılır |
| Anahtar türetme | **Argon2id** (t=3, m=64 MB, p=4) · PBKDF2-HMAC-SHA256 100.000 (eski dosyalar) |
| Şifreleme | **AES-256-GCM** |
| Bütünlük | Dosya sonu SHA-256 özeti + atomik yazma |
| Silinme koruması | Her kayıtta AppData'ya şifreli yedek (son 10) + salt-okunur kilidi + açılışta silinme tespiti ve yedekten geri yükleme |

> **İzinlerin kapsamı — bilinmesi gereken sınır.** *Gizli sekmeler* kriptografik
> olarak korunur: alt kullanıcı anahtara sahip olmadığı için içeriği hiçbir
> şekilde çözemez. Buna karşılık *görünür* sekmelerdeki **alan bazlı izinler**
> (`Görmez` / `Maskeli` / `Düzenler`) yalnızca arayüzde uygulanır — o sekmelerin
> içeriği, geçerli bir kullanıcı parolasıyla çözülen ortak blokta durur.
> Bu nedenle **gerçekten gizlenmesi gereken kayıtları gizli sekmeye koyun**;
> alan izinlerini yetkisiz gözlere karşı tek başına bir güvenlik sınırı olarak
> değerlendirmeyin.

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

# Partner Center Product Identity (msix\identity.json icinde sabittir):
#   Name: Hidroteknik.KobiPass
#   Publisher: CN=119D3611-306D-4F5E-B28C-3904B4C07374
#   PublisherDisplayName: Hidroteknik

# Store paketi uret (4. hane / revision her zaman 0)
.\build_msix.ps1 -Version 1.2.8.0 -SkipSign
```

Çıktı: `dist\KobiPass-1.2.8.0.msix`

**Partner Center’a yükleme**

1. **Packages** altında bu `.msix` dosyasını yükleyin.
2. Yerelde imza yoksa (`-SkipSign`) Store yükleme sırasında imzalar.
3. Her yeni yüklemede sürümü artırın: `1.2.8.0`, `1.2.9.0` … (4. hane her zaman `0`).

Detaylar: [`msix/README.md`](msix/README.md)

## Lisans

Hidroteknik Yazılım — dahili kullanım.
