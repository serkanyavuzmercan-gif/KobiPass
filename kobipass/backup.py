"""
Kasa dosyası koruması — otomatik şifreli yedekler + salt-okunur kilidi.

Amaç: .enc dosyasının bilerek veya yanlışlıkla silinmesine karşı dayanıklılık.
Yedekler dosyanın ŞİFRELİ birebir kopyasıdır; parolasız açılamazlar, bu yüzden
ek bir sızıntı yüzeyi oluşturmazlar.

- Her başarılı kayıtta kopya: %APPDATA%/KobiPass/backups (Windows) veya
  ~/.local/share/KobiPass/backups (diğer platformlar).
- Kasa başına son BACKUP_KEEP kopya tutulur; eskiler silinir.
- Kayıt sonrası dosyaya salt-okunur özniteliği basılır; kayıt öncesi kaldırılır.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BACKUP_KEEP = 10
_TIME_FMT = "%Y%m%d-%H%M%S-%f"

# Kasa dosyası izinleri: YALNIZCA sahibi okuyabilir (0400). Eskiden gruba ve
# herkese okuma izni veriliyordu (0444); çok kullanıcılı bir makinede şifreli
# de olsa kasa dosyasının herkese açık olması gereksiz bir saldırı yüzeyidir
# (çevrimdışı parola denemesi için dosyanın kopyalanması yeterli).
_VAULT_READ_ONLY = stat.S_IRUSR
_VAULT_READ_WRITE = stat.S_IRUSR | stat.S_IWUSR
# Yedekler sahibi tarafından SİLİNEBİLİR olmalı: Windows'ta salt-okunur
# özniteliği unlink() çağrısını engeller ve budama sessizce başarısız olurdu
# (yedekler sonsuza kadar birikirdi).
_BACKUP_MODE = stat.S_IRUSR | stat.S_IWUSR


def backup_dir() -> Path:
    """Yedek klasörü — kasanın bulunduğu diskten bağımsız ikinci konum."""
    override = os.environ.get("KOBIPASS_BACKUP_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "KobiPass" / "backups"
    return Path.home() / ".local" / "share" / "KobiPass" / "backups"


def _location_tag(vault_path: Path) -> str:
    """Kasanın BULUNDUĞU KLASÖRÜ temsil eden kısa etiket.

    Tüm yedekler tek bir klasörde toplandığından, farklı dizinlerdeki aynı adlı
    iki kasa ("C:/is/kasa.enc" ve "D:/ev/kasa.enc") aynı yedek adını üretiyordu:
    listeleme birini diğerinin yedeği sanıyor, budama BAŞKA KASANIN yedeklerini
    siliyordu. Klasör yolunun kısa özeti adları ayırır.
    """
    try:
        parent = Path(vault_path).expanduser().resolve().parent
    except OSError:
        parent = Path(vault_path).absolute().parent
    raw = str(parent)
    if sys.platform == "win32":
        raw = raw.lower()
    return hashlib.sha256(raw.encode("utf-8", "surrogateescape")).hexdigest()[:8]


def _backup_stem(vault_path: Path) -> str:
    """Yeni yedeklerin ad öneki: "<kasa adı>~<klasör etiketi>"."""
    return f"{Path(vault_path).stem}~{_location_tag(vault_path)}"


def _legacy_stem(vault_path: Path) -> str:
    """Klasör etiketi eklenmeden önce üretilmiş yedeklerin öneki."""
    return Path(vault_path).stem


# Yedek adı: "<önek>-<tarih>-<saat>[-<mikrosaniye>][-<sayaç>].enc"
# Önekten SONRA mutlaka zaman damgası gelmeli. Düz önek ("kasa-" ile başlıyor
# mu) kontrolü yetmez: o zaman "kasa.enc", "kasa-yedek.enc" kasasının
# yedeklerini de kendi yedeği sanar; budama sırasında BAŞKA KASANIN YEDEKLERİNİ
# SİLER ve geri yükleme listesinde yanlış kasayı gösterir.
_STAMP_SUFFIX = re.compile(r"^-\d{8}-\d{6}(?:-\d{6})?(?:-\d+)?$")


def _is_backup_of(path: Path, stem: str) -> bool:
    """``path`` adlı dosya, ``stem`` önekli kasanın yedeği mi?"""
    name = path.stem
    if not name.startswith(stem):
        return False
    return bool(_STAMP_SUFFIX.match(name[len(stem) :]))


def _backups_for(directory: Path, vault_path: Path) -> list[Path]:
    """Bu kasaya ait yedekler — yeni (klasör etiketli) ve eski adlandırma.

    Eski yedekler hangi klasörden geldiklerini taşımaz; ayırt edilemezler.
    Geri yükleme listesinde görünmeye devam ederler, yenileri biriktikçe
    budamayla doğal olarak yerlerini yeni ada bırakırlar.
    """
    stem = _backup_stem(vault_path)
    legacy = _legacy_stem(vault_path)
    return [
        p
        for p in directory.glob("*.enc")
        if _is_backup_of(p, stem) or _is_backup_of(p, legacy)
    ]


def _backup_sort_key(path: Path) -> tuple[str, str, int, int]:
    """Yeni/legacy yedek adlarını kronolojik ve sayaç bazlı güvenilir sıralar."""
    stem = path.stem
    modern = re.search(r"-(\d{8})-(\d{6})-(\d{6})(?:-(\d+))?$", stem)
    if modern:
        date, clock, micros, counter = modern.groups()
        return date, clock, int(micros), int(counter or 0)
    legacy = re.search(r"-(\d{8})-(\d{6})(?:-(\d+))?$", stem)
    if legacy:
        date, clock, counter = legacy.groups()
        return date, clock, 0, int(counter or 0)
    stat_result = path.stat()
    return "", "", stat_result.st_mtime_ns, 0


def create_backup(vault_path: Path) -> Path | None:
    """Kasanın şifreli kopyasını yedek klasörüne yazar; son N kopyayı tutar."""
    vault_path = Path(vault_path)
    if not vault_path.is_file():
        return None
    directory = backup_dir()
    directory.mkdir(parents=True, exist_ok=True)

    prefix = _backup_stem(vault_path)
    stamp = datetime.now().strftime(_TIME_FMT)
    target = directory / f"{prefix}-{stamp}.enc"
    # Aynı saniyede ikinci kayıt: sıra numarası ekle.
    counter = 1
    while target.exists():
        target = directory / f"{prefix}-{stamp}-{counter}.enc"
        counter += 1

    shutil.copy2(vault_path, target)
    # copy2 kaynak mtime'ını korur; hızlı ardışık kayıtlarda sıralama eşitlenmesin.
    target.touch()
    # copy2 kaynak izinlerini de kopyalar; yedek salt-okunur kalırsa Windows'ta
    # budama silemez. Sahibe okuma+yazma, başkasına hiçbir şey.
    try:
        os.chmod(target, _BACKUP_MODE)
    except OSError:
        pass
    _prune(directory, vault_path)
    return target


def find_backups(vault_path: Path | str | None = None) -> list[Path]:
    """Yedekleri en yeniden eskiye listeler; vault_path verilirse o kasaya ait olanlar."""
    directory = backup_dir()
    if not directory.is_dir():
        return []
    if vault_path is not None:
        candidates = _backups_for(directory, Path(vault_path))
    else:
        candidates = list(directory.glob("*.enc"))
    return sorted(candidates, key=_backup_sort_key, reverse=True)


def restore_backup(backup_path: Path, target_path: Path) -> None:
    """Yedeği asıl konuma ATOMİK olarak geri kopyalar.

    Doğrudan üzerine yazmak tehlikeliydi: kopyalama ortasında disk dolarsa veya
    elektrik giderse hedefte YARIM bir dosya kalıyordu — hem mevcut kasa hem de
    geri yükleme kayboluyordu. Önce aynı klasöre geçici dosya yazılır, diske
    boşaltılır, sonra os.replace ile tek adımda yerine geçer.
    """
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    clear_read_only(target_path)

    fd, tmp_name = tempfile.mkstemp(
        dir=str(target_path.parent), prefix=f".{target_path.name}.", suffix=".tmp"
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        shutil.copyfile(backup_path, tmp_path)
        with open(tmp_path, "rb") as handle:
            os.fsync(handle.fileno())
        os.chmod(tmp_path, _VAULT_READ_WRITE)
        os.replace(tmp_path, target_path)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise
    set_read_only(target_path)


def set_read_only(path: Path) -> None:
    """Kazara silme/üzerine yazmaya karşı salt-okunur özniteliği basar."""
    try:
        os.chmod(path, _VAULT_READ_ONLY)
    except OSError:
        pass  # koruma katmanı — başarısızlığı kaydı engellemesin


def clear_read_only(path: Path) -> None:
    """Kayıttan hemen önce yazma iznini geri verir."""
    try:
        if Path(path).exists():
            os.chmod(path, _VAULT_READ_WRITE)
    except OSError:
        pass


def _prune(directory: Path, vault_path: Path) -> None:
    entries = sorted(
        _backups_for(directory, vault_path),
        key=_backup_sort_key,
        reverse=True,
    )
    for old in entries[BACKUP_KEEP:]:
        try:
            # Windows: salt-okunur öznitelik silmeyi engeller (eski sürümlerde
            # üretilmiş yedekler kaynağın iznini miras almış olabilir).
            os.chmod(old, _BACKUP_MODE)
        except OSError:
            pass
        try:
            old.unlink()
        except OSError:
            pass
