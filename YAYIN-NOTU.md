# Yayın Notu — Microsoft Store'a yüklenecek sürüm

> **Bu dosya devir notudur.** Store / Partner Center yönetimi geliştirmeyi yapan
> kişide değildir. Aşağıdaki adım, yayını yöneten kişi tarafından yapılmalıdır.

## ✅ Durum: 1.3.5 yayınlandı — Store'a yüklenmeyi bekliyor

**1.2.9** Partner Center'a Submission 7 ile yüklenip yayınlandı.
**1.3.5** GitHub'da yayınlandı ve Store'a yüklenmeyi bekliyor.

Sıradaki iş: aşağıdaki **Partner Center adımları** ile 1.3.5.0 paketini
yüklemek. Sertifikasyon genelde birkaç saat, en fazla 3 iş günü sürer; durum
**Application overview** sayfasından izlenir (Pre-processing → Certification →
Publishing → In the Store).

> **Önemli:** Sürümler kümülatiftir. Store'da hangi sürüm yayında olursa olsun
> **doğrudan 1.3.5 yüklenmelidir**; ara sürümleri (1.3.0 – 1.3.4) ayrıca
> yüklemeye gerek yoktur.

Aşağıdaki bölümler, sonraki sürümlerde aynı işlemi yapacak kişi içindir.

## ➜ Yüklenecek sürüm: **1.3.5.0**

| | |
|---|---|
| **Paket** | `KobiPass-1.3.5.0.msix` |
| **Nereden** | GitHub Releases → **v1.3.5** |
| **Bağlantı** | https://github.com/serkanyavuzmercan-gif/KobiPass/releases/tag/v1.3.5 |
| **Öncelik** | **Kritik** — 1.3.3'teki parola/anahtar sızıntısı düzeltmesini de kapsar |

Paket, GitHub Actions ile üretilmiş ve yayınlanmıştır; elle derlemeye gerek yoktur.

## 1.3.5 ne getiriyor

**1. Parola yaşı skalası.**
Her kaydın sağında, parolanın son değiştirilme tarihinin altında dört bölmeli
renkli bir ölçek ve kademenin adı görünür:
**Taze** (0-3 ay, yeşil) · **İyi** (3-6 ay) · **Eskiyor** (6-12 ay, amber) ·
**Eski** (1 yıl+, kırmızı). Bayat parolalar bir bakışta ayırt edilir; üzerine
gelince skalanın açıklaması çıkar.

**2. CSV'ye dışa aktarma.**
Kayıtlar CSV dosyası olarak dışa aktarılabilir — başka bir parola yöneticisine
taşınmak ya da Excel'de açmak için. Özellik bilinçli olarak korumalıdır:
- Yalnızca **yönetici** kullanabilir ve **parolası yeniden sorulur**.
- Onay ekranı kaç kaydın gideceğini ve dosyanın **şifresiz** olduğunu söyler.
- Her dışa aktarma, tarih ve kullanıcıyla **değişiklik geçmişine kaydedilir**
  ve bu kayıt anında kasaya yazılır. Kayıt yazılamazsa dışa aktarma iptal
  edilir; kaydı olmayan bir dışa aktarma dosyası oluşmaz.
- **Gizli sekmeler varsayılan olarak dahil edilmez**; dahil edilirse bu
  kayıtta açıkça belirtilir.
- İki biçim: Excel uyumlu (noktalı virgül) ve standart CSV (virgül; diğer
  parola yöneticileri için).

Önceki sürümlerde dışa aktarma "güvenlik gereği" kapalıydı. Bu karar geri
alındı: yönetici parolaları zaten ekranda görüp kopyalayabiliyordu, yani yasak
bir şeyi korumuyordu. Üstelik ekran görüntüsü kayda geçmez ama dışa aktarma
geçer — izlenebilir bir yol sunmak daha iyi bir savunmadır.

