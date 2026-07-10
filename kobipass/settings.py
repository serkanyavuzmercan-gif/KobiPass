"""
Uygulama ayarları — son dosyalar, güvenlik zaman aşımları.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings

ORG = "MercanSoftware"
APP = "KobiPass"

RECENT_MAX = 8
DEFAULT_CLIPBOARD_CLEAR_MS = 30_000
DEFAULT_IDLE_LOCK_MS = 5 * 60_000


def _settings() -> QSettings:
    return QSettings(ORG, APP)


def get_recent_files() -> list[str]:
    raw = _settings().value("recent_files", [])
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for item in raw:
        path = str(item).strip()
        if path and path not in result:
            result.append(path)
    return result[:RECENT_MAX]


def add_recent_file(path: Path | str) -> None:
    path_str = str(Path(path).resolve())
    recent = [p for p in get_recent_files() if p != path_str]
    recent.insert(0, path_str)
    _settings().setValue("recent_files", recent[:RECENT_MAX])


def clear_recent_files() -> None:
    _settings().setValue("recent_files", [])


def get_clipboard_clear_ms() -> int:
    value = _settings().value("clipboard_clear_ms", DEFAULT_CLIPBOARD_CLEAR_MS)
    try:
        return max(5_000, int(value))
    except (TypeError, ValueError):
        return DEFAULT_CLIPBOARD_CLEAR_MS


def get_idle_lock_ms() -> int:
    value = _settings().value("idle_lock_ms", DEFAULT_IDLE_LOCK_MS)
    try:
        return max(60_000, int(value))
    except (TypeError, ValueError):
        return DEFAULT_IDLE_LOCK_MS
