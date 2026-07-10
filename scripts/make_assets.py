#!/usr/bin/env python3
"""
KobiPass logo işleme: arka plan temizleme, logo.png ve icon.ico üretimi.

Kaynak öncelik sırası: assets/logo2.png → assets/logo_source.png
(veya komut satırı argümanı). Beyaz veya siyah arka plan desteklenir.
"""

from __future__ import annotations

import math
import sys
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# Yeni logo (logo2.png) varsa onu kaynak al; yoksa eski logo_source.png'ye düş.
_SOURCE_CANDIDATES = ("logo2.png", "logo_source.png")


def _default_source() -> Path:
    for name in _SOURCE_CANDIDATES:
        candidate = ASSETS / name
        if candidate.is_file():
            return candidate
    return ASSETS / _SOURCE_CANDIDATES[-1]


SOURCE = _default_source()
LOGO_OUT = ASSETS / "logo.png"
ICON_OUT = ASSETS / "icon.ico"

LOGO_HEIGHT = 256


def _color_dist(c1: tuple[int, ...], c2: tuple[int, ...]) -> float:
    return math.sqrt(sum((int(a) - int(b)) ** 2 for a, b in zip(c1, c2)))


def _luminance(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def _chroma_span(r: int, g: int, b: int) -> int:
    return max(r, g, b) - min(r, g, b)


def _corner_background(img: Image.Image) -> tuple[int, int, int]:
    w, h = img.size
    corners = [
        img.getpixel((0, 0))[:3],
        img.getpixel((w - 1, 0))[:3],
        img.getpixel((0, h - 1))[:3],
        img.getpixel((w - 1, h - 1))[:3],
    ]
    return tuple(sum(c[i] for c in corners) // 4 for i in range(3))  # type: ignore[return-value]


def _is_dark_background(bg: tuple[int, int, int]) -> bool:
    return _luminance(*bg) < 64.0


def _is_background_pixel(
    rgb: tuple[int, int, int],
    bg: tuple[int, int, int],
    tolerance: float,
    dark_bg: bool,
) -> bool:
    r, g, b = rgb
    if _color_dist(rgb, bg) <= tolerance:
        return True

    lum = _luminance(r, g, b)
    span = _chroma_span(r, g, b)

    if dark_bg:
        # Siyah / cok koyu arka plan ve kulac icindeki bosluklar
        if lum <= 32 and span <= 24:
            return True
        return False

    # Beyaz / acik arka plan
    if lum >= 248 and span <= 18:
        return True
    return False


def _is_void_black(rgb: tuple[int, int, int], lum_max: float = 30.0) -> bool:
    r, g, b = rgb
    lum = _luminance(r, g, b)
    return lum <= lum_max and _chroma_span(r, g, b) <= 26


def remove_background_flood(
    img: Image.Image,
    tolerance: float = 42.0,
) -> Image.Image:
    """Kenarlardan flood-fill ile arka plani seffaf yapar."""
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size
    bg = _corner_background(rgba)
    dark_bg = _is_dark_background(bg)

    if dark_bg:
        tolerance = max(tolerance, 55.0)

    transparent = [[False] * w for _ in range(h)]
    queue: deque[tuple[int, int]] = deque()

    def try_seed(x: int, y: int) -> None:
        if 0 <= x < w and 0 <= y < h:
            rgb = pixels[x, y][:3]
            if _is_background_pixel(rgb, bg, tolerance, dark_bg):
                queue.append((x, y))

    for x in range(w):
        try_seed(x, 0)
        try_seed(x, h - 1)
    for y in range(h):
        try_seed(0, y)
        try_seed(w - 1, y)

    while queue:
        x, y = queue.popleft()
        if transparent[y][x]:
            continue
        rgb = pixels[x, y][:3]
        if not _is_background_pixel(rgb, bg, tolerance, dark_bg):
            continue
        transparent[y][x] = True
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and not transparent[ny][nx]:
                queue.append((nx, ny))

    rgba = _remove_enclosed_voids(rgba, lum_max=38.0)
    rgba = _remove_enclosed_voids(rgba, lum_max=38.0)
    rgba = _purge_near_black(rgba, lum_max=24.0)
    rgba = _strip_outer_halos(rgba, bg, tolerance, dark_bg)
    rgba = _grow_transparency_into_voids(rgba, lum_max=42.0)
    rgba = _feather_edges(rgba, bg, tolerance, dark_bg)
    rgba = _finalize_cleanup(rgba)
    return _remove_detached_specks(rgba)


def _purge_near_black(img: Image.Image, lum_max: float = 24.0) -> Image.Image:
    """Saf siyaha yakin pikselleri temizler (turuncu ve metal golgeleri korunur)."""
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            if _luminance(r, g, b) <= lum_max and _chroma_span(r, g, b) <= 20:
                pixels[x, y] = (0, 0, 0, 0)
    return img


def _grow_transparency_into_voids(
    img: Image.Image,
    lum_max: float = 42.0,
    passes: int = 6,
) -> Image.Image:
    """Seffaf kenara bitisen siyah bolgeleri iceri dogru genisletir."""
    pixels = img.load()
    w, h = img.size

    def touches_transparent(x: int, y: int) -> bool:
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and pixels[nx, ny][3] == 0:
                return True
        return False

    for _ in range(passes):
        removed: list[tuple[int, int]] = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a == 0 or not touches_transparent(x, y):
                    continue
                if _is_void_black((r, g, b), lum_max):
                    removed.append((x, y))
        if not removed:
            break
        for x, y in removed:
            pixels[x, y] = (0, 0, 0, 0)
    return img


def _remove_enclosed_voids(img: Image.Image, lum_max: float = 30.0) -> Image.Image:
    """Kulac icindeki vb. dis kenara baglanmayan siyah bolgeleri siler."""
    pixels = img.load()
    w, h = img.size
    visited = [[False] * w for _ in range(h)]

    for sy in range(h):
        for sx in range(w):
            if visited[sy][sx]:
                continue
            r, g, b, a = pixels[sx, sy]
            if a == 0 or not _is_void_black((r, g, b), lum_max):
                continue

            component: list[tuple[int, int]] = []
            touches_border = False
            q: deque[tuple[int, int]] = deque([(sx, sy)])

            while q:
                x, y = q.popleft()
                if visited[y][x]:
                    continue
                visited[y][x] = True
                pr, pg, pb, pa = pixels[x, y]
                if pa == 0 or not _is_void_black((pr, pg, pb), lum_max):
                    continue
                component.append((x, y))
                if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                    touches_border = True
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                        q.append((nx, ny))

            if not touches_border:
                for x, y in component:
                    pixels[x, y] = (0, 0, 0, 0)

    return img


def _strip_outer_halos(
    img: Image.Image,
    bg: tuple[int, int, int],
    tolerance: float,
    dark_bg: bool,
) -> Image.Image:
    """Dis kenardaki arka plan halesini iteratif temizler."""
    pixels = img.load()
    w, h = img.size

    def touches_transparent(x: int, y: int) -> bool:
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and pixels[nx, ny][3] == 0:
                return True
        return False

    for _ in range(8):
        removed: list[tuple[int, int]] = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a == 0 or not touches_transparent(x, y):
                    continue
                lum = _luminance(r, g, b)
                span = _chroma_span(r, g, b)
                if _color_dist((r, g, b), bg) <= tolerance:
                    removed.append((x, y))
                    continue
                if dark_bg and lum <= 36 and span <= 28:
                    removed.append((x, y))
                    continue
                if not dark_bg and lum >= 232 and span <= 28:
                    removed.append((x, y))
        if not removed:
            break
        for x, y in removed:
            pixels[x, y] = (0, 0, 0, 0)
    return img


def _feather_edges(
    img: Image.Image,
    bg: tuple[int, int, int],
    tolerance: float,
    dark_bg: bool,
) -> Image.Image:
    """Yalnizca seffaf kenara bitisen piksellerde yumusak alpha."""
    pixels = img.load()
    w, h = img.size
    feather = 22.0

    def touches_transparent(x: int, y: int) -> bool:
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and pixels[nx, ny][3] == 0:
                return True
        return False

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0 or not touches_transparent(x, y):
                continue
            dist = _color_dist((r, g, b), bg)
            lum = _luminance(r, g, b)
            near_bg = dist <= tolerance + feather
            if dark_bg:
                near_bg = near_bg or lum <= 36 + feather / 2
            if near_bg:
                if dark_bg:
                    blend = min(1.0, lum / 40.0) if lum < 40 else 1.0
                    if blend < 0.35:
                        pixels[x, y] = (0, 0, 0, 0)
                        continue
                else:
                    blend = (dist - tolerance) / feather
                    blend = max(0.0, min(1.0, blend))
                new_a = int(a * blend)
                if new_a <= 0:
                    pixels[x, y] = (0, 0, 0, 0)
                else:
                    pixels[x, y] = (r, g, b, new_a)
    return img


def _finalize_cleanup(img: Image.Image) -> Image.Image:
    """Siyah saçaklari ve dusuk-alpha artefaktlari temizler (resize sonrasi da)."""
    img = _purge_near_black(img, lum_max=30.0)
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            if a < 20:
                pixels[x, y] = (0, 0, 0, 0)
                continue
            if max(r, g, b) < 18 and _chroma_span(r, g, b) <= 18:
                pixels[x, y] = (0, 0, 0, 0)
    img = _grow_transparency_into_voids(img, lum_max=34.0, passes=4)
    return _remove_detached_specks(img, min_area=95, anchor_min_area=1200, dilate=8)


def _remove_detached_specks(
    img: Image.Image,
    min_area: int = 90,
    anchor_min_area: int = 1800,
    dilate: int = 10,
) -> Image.Image:
    """Logodan kopuk kucuk adaciklari (parilti, kirinti) siler."""
    pixels = img.load()
    w, h = img.size
    visited = [[False] * w for _ in range(h)]
    components: list[list[tuple[int, int]]] = []

    for sy in range(h):
        for sx in range(w):
            if visited[sy][sx] or pixels[sx, sy][3] == 0:
                visited[sy][sx] = True
                continue
            component: list[tuple[int, int]] = []
            q: deque[tuple[int, int]] = deque([(sx, sy)])
            while q:
                x, y = q.popleft()
                if visited[y][x] or pixels[x, y][3] == 0:
                    visited[y][x] = True
                    continue
                visited[y][x] = True
                component.append((x, y))
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                        q.append((nx, ny))
            components.append(component)

    anchor = [[False] * w for _ in range(h)]
    for component in components:
        if len(component) < anchor_min_area:
            continue
        for x, y in component:
            anchor[y][x] = True

    if not any(any(row) for row in anchor):
        return img

    dilated = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if not anchor[y][x]:
                continue
            for dy in range(-dilate, dilate + 1):
                for dx in range(-dilate, dilate + 1):
                    if dx * dx + dy * dy > dilate * dilate:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        dilated[ny][nx] = True

    def is_grey_debris_component(component: list[tuple[int, int]]) -> bool:
        if len(component) >= 220:
            return False
        warm = 0
        for x, y in component:
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            if r >= 118 or (r >= 95 and r - min(g, b) >= 28):
                warm += 1
        return warm < max(4, len(component) // 5)

    for component in components:
        if len(component) >= min_area and not is_grey_debris_component(component):
            continue
        if len(component) < min_area and is_grey_debris_component(component):
            for x, y in component:
                pixels[x, y] = (0, 0, 0, 0)
            continue
        if any(dilated[y][x] for x, y in component):
            continue
        for x, y in component:
            pixels[x, y] = (0, 0, 0, 0)
    return img


def _resize_rgba(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    resized = img.resize(size, Image.Resampling.LANCZOS)
    return _finalize_cleanup(resized)


def trim_transparent(img: Image.Image, pad: int = 8) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img.width, right + pad)
    bottom = min(img.height, bottom + pad)
    return img.crop((left, top, right, bottom))


def center_on_square(img: Image.Image, size: int, padding_ratio: float = 0.06) -> Image.Image:
    cw, ch = img.size
    side = max(cw, ch)
    pad = int(side * padding_ratio)
    canvas_side = side + 2 * pad
    square = Image.new("RGBA", (canvas_side, canvas_side), (0, 0, 0, 0))
    square.paste(img, (pad + (side - cw) // 2, pad + (side - ch) // 2), img)
    return _resize_rgba(square, (size, size))


def make_logo_png(processed: Image.Image) -> Image.Image:
    cropped = trim_transparent(processed, pad=4)
    w, h = cropped.size
    new_h = LOGO_HEIGHT
    new_w = max(1, int(w * new_h / h))
    return _resize_rgba(cropped, (new_w, new_h))


def make_icon(processed: Image.Image) -> None:
    master = center_on_square(processed, 256)
    sizes = [256, 128, 64, 48, 32, 24, 16]
    images = [_resize_rgba(master, (side, side)) for side in sizes]
    images[0].save(
        ICON_OUT,
        format="ICO",
        sizes=[(side, side) for side in sizes],
        append_images=images[1:],
    )
    size_kb = ICON_OUT.stat().st_size / 1024
    if size_kb < 8:
        raise SystemExit(f"icon.ico cok kucuk ({size_kb:.1f} KB)")


def process_source(path: Path) -> Image.Image:
    if not path.is_file():
        raise SystemExit(f"Kaynak logo bulunamadi: {path}")
    raw = Image.open(path)
    cleaned = remove_background_flood(raw)
    return trim_transparent(cleaned, pad=6)


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE
    ASSETS.mkdir(parents=True, exist_ok=True)

    processed = process_source(source)
    logo = make_logo_png(processed)
    logo.save(LOGO_OUT, format="PNG", optimize=True)
    make_icon(processed)

    print(f"Kaynak: {source}")
    print(f"Logo:   {LOGO_OUT} ({logo.width}x{logo.height})")
    print(f"Ikon:   {ICON_OUT} ({ICON_OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
