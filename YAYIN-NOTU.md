# Yayın Notu — Microsoft Store'a yüklenecek sürüm

> **Bu dosya devir notudur.** Store / Partner Center yönetimi geliştirmeyi yapan
> kişide değildir. Aşağıdaki adım, yayını yöneten kişi tarafından yapılmalıdır.

## ✅ Durum: 1.3.2 yayınlandı — Store'a yüklenmeyi bekliyor

**1.2.9** Partner Center'a Submission 7 ile yüklenip yayınlandı.
**1.3.2** GitHub'da yayınlandı ve Store'a yüklenmeyi bekliyor.

Sıradaki iş: aşağıdaki **Partner Center adımları** ile 1.3.2.0 paketini
yüklemek. Sertifikasyon genelde birkaç saat, en fazla 3 iş günü sürer; durum
**Application overview** sayfasından izlenir (Pre-processing → Certification →
Publishing → In the Store).

> **Önemli:** Sürümler kümülatiftir. Store'da hangi sürüm yayında olursa olsun
> **doğrudan 1.3.2 yüklenmelidir**; ara sürümleri (1.3.0, 1.3.1) ayrıca
> yüklemeye gerek yoktur.

Aşağıdaki bölümler, sonraki sürümlerde aynı işlemi yapacak kişi içindir.

## ➜ Yüklenecek sürüm: **1.3.2.0**

| | |
|---|---|
| **Paket** | `KobiPass-1.3.2.0.msix` |
| **Nereden** | GitHub Releases → **v1.3.2** |
| **Bağlantı** | https://github.com/serkanyavuzmercan-gif/KobiPass/releases/tag/v1.3.2 |
| **Öncelik** | **Kritik** — kasanın kalıcı olarak açılamaz hale geldiği bir hatayı gideriyor |

Paket, GitHub Actions ile üretilmiş ve yayınlanmıştır; elle derlemeye gerek yoktur.

## Neden yükseltilmeli — 1.3.2 ne getiriyor

Bu sürüm, programın baştan sona denetlenmesiyle çıkan bulguların giderilmesidir.
Yeni özellik yoktur; tamamı düzeltmedir.

**1. Kasadan kalıcı kilitlenme — asıl sebep bu.**
Yönetici parolası değiştirildikten sonra gizli bir sekme eklenip kaydedilirse,
kasa **hiçbir parolayla bir daha açılamıyordu** — ne eski ne yeni parola
çalışıyordu. Bu yol kapatıldı. Ayrıca kilit ekranı artık henüz kaydedilmemiş
yeni yönetici parolasını da tanıyor; eskiden parolayı değiştirip kaydetmeden
kilit devreye girerse oturuma geri dönmek mümkün olmuyordu.

**2. Kayıtlar birbirine karışmıyor.**
Aynı içeriğe sahip iki kayıt, aramada ve aşağı kaydırmada birbirine bağlanıp
**yanlış kaydın üzerine yazabiliyordu**. Ayrıca silinen kayıt kaydırınca geri
gelmiyor, "değişiklikleri at" dedikten sonra atılan veriler diske yazılmıyor ve
boş bir sekme açıkken kaydetme artık tümden engellenmiyor (eskiden diğer
sekmelerdeki değişiklikler de kaydedilemiyordu).

**3. Beklenmedik kapanmalar.**
Yedek klasörüne erişilemediğinde (ağ payı, dolu disk), bozuk bir CSV
açıldığında, kasa dosyası taşındığında veya kopyaladıktan hemen sonra satır
silindiğinde program kapanıyordu. Bunların hepsi artık anlaşılır bir hata
penceresiyle bildiriliyor; program açık kalıyor ve kaydedilmemiş veri gitmiyor.

**4. Gizli sekmeler gerçekten gizli.**
Gizli sekmelerde yapılan değişikliklerin kaydı — kayıt adlarıyla birlikte —
alt kullanıcıların okuyabildiği bölüme yazılıyordu. Bu içerik artık yalnızca
yöneticinin erişebildiği yerde saklanıyor. Ayrıca bir parola hem yönetici hem
alt kullanıcı girişini açıyorsa (normalde imkânsızdır, dosya dışarıdan
değiştirilmişse olur) kasa açılışında uyarı gösteriliyor.

