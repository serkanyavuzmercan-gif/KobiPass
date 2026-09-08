# Yayın Notu — Microsoft Store'a yüklenecek sürüm

> **Bu dosya devir notudur.** Store / Partner Center yönetimi geliştirmeyi yapan
> kişide değildir. Aşağıdaki adım, yayını yöneten kişi tarafından yapılmalıdır.

## ✅ Durum: 1.3.3 yayınlandı — Store'a yüklenmeyi bekliyor

**1.2.9** Partner Center'a Submission 7 ile yüklenip yayınlandı.
**1.3.3** GitHub'da yayınlandı ve Store'a yüklenmeyi bekliyor.

Sıradaki iş: aşağıdaki **Partner Center adımları** ile 1.3.3.0 paketini
yüklemek. Sertifikasyon genelde birkaç saat, en fazla 3 iş günü sürer; durum
**Application overview** sayfasından izlenir (Pre-processing → Certification →
Publishing → In the Store).

> **Önemli:** Sürümler kümülatiftir. Store'da hangi sürüm yayında olursa olsun
> **doğrudan 1.3.3 yüklenmelidir**; ara sürümleri (1.3.0 – 1.3.2) ayrıca
> yüklemeye gerek yoktur.

Aşağıdaki bölümler, sonraki sürümlerde aynı işlemi yapacak kişi içindir.

## ➜ Yüklenecek sürüm: **1.3.3.0**

| | |
|---|---|
| **Paket** | `KobiPass-1.3.3.0.msix` |
| **Nereden** | GitHub Releases → **v1.3.3** |
| **Bağlantı** | https://github.com/serkanyavuzmercan-gif/KobiPass/releases/tag/v1.3.3 |
| **Öncelik** | **Kritik** — parola/anahtar değerlerinin sızdığı bir hatayı gideriyor |

Paket, GitHub Actions ile üretilmiş ve yayınlanmıştır; elle derlemeye gerek yoktur.

## Neden yükseltilmeli — 1.3.3 ne getiriyor

**1. Değişiklik geçmişindeki değerler artık gizli — asıl sebep bu.**
Kasa ekranında isim dışındaki her hücre maskelidir; göz düğmesine basmadan
değeri göremezsiniz. Ama **değişiklik geçmişi bu kuralı uygulamıyordu**:
1. Bilgi maskeleniyor, 2. Bilgi ve sonrası (API anahtarları, tokenlar, hesap
numaraları) düz metin olarak hem ekranda gösteriliyor hem de kasa dosyasına
yazılıyordu.

Bu yalnızca görüntü sorunu değildi. O bölüm, **her alt kullanıcının parolasıyla
açılabilen** bölümdür. Yani bir alanı "Görmez" veya "Maskeli" olarak
ayarladığınız alt kullanıcı, göremediği değerleri değişiklik geçmişinden
okuyabiliyordu.

Artık hiçbir değer hücresi saklanmıyor ve geçmişte koşulsuz maskeleniyor.
**Eski kayıtlardaki düz metin değerler de temizleniyor:** kasanız açılırken
düşürülüyor, ilk kaydınızda dosyadan kalıcı olarak siliniyor. Geçmişte kimin,
ne zaman, hangi kaydın hangi alanını değiştirdiği görünmeye devam ediyor —
yalnızca değerin kendisi gitti.

**2. Değişiklik geçmişi artık doğru anlatıyor.**
İki ayrı sorun geçmişi güvenilmez gösteriyordu:
- Bir **hücre sildiğinizde** sonraki hücreler sola kayıyor, geçmiş bunu konum
  konum "VERİ2 şu oldu, VERİ3 boşaldı" zinciri olarak yazıyordu. Siz öyle bir
  düzenleme yapmadığınız için uydurma görünüyordu. Artık tek satır:
  "VERİ2 hücresi silindi (sonrakiler sola kaydı)".
- **Kayıt adını değiştirdiğinizde**, isim sütununa özel bir etiket verdiyseniz
  (ör. "AÇIKLAMA") özet "AÇIKLAMA güncellendi" oluyordu — "Kayıt" sütunu zaten
  yeni adı gösterdiği için satır dairesel ve tanınmaz haldeydi. Artık açıkça
  "Kayıt adı değiştirildi" diyor.

