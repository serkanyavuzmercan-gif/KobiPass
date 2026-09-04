# Yayın Notu — Microsoft Store'a yüklenecek sürüm

> **Bu dosya devir notudur.** Store / Partner Center yönetimi geliştirmeyi yapan
> kişide değildir. Aşağıdaki adım, yayını yöneten kişi tarafından yapılmalıdır.

## ➜ Yüklenecek sürüm: **1.2.9.0**

| | |
|---|---|
| **Paket** | `KobiPass-1.2.9.0.msix` |
| **Nereden** | GitHub Releases → **v1.2.9** |
| **Bağlantı** | https://github.com/serkanyavuzmercan-gif/KobiPass/releases/tag/v1.2.9 |
| **Öncelik** | **Yüksek** — veri kaybına yol açan bir hatayı gideriyor |

Paket, GitHub Actions ile üretilmiş ve yayınlanmıştır; elle derlemeye gerek yoktur.

## Neden yükseltilmeli — 1.2.9 ne getiriyor

**1. Yedeklerin silinmesi (veri kaybı) — asıl sebep bu.**
Adı bir diğerinin öneki olan iki kasa (örn. `kasa.enc` ve `kasa-yedek.enc`)
aynı yedek klasörünü paylaşınca birbirine karışıyordu. `kasa.enc` yeterince
kaydedildiğinde, diğer kasanın yedekleri **sessizce siliniyordu**. Geri yükleme
ekranı da yanlış kasanın yedeklerini listeliyordu. Düzeltildi; mevcut yedekler
geçerliliğini koruyor.

**2. Kilitliyken program kapanmıyordu.**
Boşta kilit devreye girip parola ekranı geldiğinde, kaydedilmemiş değişiklik
varsa uygulama kapanmayı reddediyordu (X, Alt+F4, görev çubuğu — hiçbiri
çalışmıyordu). Artık açık onayla çıkılabiliyor. Güvenlik korunuyor: kilitliyken
"Kaydet" seçeneği sunulmaz, yetkisiz kişi değişiklikleri diske yazamaz.

**3. Kod temizliği (davranış değişikliği yok).**
Ölü kod, tekrar eden tanımlar ve kullanılmayan import'lar kaldırıldı. Kullanıcıya
yansıyan bir değişiklik yoktur; bakım kolaylığı içindir.

> Yukarıdaki 1. ve 2. maddeler 1.2.8 ile düzeltilmişti. **1.2.8 Store'a
> yüklenmediyse doğrudan 1.2.9 yüklenmelidir** — 1.2.9 hepsini kapsar.

## Partner Center adımları

1. Partner Center → ilgili gönderim → **Packages**
2. `KobiPass-1.2.9.0.msix` dosyasını yükleyin
3. Paket **imzasız** üretilmiştir (`-SkipSign`); imzayı Store yükleme sırasında
   kendisi atar — ek işlem gerekmez
4. Gönderimi yayınlayın

**Ürün kimliği** (pakette sabittir, değiştirilmemelidir):

```
PackageName          : Hidroteknik.KobiPass
Publisher            : CN=119D3611-306D-4F5E-B28C-3904B4C07374
PublisherDisplayName : Hidroteknik
```

**Sistem gereksinimi:** Windows 10 (1809 / build 10.0.17763) veya üzeri, 64-bit.
Windows 7/8 desteklenmez.

## Sonraki sürümler için not

- Store sürüm numarasının **4. hanesi her zaman `0`** olmalıdır: `1.2.10.0` gibi.
- Her yeni gönderimde sürüm artmalıdır; aynı numara ikinci kez kabul edilmez.

**1) Sürüm numarası üç dosyada güncellenir:**

| Dosya | Kaç yerde | Ne işe yarar |
|---|---|---|
| `assets/version_info.txt` | **4 yer** ⚠️ | `.exe`'nin Windows dosya özelliklerine gömülür |
| `kobipass/__init__.py` | 1 yer | Uygulama içinde gösterilen sürüm |
| `build_msix.ps1` | 1 yer (satır 10) | Yalnızca elle derlemede kullanılır |

> ⚠️ **`version_info.txt`'te sürüm iki ayrı biçimde geçer** ve dördü de
> değişmelidir — atlanması kolay bir yerdir:
> `filevers=(1, 2, 9, 0)` · `prodvers=(1, 2, 9, 0)` ·
> `FileVersion '1.2.9'` · `ProductVersion '1.2.9'`

**2) Paket üretimi:** GitHub → **Actions → "Release Windows" → Run workflow** →
`version` alanına `v1.2.10` yazılır → Run. Yaklaşık 4 dakika sürer.
Workflow etiketi **kendisi oluşturur** (elle `git tag` atmaya gerek yoktur),
`.exe` ve `.msix` dosyalarını derleyip Release'e ekler.

> Not: Workflow **yalnızca elle** çalışır. Kod push'lamak veya etiket atmak tek
> başına release üretmez.

## Bilinmesi gereken sınır (hata değil)

Gizli sekmeler kriptografik olarak korunur — alt kullanıcı içeriği hiçbir
şekilde çözemez. Buna karşılık görünür sekmelerdeki **alan bazlı izinler
yalnızca arayüzde uygulanır**. Gerçekten gizlenmesi gereken kayıtlar **gizli
sekmeye** konmalıdır. Ayrıntı: `README.md` → Güvenlik bölümü.
