"""
Yardım penceresi HTML içeriği (TR / EN).
"""

from __future__ import annotations

import math
from decimal import Decimal

from kobipass.crypto import NONCE_SIZE, PBKDF2_ITERATIONS, SALT_SIZE
from kobipass.i18n import MIN_PASSWORD_LENGTH, i18n


def _format_number(value: float | Decimal, decimals: int = 0) -> str:
    lang = i18n.lang
    if isinstance(value, Decimal):
        if decimals == 0:
            num = int(value)
            text = f"{num:,}"
        else:
            quant = Decimal("0." + "0" * (decimals - 1) + "1")
            text = f"{value.quantize(quant):,.{decimals}f}"
    elif decimals == 0:
        text = f"{int(round(value)):,}"
    else:
        text = f"{value:,.{decimals}f}"

    if lang == "tr":
        return text.replace(",", "X").replace(".", ",").replace("X", ".")
    return text


def _crack_estimate_paragraph() -> str:
    charset_size = 94
    password_len = MIN_PASSWORD_LENGTH
    guesses_per_second = 100
    seconds_per_year = 365.25 * 24 * 3600
    universe_age_years = Decimal("13800000000")

    combinations = charset_size**password_len
    entropy_bits = password_len * math.log2(charset_size)
    avg_guesses = combinations // 2
    avg_seconds = avg_guesses // guesses_per_second
    avg_years = Decimal(avg_seconds) / Decimal(int(seconds_per_year))
    universe_ratio = avg_years / universe_age_years
    trillion_years = avg_years / Decimal(10**12)

    exp = int(math.floor(math.log10(combinations)))
    mantissa = combinations / (10**exp)
    sep = "," if i18n.is_tr() else "."
    comb_display = f"{mantissa:.2f}".replace(".", sep) + f" × 10<sup>{exp}</sup>"

    if i18n.is_tr():
        return (
            f"Örneğin büyük/küçük harf, rakam ve sembol içeren "
            f"<b>{password_len} karakterlik</b> güçlü bir parola için olası kombinasyon "
            f"sayısı yaklaşık <b>{comb_display}</b> "
            f"(≈ <b>{entropy_bits:.1f}".replace(".", sep)
            + f" bit</b> entropi) değerindedir. "
            f"KobiPass her tahminde <b>{_format_number(PBKDF2_ITERATIONS)}</b> iterasyonlu "
            f"PBKDF2 uyguladığından tek bir tahmin maliyetlidir."
        )

    return (
        f"For example, a strong <b>{password_len}-character</b> password has about "
        f"<b>{comb_display}</b> combinations (≈ <b>{entropy_bits:.1f} bits</b> of entropy). "
        f"KobiPass runs PBKDF2 with <b>{_format_number(PBKDF2_ITERATIONS)}</b> "
        f"iterations per guess, so each attempt is costly."
    )


