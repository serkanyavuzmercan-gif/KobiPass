#!/usr/bin/env python3
"""logo.png dosyasından Windows icon.ico üretir (exe + uygulama ikonu)."""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "logo.png"
DST = ROOT / "assets" / "icon.ico"

# Windows Explorer ve PyInstaller icin gerekli boyutlar
ICO_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Logo bulunamadi: {SRC}")

    base = Image.open(SRC).convert("RGBA")
    master = base.resize((256, 256), Image.Resampling.LANCZOS)

    master.save(DST, format="ICO", sizes=ICO_SIZES)

    size_kb = DST.stat().st_size / 1024
    if size_kb < 10:
        raise SystemExit(f"icon.ico cok kucuk ({size_kb:.1f} KB) — uretim basarisiz.")

    print(f"Olusturuldu: {DST} ({size_kb:.0f} KB, {len(ICO_SIZES)} boyut)")


if __name__ == "__main__":
    main()
