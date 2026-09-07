# Yayın Notu — Microsoft Store'a yüklenecek sürüm

> **Bu dosya devir notudur.** Store / Partner Center yönetimi geliştirmeyi yapan
> kişide değildir. Aşağıdaki adım, yayını yöneten kişi tarafından yapılmalıdır.

## ✅ Durum: 1.3.0 yayınlandı — Store'a yüklenmeyi bekliyor

**1.2.9** Partner Center'a Submission 7 ile yüklenip yayınlandı.
**1.3.0** GitHub'da yayınlandı ve Store'a yüklenmeyi bekliyor.

Sıradaki iş: aşağıdaki **Partner Center adımları** ile 1.3.0.0 paketini
yüklemek. Sertifikasyon genelde birkaç saat, en fazla 3 iş günü sürer; durum
**Application overview** sayfasından izlenir (Pre-processing → Certification →
Publishing → In the Store).

> **Önemli:** Sürümler kümülatiftir. Store'da hangi sürüm yayında olursa olsun
> **doğrudan 1.3.0 yüklenmelidir**; ara sürümleri ayrıca yüklemeye gerek yoktur.

Aşağıdaki bölümler, sonraki sürümlerde aynı işlemi yapacak kişi içindir.

## ➜ Yüklenecek sürüm: **1.3.0.0**

| | |
|---|---|
| **Paket** | `KobiPass-1.3.0.0.msix` |
| **Nereden** | GitHub Releases → **v1.3.0** |
| **Bağlantı** | https://github.com/serkanyavuzmercan-gif/KobiPass/releases/tag/v1.3.0 |
| **Öncelik** | **Yüksek** — veri kaybına yol açan bir hatayı gideriyor |

Paket, GitHub Actions ile üretilmiş ve yayınlanmıştır; elle derlemeye gerek yoktur.

## Neden yükseltilmeli — 1.3.0 ne getiriyor

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

**3. Performans.** 138 kayıtlı bir sekmeye geçiş ve tema değişimi saniyelerce
bekletiyordu; açılışta kurulan satır sayısı düşürüldü (sekme geçişi ~4,5x, tema
değişimi ~4x hızlandı).

**4. Kullanım kolaylıkları.** Araç çubuğuna "Kayıt Ekle" (listenin sonuna inmeye
gerek yok) ve "Gözleri Aç" (tüm şifreleri 10 sn göster) eklendi. Sağ özet paneli
varsayılan kapalı. İlk şifre sütunu artık silinebiliyor.

**5. Görsel düzeltmeler.** Aydınlık temada kilit ekranı da aydınlık; logo ve
uygulama ikonundaki beyaz hale giderildi; satır içindeki gereksiz yatay kaydırma
çubuğu kaldırıldı; aydınlık temada yüzey ayrımı belirginleştirildi.

**6. Değişiklik geçmişi.** Yönetici düzenlemeleri de kaydediliyor; eskiden
yalnızca alt kullanıcı değişiklikleri yazıldığı için tek yöneticili kasalarda
geçmiş boş kalıyordu.

> 1. ve 2. maddeler 1.2.8, 3-6 arası 1.3.0 ile geldi. **1.3.0 önceki tüm
> sürümleri kapsar**; ara sürümleri ayrıca yüklemeye gerek yoktur.

## Partner Center adımları

1. Partner Center → ilgili gönderim → **Packages**
2. `KobiPass-1.3.0.0.msix` dosyasını yükleyin
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

- Store sürüm numarasının **4. hanesi her zaman `0`** olmalıdır: `1.3.1.0` gibi.
- Her yeni gönderimde sürüm artmalıdır; aynı numara ikinci kez kabul edilmez.

**1) Sürüm numarası üç dosyada güncellenir:**

| Dosya | Kaç yerde | Ne işe yarar |
|---|---|---|
| `assets/version_info.txt` | **4 yer** ⚠️ | `.exe`'nin Windows dosya özelliklerine gömülür |
| `kobipass/__init__.py` | 1 yer | Uygulama içinde gösterilen sürüm |
| `build_msix.ps1` | 1 yer (satır 10) | Yalnızca elle derlemede kullanılır |

> ⚠️ **`version_info.txt`'te sürüm iki ayrı biçimde geçer** ve dördü de
> değişmelidir — atlanması kolay bir yerdir:
> `filevers=(1, 3, 0, 0)` · `prodvers=(1, 3, 0, 0)` ·
> `FileVersion '1.3.0'` · `ProductVersion '1.3.0'`

**2) Paket üretimi:** GitHub → **Actions → "Release Windows" → Run workflow** →
`version` alanına `v1.3.1` yazılır → Run. Yaklaşık 4 dakika sürer.
Workflow etiketi **kendisi oluşturur** (elle `git tag` atmaya gerek yoktur),
`.exe` ve `.msix` dosyalarını derleyip Release'e ekler.

> Not: Workflow **yalnızca elle** çalışır. Kod push'lamak veya etiket atmak tek
> başına release üretmez.

## Bilinmesi gereken sınır (hata değil)

Gizli sekmeler kriptografik olarak korunur — alt kullanıcı içeriği hiçbir
şekilde çözemez. Buna karşılık görünür sekmelerdeki **alan bazlı izinler
yalnızca arayüzde uygulanır**. Gerçekten gizlenmesi gereken kayıtlar **gizli
sekmeye** konmalıdır. Ayrıntı: `README.md` → Güvenlik bölümü.
