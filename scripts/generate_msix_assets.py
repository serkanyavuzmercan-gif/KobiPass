#!/usr/bin/env python3
"""
KobiPass MSIX / Microsoft Store görsellerini tek kaynaktan üretir.

Kaynak öncelik sırası: assets/logo.png → assets/logo2.png → assets/logo_source.png
(veya --icon ile verilen dosya). Kare kutucuklar şeffaflığı korur; geniş kutucuk ve
splash açık zemin (#F4F6FB) üzerine ortalanır.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

# Geniş kutucuk / splash için açık zemin (uygulama gövdesiyle aynı: #F4F6FB).
_LIGHT_BG = (244, 246, 251, 255)

# Uyarlanabilir kutucuklar ve görev çubuğu için DPI ölçek çeşitleri.
_SCALE_VARIANTS = (100, 125, 150, 200, 400)

# Görev çubuğunun DPI'dan bağımsız kullandığı tam piksel boyutları.
_TARGET_SIZES = (16, 24, 32, 48, 256)

ASSET_SPECS: list[tuple[str, int | tuple[int, int]]] = [
    ("StoreLogo.png", 50),
    ("Square44x44Logo.png", 44),
    ("Square150x150Logo.png", 150),
    ("Wide310x150Logo.png", (310, 150)),
    ("SplashScreen.png", (620, 300)),
]

for _scale in _SCALE_VARIANTS:
    ASSET_SPECS.append((f"Square44x44Logo.scale-{_scale}.png", round(44 * _scale / 100)))

for _ts in _TARGET_SIZES:
    for _suffix in ("", "_altform-unplated"):
        ASSET_SPECS.append((f"Square44x44Logo.targetsize-{_ts}{_suffix}.png", _ts))

for _scale in _SCALE_VARIANTS:
    ASSET_SPECS.append((f"Square150x150Logo.scale-{_scale}.png", round(150 * _scale / 100)))


def _square(source: Image.Image, size: int) -> Image.Image:
    """İkonu kare boyuta getirir; şeffaflığı (yuvarlak köşeler) korur."""
    return source.resize((size, size), Image.Resampling.LANCZOS)


def save_asset(
    source: Image.Image,
    destination: Path,
    size: int | tuple[int, int],
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(size, tuple):
        # Geniş kutucuk / splash: açık plaka üzerine ortalanmış ikon.
        width, height = size
        canvas = Image.new("RGBA", (width, height), _LIGHT_BG)
        fitted = source.copy()
        fitted.thumbnail((width, height), Image.Resampling.LANCZOS)
        offset = ((width - fitted.width) // 2, (height - fitted.height) // 2)
        canvas.paste(fitted, offset, fitted)
        canvas.convert("RGB").save(destination, format="PNG")
        return

    # Kare logolar şeffaf kalır; Windows yuvarlak köşelerin arkasına kendi
    # kutucuk plakasını çizer.
    _square(source, size).save(destination, format="PNG")


def _default_icon(assets: Path) -> Path:
    for name in ("logo.png", "logo2.png", "logo_source.png"):
        candidate = assets / name
        if candidate.is_file():
            return candidate
    return assets / "logo.png"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    assets = root / "assets"

    parser = argparse.ArgumentParser(description="KobiPass MSIX görsellerini üretir")
    parser.add_argument("--icon", type=Path, default=_default_icon(assets))
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "dist" / "msix-layout" / "Assets",
    )
    args = parser.parse_args()

    if not args.icon.is_file():
        raise SystemExit(f"Kaynak ikon bulunamadi: {args.icon}")

    with Image.open(args.icon) as icon:
        source = icon.convert("RGBA")
        for filename, size in ASSET_SPECS:
            save_asset(source, args.output / filename, size)

    print(f"Kaynak: {args.icon}")
    print(f"MSIX gorselleri uretildi: {args.output} ({len(ASSET_SPECS)} dosya)")


if __name__ == "__main__":
    main()
