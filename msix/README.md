# KobiPass — Microsoft Store (MSIX) paketi

Bu klasör, KobiPass'i Microsoft Store için MSIX olarak paketlemek üzere
gereken manifest ve kimlik dosyalarını içerir. Görsel varlıklar (kutucuklar,
StoreLogo, splash) **tek kaynaktan** — `assets/logo2.png` — otomatik üretilir.

## Dosyalar

| Dosya | Görev |
|---|---|
| `AppxManifest.xml` | Store manifest şablonu (yer tutucular derleme sırasında doldurulur). |
| `identity.json` | Paket kimliği (PackageName, Publisher CN, görünen adlar). |
| `../scripts/generate_msix_assets.py` | `logo2.png` → tüm Store kutucuk boyutları. |
| `../scripts/apply_msix_manifest.py` | `identity.json` + şablon → `AppxManifest.xml`. |
| `../build_msix.ps1` | Uçtan uca: exe derle → görselleri üret → paketle. |

## Üretilen görseller (tüm boyutlar)

- `StoreLogo.png` (50)
- `Square44x44Logo.png` + `scale-100/125/150/200/400` + `targetsize-16/24/32/48/256` (plated & unplated)
- `Square150x150Logo.png` + `scale-100/125/150/200/400`
- `Wide310x150Logo.png` (geniş kutucuk)
- `SplashScreen.png` (620×300)

## Kullanım

```powershell
# 1) Yeni logoyu ekleyin
#    assets/logo2.png  (kare, şeffaf veya düz zeminli PNG)

# 2) Store paketini üretin (revision = 0: 1.2.0.0)
.\build_msix.ps1 -Version 1.2.0.0

# makeappx.exe yoksa yalnızca yerleşimi hazırlar:
.\build_msix.ps1 -LayoutOnly
```

Sadece uygulama ikonu/logosunu yenilemek için (Store olmadan):

```powershell
python scripts\make_assets.py     # assets/logo.png + assets/icon.ico
```

## ÖNEMLİ — Partner Center kimliği

`identity.json` içindeki `PackageName` ve `Publisher` (CN=...) değerleri
**yer tutucudur**. Store'a yüklemeden önce bunları
**Partner Center → Product identity** sayfasındaki gerçek değerlerle
değiştirin; aksi halde paket reddedilir. Sürüm numarasının 4. bölümü (revision)
her zaman `0` olmalıdır.
