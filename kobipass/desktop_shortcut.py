"""
Masaüstü kısayolu oluşturma (yalnızca Windows).

İki durum vardır:
- Paketli (MSIX / Store): kısayol, uygulamanın AUMID'sine işaret eder
  (``explorer.exe shell:AppsFolder\\<AUMID>``). Store paketleri masaüstüne
  otomatik kısayol koymaz; bu yüzden uygulama ilk açılışta kullanıcıya sorup
  bunu oluşturur.
- Paketsiz (taşınabilir .exe): kısayol doğrudan .exe'ye işaret eder ve ikonu
  exe'nin gömülü ikonundan alır.

Kısayol, güvenilir tırnak/OneDrive yönlendirmesi için WScript.Shell üzerinden
(PowerShell) oluşturulur; böylece ek Python bağımlılığı gerekmez. Her hata
sessizce False döndürür — uygulamayı asla çökertmez.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path

_SHORTCUT_NAME = "KobiPass.lnk"
_CREATE_NO_WINDOW = 0x08000000
_ERROR_INSUFFICIENT_BUFFER = 122


def current_aumid() -> str | None:
    """Paketli (MSIX) uygulamada AUMID (PFN!AppId); paketsizse None."""
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
    except (AttributeError, OSError):
        return None
    length = ctypes.c_uint32(0)
    rc = kernel32.GetCurrentApplicationUserModelId(ctypes.byref(length), None)
    if rc != _ERROR_INSUFFICIENT_BUFFER or length.value == 0:
        return None
    buf = ctypes.create_unicode_buffer(length.value)
    rc = kernel32.GetCurrentApplicationUserModelId(ctypes.byref(length), buf)
    if rc != 0:
        return None
    return buf.value or None


def _icon_path() -> str:
    """Paketli (onedir) kurulumda kalıcı ikon yolu; yoksa boş."""
    try:
        from kobipass.resources import asset_path

        ico = asset_path("icon.ico")
        if ico.is_file():
            return str(ico)
    except Exception:
        pass
    return ""


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _run_powershell(script: str) -> bool:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "-",
            ],
            input=script,
            text=True,
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
            timeout=25,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def create_desktop_shortcut() -> bool:
    """Masaüstüne KobiPass kısayolu oluşturur. Başarılıysa True.

    Yalnızca Windows'ta çalışır. Paketli uygulamada AUMID'e, paketsiz .exe'de
    doğrudan yürütülebilir dosyaya işaret eder.
    """
    if sys.platform != "win32":
        return False

    aumid = current_aumid()
    if aumid:
        # Paketli (MSIX): shell üzerinden AUMID ile başlat.
        target = r"%WINDIR%\explorer.exe"
        arguments = f"shell:AppsFolder\\{aumid}"
        icon = _icon_path()
    else:
        # Paketsiz: exe'nin kendisi (frozen değilse anlamsız — çağıran taraf
        # zaten yalnızca frozen'da teklif eder).
        target = sys.executable
        arguments = ""
        icon = sys.executable

    lines = [
        "$ErrorActionPreference='Stop'",
        "$desktop=[Environment]::GetFolderPath('Desktop')",
        f"$lnk=Join-Path $desktop {_ps_quote(_SHORTCUT_NAME)}",
        "$w=New-Object -ComObject WScript.Shell",
        "$s=$w.CreateShortcut($lnk)",
        f"$s.TargetPath={_ps_quote(target)}",
        f"$s.Arguments={_ps_quote(arguments)}",
        "$s.Description='KobiPass'",
    ]
    if icon:
        lines.append(f"$s.IconLocation={_ps_quote(icon)}")
    lines.append("$s.Save()")
    return _run_powershell("\n".join(lines))