**3. Kapanışta çökme düzeltmesi.**
Birden fazla silinmiş kasa kaydı varken, açılıştaki "yedekten geri yükleyeyim
mi?" sorusu ekrandayken program kapatılırsa program çöküyordu. Giderildi.

## Önceki sürümlerden devreden (bu pakete dahildir)

**1.3.4 — Satır yanlışlıkla taşınmıyor.** Sıralama yalnızca satırın en
solundaki tutamaktan (⠇⠇) başlar; alanlar arasında sağa sola kaydırırken satır
artık yukarı aşağı taşınmaz.

**1.3.3 — aşağıdakilerin tamamı:**

**1. Değişiklik geçmişindeki değerler artık gizli.**
Kasa ekranında isim dışındaki her hücre maskelidir, ama değişiklik geçmişi bu
kuralı uygulamıyordu: 2. Bilgi ve sonrası (API anahtarları, tokenlar, hesap
numaraları) düz metin olarak hem ekranda gösteriliyor hem de kasa dosyasına
yazılıyordu. O bölüm **her alt kullanıcının parolasıyla açılabilen** bölümdür;
yani bir alanı "Görmez"/"Maskeli" yaptığınız alt kullanıcı, göremediği değerleri
geçmişten okuyabiliyordu. Artık hiçbir değer saklanmıyor ve koşulsuz
maskeleniyor. **Eski kayıtlardaki düz metin değerler de temizleniyor:** kasa
açılırken düşürülüyor, ilk kayıtta dosyadan kalıcı olarak siliniyor.

**2. Değişiklik geçmişi doğru anlatıyor.** Hücre silmek artık tek satır
("VERİ2 hücresi silindi — sonrakiler sola kaydı"), kayıt adı değişimi de kendi
özetiyle ("Kayıt adı değiştirildi") görünüyor.

**3. "Boş Hücreleri Sil" düğmesi.** Onay sorar, kaç hücrenin kaç kayıtta
etkileneceğini söyler, kayıt silmez.

**4. Satır içi sağa sola gezinme.** Hücreler artık satıra sığmaya çalışıyor;
gerçekten taşan satırlarda kenar okları, konum çubuğu ve Tab ile odak takibi var.

**5. Çökme düzeltmesi.** Satırların bellekten temizlenmesinde çöp toplayıcı
kaynaklı bir çökme giderildi.

> Sürümler kümülatiftir: **1.3.5 önceki tüm sürümleri kapsar**; ara sürümleri
> ayrıca yüklemeye gerek yoktur.

## Partner Center adımları

1. Partner Center → ilgili gönderim → **Packages**
2. `KobiPass-1.3.5.0.msix` dosyasını yükleyin
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

- Store sürüm numarasının **4. hanesi her zaman `0`** olmalıdır: `1.3.6.0` gibi.
- Her yeni gönderimde sürüm artmalıdır; aynı numara ikinci kez kabul edilmez.

**1) Sürüm numarası üç dosyada güncellenir:**

| Dosya | Kaç yerde | Ne işe yarar |
|---|---|---|
| `assets/version_info.txt` | **4 yer** ⚠️ | `.exe`'nin Windows dosya özelliklerine gömülür |
| `kobipass/__init__.py` | 1 yer | Uygulama içinde gösterilen sürüm (Hakkında / Güvenlik) |
| `build_msix.ps1` | 1 yer (satır 10) | Yalnızca elle derlemede kullanılır |

> ⚠️ **`version_info.txt`'te sürüm iki ayrı biçimde geçer** ve dördü de
> değişmelidir — atlanması kolay bir yerdir:
> `filevers=(1, 3, 5, 0)` · `prodvers=(1, 3, 5, 0)` ·
> `FileVersion '1.3.5'` · `ProductVersion '1.3.5'`
>
> İlk ikisi **tuple**'dır (tırnaksız, virgülle ayrılmış), son ikisi **metin**.

**2) Paket üretimi:** GitHub → **Actions → "Release Windows" → Run workflow** →
`version` alanına `v1.3.6` yazılır → Run. Yaklaşık 4 dakika sürer.
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
