"""
Parola araçları — güvenli üreteç ve güç değerlendirme.

Üreteç `secrets` kullanır (kriptografik RNG); güç mantığı hem kayıt
alanlarında hem ana parola göstergesinde ortak kullanılır.
"""

from __future__ import annotations

import secrets

LOWER = "abcdefghijkmnopqrstuvwxyz"          # l çıkarıldı (karışıklık)
UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"           # I, O çıkarıldı
DIGITS = "23456789"                          # 0, 1 çıkarıldı
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"

WEAK = "weak"
MEDIUM = "medium"
STRONG = "strong"

_COLORS = {
    "": "transparent",
    WEAK: "#c42b1c",
    MEDIUM: "#e07020",
    STRONG: "#3ddc84",
}


def generate_password(
    length: int = 16,
    *,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Seçilen karakter sınıflarından güvenli rastgele parola üretir.

    Seçilen her sınıftan en az bir karakter garanti edilir; kalanı tüm
    havuzdan çekilir ve sonuç karıştırılır.
    """
    pools: list[str] = []
    if use_lower:
        pools.append(LOWER)
    if use_upper:
        pools.append(UPPER)
    if use_digits:
        pools.append(DIGITS)
    if use_symbols:
        pools.append(SYMBOLS)
    if not pools:
        pools = [LOWER, UPPER, DIGITS]
    length = max(length, len(pools), 4)

    alphabet = "".join(pools)
    # Her seçili sınıftan en az bir karakter.
    chars = [secrets.choice(pool) for pool in pools]
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    # Fisher–Yates (secrets ile) — sınıf karakterleri baştaki sabit konumda kalmasın.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def password_score(text: str) -> int:
    """0–6 arası kaba güç puanı (uzunluk + karakter çeşitliliği)."""
    if not text:
        return 0
    score = 0
    if len(text) >= 6:
        score += 1
    if len(text) >= 10:
        score += 1
    if len(text) >= 14:
        score += 1
    if any(c.islower() for c in text) and any(c.isupper() for c in text):
        score += 1
    if any(c.isdigit() for c in text):
        score += 1
    if any(not c.isalnum() for c in text):
        score += 1
    return score


def strength_bucket(text: str) -> str:
    """"" / weak / medium / strong."""
    if not text:
        return ""
    score = password_score(text)
    if score <= 2:
        return WEAK
    if score <= 4:
        return MEDIUM
    return STRONG


def strength_color(text: str) -> str:
    return _COLORS[strength_bucket(text)]


def is_weak(text: str) -> bool:
    return bool(text) and strength_bucket(text) == WEAK


def age_days(iso: str) -> int | None:
    """ISO 8601 damgasından bugüne kadar geçen gün sayısı; geçersizse None."""
    if not iso:
        return None
    from datetime import datetime, timezone

    text = iso.strip().replace("Z", "+00:00")
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - when
    return max(0, delta.days)


def humanize_age(iso: str) -> str:
    """Parola yaşını okunur metne çevirir (i18n)."""
    from kobipass.i18n import tr

    days = age_days(iso)
    if days is None:
        return tr("pw_age_unknown")
    if days == 0:
        return tr("pw_age_today")
    if days == 1:
        return tr("pw_age_yesterday")
    if days < 30:
        return tr("pw_age_days", n=days)
    if days < 365:
        return tr("pw_age_months", n=days // 30)
    return tr("pw_age_years", n=days // 365)


def format_date(iso: str) -> str:
    """ISO damgasını yerel 'GG.AA.YYYY' biçimine çevirir; geçersizse boş."""
    if not iso:
        return ""
    from datetime import datetime, timezone

    try:
        when = datetime.fromisoformat(iso.strip().replace("Z", "+00:00"))
    except ValueError:
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone().strftime("%d.%m.%Y")


def pw_freshness_color(iso: str) -> str:
    """Parola yaşına göre tazelik rengi (görsel uyarı)."""
    days = age_days(iso)
    if days is None:
        return "#8a94a8"  # bilinmiyor — nötr gri
    if days < 90:
        return "#3ddc84"  # taze — yeşil
    if days < 365:
        return "#e0b64a"  # eskiyor — amber
    return "#e0685f"  # eski — kırmızı
