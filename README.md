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

## Geliştirme

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python scripts\make_assets.py   # logo_source.png → logo.png + icon.ico
python main.py
pytest
```

## EXE derleme

```powershell
.\build_exe.ps1
```

Çıktı: `dist\kobiPass.exe` ve `C:\kobiPass\kobiPass.exe`

## Lisans

Hidroteknik Yazılım — dahili kullanım.