**5. Yedekler birbirini silmiyor, geri yükleme yarıda kalmıyor.**
Farklı klasörlerdeki aynı adlı kasalar (örn. `iş\kasa.enc` ve `ev\kasa.enc`)
birbirinin yedeklerini siliyordu; artık ayrı tutuluyorlar. Geri yükleme tek
adımda tamamlanıyor — yarıda kesilse bile mevcut kasa zarar görmüyor. Kasa
dosyası artık yalnızca sahibi tarafından okunabiliyor.

**6. Kopyalanan parola panoda kalmıyor.**
Pano; kasa kilitlendiğinde, ana ekrana dönüldüğünde ve program kapandığında
temizleniyor (eskiden yalnızca süre dolarsa temizleniyordu). "Maskeli
görüntüleyebilir" yetkisi olan kullanıcı da artık gizli alanı tek tıkla
kopyalayamıyor.

**7. CSV içe aktarma.**
Excel'in "Unicode Metin" çıktısı bozuk karakterlere dönüşerek sessizce kasaya
yazılıyordu; kapanmayan tırnak içeren dosyalarda satırlar kayboluyor, başında
veya sonunda boşluk olan parolalar sessizce değiştiriliyordu. Hepsi düzeltildi;
şüpheli durumlar önizleme ekranında uyarı olarak gösteriliyor.

**8. Değişiklik geçmişi eksiksiz.**
Yalnızca o an açık olan sekmedeki değişiklikler kaydediliyordu; artık tüm
sekmeler kapsanıyor, kayıt ekleme ve silme de geçmişe düşüyor, tarihler yerel
saate göre gösteriliyor ve arama ekranda görünen metinde çalışıyor.

**9. Kullanıcı yönetimi ve arayüz tutarlılığı.**
Kullanıcı kartları gerçek slot numarasına göre adlandırılıyor; parolası
girilmemiş kart sessizce kaybolmuyor; eksik parola hangi kart olduğunu
söylüyor; kaydetmeden diyaloğu tekrar açmak bekleyen kullanıcıyı ve parola
değişikliğini silmiyor. Ayrıca kasa açmak artık sahte "kaydedilmemiş
değişiklik" uyarısı vermiyor, parola güç göstergesi tüm satırlarda görünüyor,
dil değişimi tüm ekranlara uygulanıyor ve programın iki kez açılması artık
çalışan pencereyi bozmuyor.

> Sürümler kümülatiftir: **1.3.2 önceki tüm sürümleri kapsar**; ara sürümleri
> ayrıca yüklemeye gerek yoktur.

## Partner Center adımları

1. Partner Center → ilgili gönderim → **Packages**
2. `KobiPass-1.3.2.0.msix` dosyasını yükleyin
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

- Store sürüm numarasının **4. hanesi her zaman `0`** olmalıdır: `1.3.3.0` gibi.
- Her yeni gönderimde sürüm artmalıdır; aynı numara ikinci kez kabul edilmez.

**1) Sürüm numarası üç dosyada güncellenir:**

| Dosya | Kaç yerde | Ne işe yarar |
|---|---|---|
| `assets/version_info.txt` | **4 yer** ⚠️ | `.exe`'nin Windows dosya özelliklerine gömülür |
| `kobipass/__init__.py` | 1 yer | Uygulama içinde gösterilen sürüm (Hakkında / Güvenlik) |
| `build_msix.ps1` | 1 yer (satır 10) | Yalnızca elle derlemede kullanılır |

> ⚠️ **`version_info.txt`'te sürüm iki ayrı biçimde geçer** ve dördü de
> değişmelidir — atlanması kolay bir yerdir:
> `filevers=(1, 3, 2, 0)` · `prodvers=(1, 3, 2, 0)` ·
> `FileVersion '1.3.2'` · `ProductVersion '1.3.2'`
>
> İlk ikisi **tuple**'dır (tırnaksız, virgülle ayrılmış), son ikisi **metin**.

**2) Paket üretimi:** GitHub → **Actions → "Release Windows" → Run workflow** →
`version` alanına `v1.3.3` yazılır → Run. Yaklaşık 4 dakika sürer.
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