**3. Yeni: "Boş Hücreleri Sil" düğmesi.**
Araç çubuğuna eklendi. Aktif sekmedeki kayıtlarda boş kalan bilgi hücrelerini
toplu temizler. Silmeden önce **kaç hücrenin kaç kayıtta** etkileneceğini
söyleyip onay ister; sonrakilerin sola kayacağını ve kasanın hemen
kaydedilmediğini belirtir — sonucu beğenmezseniz kaydetmeden çıkabilirsiniz.
Bir kayıt en az bir hücre tutar, yani kayıt silinmez.

**4. Satırda sağa sola gidememe sorunu.**
Bir kayda 4'ten fazla bilgi alanı eklendiğinde son alanlara ulaşılamıyordu.
Kök nedeni giderildi: hücreler artık **satıra sığmaya çalışıyor** — 1920px'lik
bir pencerede 6 alanlı satır hiç taşmıyor. Gerçekten taşan satırlarda (çok fazla
alan veya dar pencere) satırın kenarlarında **ok düğmeleri** çıkıyor, ince bir
konum çubuğu imleç o satırdayken belirginleşiyor ve **Tab** ile gittiğiniz hücre
görüş alanına getiriliyor. Sığan satırlarda hiçbir gezinme süsü çıkmıyor.

**5. Çökme düzeltmesi.**
Kayıt satırlarının bellekten temizlenmesinde, çöp toplayıcının silinmiş bir
nesneye dokunmasına yol açan bir hata bulundu ve giderildi. Test paketi
düzeltmeden önce 8 denemenin 8'inde çöküyordu; sonrasında 8/8 temiz.

> Sürümler kümülatiftir: **1.3.3 önceki tüm sürümleri kapsar**; ara sürümleri
> ayrıca yüklemeye gerek yoktur.

## Partner Center adımları

1. Partner Center → ilgili gönderim → **Packages**
2. `KobiPass-1.3.3.0.msix` dosyasını yükleyin
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

- Store sürüm numarasının **4. hanesi her zaman `0`** olmalıdır: `1.3.4.0` gibi.
- Her yeni gönderimde sürüm artmalıdır; aynı numara ikinci kez kabul edilmez.

**1) Sürüm numarası üç dosyada güncellenir:**

| Dosya | Kaç yerde | Ne işe yarar |
|---|---|---|
| `assets/version_info.txt` | **4 yer** ⚠️ | `.exe`'nin Windows dosya özelliklerine gömülür |
| `kobipass/__init__.py` | 1 yer | Uygulama içinde gösterilen sürüm (Hakkında / Güvenlik) |
| `build_msix.ps1` | 1 yer (satır 10) | Yalnızca elle derlemede kullanılır |

> ⚠️ **`version_info.txt`'te sürüm iki ayrı biçimde geçer** ve dördü de
> değişmelidir — atlanması kolay bir yerdir:
> `filevers=(1, 3, 3, 0)` · `prodvers=(1, 3, 3, 0)` ·
> `FileVersion '1.3.3'` · `ProductVersion '1.3.3'`
>
> İlk ikisi **tuple**'dır (tırnaksız, virgülle ayrılmış), son ikisi **metin**.

**2) Paket üretimi:** GitHub → **Actions → "Release Windows" → Run workflow** →
`version` alanına `v1.3.4` yazılır → Run. Yaklaşık 4 dakika sürer.
Workflow etiketi **kendisi oluşturur** (elle `git tag` atmaya gerek yoktur),
`.exe` ve `.msix` dosyalarını derleyip Release'e ekler.

> Not: Workflow **yalnızca elle** çalışır. Kod push'lamak veya etiket atmak tek
> başına release üretmez.

## Bilinmesi gereken sınır (hata değil)

Gizli sekmeler kriptografik olarak korunur — alt kullanıcı içeriği hiçbir
şekilde çözemez. Buna karşılık görünür sekmelerdeki **alan bazlı izinler
yalnızca arayüzde uygulanır**; aynı şekilde **rol ayrımı da kriptografik
değildir** (yönetici ve alt kullanıcılar aynı veri anahtarını paylaşır).
Gerçekten gizlenmesi gereken kayıtlar **gizli sekmeye** konmalıdır.
Ayrıntı: `README.md` → Güvenlik bölümü.