def help_html() -> str:
    iterations = (
        f"{PBKDF2_ITERATIONS:,}".replace(",", ".")
        if i18n.is_tr()
        else f"{PBKDF2_ITERATIONS:,}"
    )
    crack_note = _crack_estimate_paragraph()

    if i18n.is_tr():
        return f"""
    <h2 style="color:#e8eaed;margin-top:0;">KobiPass</h2>
    <p style="color:#9aa0a8;line-height:1.5;">
    Hidroteknik Yazılım ekibi tarafından geliştirilen KobiPass parola kasası. Her <code>.enc</code> dosyasında
    <b>1 yönetici</b> ve en fazla <b>3 kullanıcı</b> parolası tanımlanır.
    Yönetici tam yetkilidir; kullanıcılar yalnızca izin verilen alanları görür veya düzenler.
  </p>
    <p style="color:#9aa0a8;line-height:1.5;">{crack_note}</p>

    <h3 style="color:#e8eaed;">Roller</h3>
    <ul style="color:#c8ccd2;line-height:1.55;">
    <li><b>Yönetici</b> — Tüm kayıtlar, kullanıcı parolaları, izinler ve değişiklik geçmişi.</li>
    <li><b>Kullanıcı 1–3</b> — Ortak izin şablonu; değişiklikler loglanır.</li>
    </ul>

    <h3 style="color:#e8eaed;">Nasıl kullanılır?</h3>
    <ul style="color:#c8ccd2;line-height:1.55;">
    <li><b>Dosya Aç</b> — <code>.enc</code> seçin; yönetici veya kullanıcı parolanızı girin.</li>
    <li><b>Kaydet</b> — İlk kayıtta yönetici + kullanıcı parolaları ve izinler belirlenir.</li>
    <li><b>Kilitle</b> — Oturumu kapatır; aynı dosyayı tekrar parola ile açarsınız.</li>
    <li><b>Kullanıcılar & İzinler</b> — Yalnızca yönetici (parola ve alan izinleri).</li>
    <li><b>Değişiklik Geçmişi</b> — Yalnızca yönetici (kullanıcı düzenlemeleri).</li>
    </ul>

    <h3 style="color:#e8eaed;">Şifreleme (KBPS)</h3>
    <ul style="color:#c8ccd2;line-height:1.55;">
    <li>Zarf şifreleme: rastgele DEK + yönetici/kullanıcı sarmalayıcıları.</li>
    <li><b>PBKDF2-HMAC-SHA256</b> — {iterations} iterasyon, {SALT_SIZE} bayt salt.</li>
    <li><b>AES-256-GCM</b> — {NONCE_SIZE} bayt nonce.</li>
    <li>Dosya başlığı: <code>KBPS</code> (<code>PFRT</code> formatıyla uyumsuz).</li>
    </ul>
    <p style="color:#f0c14b;font-size:12px;">
    Parolayı unutursanız veriler kurtarılamaz.
    </p>
    """

    return f"""
    <h2 style="color:#e8eaed;margin-top:0;">KobiPass</h2>
    <p style="color:#9aa0a8;line-height:1.5;">
    SMB password vault developed by the Hidroteknik Yazılım team. Each <code>.enc</code> file has
    <b>1 admin</b> and up to <b>3 user</b> passwords.
    The admin has full access; users may only view or edit permitted fields.
    </p>
    <p style="color:#9aa0a8;line-height:1.5;">{crack_note}</p>

    <h3 style="color:#e8eaed;">Roles</h3>
    <ul style="color:#c8ccd2;line-height:1.55;">
    <li><b>Administrator</b> — All records, user passwords, permissions, change history.</li>
    <li><b>Users 1–3</b> — Shared permission template; changes are logged.</li>
    </ul>

    <h3 style="color:#e8eaed;">How to use</h3>
    <ul style="color:#c8ccd2;line-height:1.55;">
    <li><b>Open File</b> — Select <code>.enc</code>; enter admin or user password.</li>
    <li><b>Save</b> — On first save, set admin + user passwords and permissions.</li>
    <li><b>Lock</b> — End session; reopen the same file with password.</li>
    <li><b>Users & Permissions</b> — Admin only.</li>
    <li><b>Change History</b> — Admin only (user edits).</li>
    </ul>

    <h3 style="color:#e8eaed;">Encryption (KBPS)</h3>
    <ul style="color:#c8ccd2;line-height:1.55;">
    <li>Envelope encryption: random DEK + admin/user wraps.</li>
    <li><b>PBKDF2-HMAC-SHA256</b> — {iterations} iterations, {SALT_SIZE}-byte salt.</li>
    <li><b>AES-256-GCM</b> — {NONCE_SIZE}-byte nonce.</li>
    <li>File header: <code>KBPS</code> (not compatible with <code>PFRT</code> format).</li>
    </ul>
    <p style="color:#f0c14b;font-size:12px;">
    If you forget your password, data cannot be recovered.
    </p>
    """
