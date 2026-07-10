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

import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path

BACKUP_KEEP = 10
_TIME_FMT = "%Y%m%d-%H%M%S"


def backup_dir() -> Path:
    """Yedek klasörü — kasanın bulunduğu diskten bağımsız ikinci konum."""
    override = os.environ.get("KOBIPASS_BACKUP_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "KobiPass" / "backups"
    return Path.home() / ".local" / "share" / "KobiPass" / "backups"


def _backup_stem(vault_path: Path) -> str:
    return vault_path.stem


def create_backup(vault_path: Path) -> Path | None:
    """Kasanın şifreli kopyasını yedek klasörüne yazar; son N kopyayı tutar."""
    vault_path = Path(vault_path)
    if not vault_path.is_file():
        return None
    directory = backup_dir()
    directory.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime(_TIME_FMT)
    target = directory / f"{_backup_stem(vault_path)}-{stamp}.enc"
    # Aynı saniyede ikinci kayıt: sıra numarası ekle.
    counter = 1
    while target.exists():
        target = directory / f"{_backup_stem(vault_path)}-{stamp}-{counter}.enc"
        counter += 1

    shutil.copy2(vault_path, target)
    _prune(directory, _backup_stem(vault_path))
    return target


def find_backups(vault_path: Path | str | None = None) -> list[Path]:
    """Yedekleri en yeniden eskiye listeler; vault_path verilirse o kasaya ait olanlar."""
    directory = backup_dir()
    if not directory.is_dir():
        return []
    if vault_path is not None:
        prefix = f"{_backup_stem(Path(vault_path))}-"
        candidates = [p for p in directory.glob("*.enc") if p.name.startswith(prefix)]
    else:
        candidates = list(directory.glob("*.enc"))
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def restore_backup(backup_path: Path, target_path: Path) -> None:
    """Yedeği asıl konuma geri kopyalar."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    clear_read_only(target_path)
    shutil.copy2(backup_path, target_path)
    set_read_only(target_path)


def set_read_only(path: Path) -> None:
    """Kazara silme/üzerine yazmaya karşı salt-okunur özniteliği basar."""
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        pass  # koruma katmanı — başarısızlığı kaydı engellemesin


def clear_read_only(path: Path) -> None:
    """Kayıttan hemen önce yazma iznini geri verir."""
    try:
        if Path(path).exists():
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass


def _prune(directory: Path, stem: str) -> None:
    prefix = f"{stem}-"
    entries = sorted(
        (p for p in directory.glob("*.enc") if p.name.startswith(prefix)),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in entries[BACKUP_KEEP:]:
        try:
            old.unlink()
        except OSError:
            pass
