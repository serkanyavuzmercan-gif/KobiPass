"""Karşılama ekranı kasa görselini hazırlar.

`assets/hero_vault_source.png` (açık/beyaz arka planlı bir kasa görseli) alır,
arka planı şeffaflaştırır, kasayı kırpar ve `assets/hero_vault.png` olarak
kaydeder. Landing sayfası bu dosyayı otomatik yükler.

Kullanım:
    python scripts/make_hero_art.py                 # varsayılan kaynak/çıktı
    python scripts/make_hero_art.py girdi.png       # özel kaynak
    python scripts/make_hero_art.py girdi.png cikti.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / "assets" / "hero_vault_source.png"
DEFAULT_OUT = ROOT / "assets" / "hero_vault.png"

# Arka planı ayıklama eşiği: parlak (açık) VE renksiz (gri/beyaz) pikseller
# saydamlaşır. Kasa koyu ve mavi (doygun) olduğu için korunur.
_LUM_FULL = 236     # bu parlaklığın üstü tamamen saydam
_LUM_KEEP = 200     # bunun altı tamamen opak (yumuşak geçiş arası)
_MAX_SAT = 26       # renk doygunluğu bunun altındaysa "arka plan gri"


def _remove_background(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            lum = (r * 299 + g * 587 + b * 114) // 1000
            sat = max(r, g, b) - min(r, g, b)
            if sat <= _MAX_SAT and lum >= _LUM_KEEP:
                if lum >= _LUM_FULL:
                    alpha = 0
                else:
                    # _LUM_KEEP..._LUM_FULL arası yumuşak geçiş
                    alpha = int(
                        255 * (_LUM_FULL - lum) / (_LUM_FULL - _LUM_KEEP)
                    )
                px[x, y] = (r, g, b, min(a, alpha))
    return img


def _autocrop(img: Image.Image, pad: int = 24) -> Image.Image:
    bbox = img.split()[-1].getbbox()  # alfa kanalının sınır kutusu
    if not bbox:
        return img
    left, top, right, bottom = bbox
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img.width, right + pad)
    bottom = min(img.height, bottom + pad)
    return img.crop((left, top, right, bottom))


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    if not src.is_file():
        print(f"Kaynak bulunamadı: {src}")
        print("Kasa görselini bu yola koyup tekrar çalıştırın.")
        return 1
    img = Image.open(src)
    img = _remove_background(img)
    img = _autocrop(img)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"Yazıldı: {out}  ({img.width}x{img.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
