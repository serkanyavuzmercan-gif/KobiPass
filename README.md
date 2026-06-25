# KobiPass — Parola Kasası

Hidroteknik Yazılım ekibi tarafından geliştirilen, PyQt6 tabanlı parola yönetim uygulaması. **Yönetici + 3 kullanıcı** rol modeli, alan bazlı izinler ve değişiklik geçmişi sunar.

## Özellikler

- Kayıt formatı: **İsim — 1. Bilgi — 2. Bilgi — 3. Bilgi (opsiyonel) — 4. Bilgi (opsiyonel)**
- Her `.enc` dosyasında **1 yönetici** + **3 kullanıcı** parolası (boş slot destekli)
- Yönetici: sınırsız yetki, kullanıcı/izin yönetimi, değişiklik geçmişi
- Kullanıcılar: ortak izin şablonu; yalnızca izinli alanları görür/düzenler
- Kullanıcı değişiklikleri audit log'a yazılır (önceki / sonraki değerler)
- Koyu tema, TR/EN dil desteği, taşınabilir Windows `.exe`

## Güvenlik

| Bileşen | Detay |
|---------|--------|
| Format | `KBPS` (`PFRT` formatıyla uyumsuz) |
| Zarf şifreleme | Rastgele DEK + yönetici/kullanıcı sarmalayıcıları |
| Anahtar türetme | PBKDF2-HMAC-SHA256, **100.000** iterasyon |
| Şifreleme | **AES-256-GCM** |

## Geliştirme

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python scripts\make_assets.py   # logo_source.png → logo.png + icon.ico
python main.py
```

## EXE derleme

```powershell
.\build_exe.ps1
```

Çıktı: `dist\kobiPass.exe` ve `C:\kobiPass\kobiPass.exe`

## Lisans

Hidroteknik Yazılım — dahili kullanım.
