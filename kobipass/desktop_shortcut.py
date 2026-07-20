"""
Masaüstü kısayolu oluşturma (yalnızca Windows).

ÖNEMLİ: Kısayol, harici bir betik süreci (ör. ``powershell -ExecutionPolicy
Bypass``) ÇALIŞTIRMADAN, süreç-içi COM (IShellLinkW) ile oluşturulur. Bilinmeyen/
imzasız bir exe'nin PowerShell'i bypass ile başlatması, Windows Defender'ın
davranış motorunda "DefenseEvasion" olarak işaretlenebiliyordu; süreç-içi COM bu
tetikleyiciyi ortadan kaldırır.

İki durum:
- Paketli (MSIX / Store): kısayol AUMID'e işaret eder
  (``explorer.exe shell:AppsFolder\\<AUMID>``) — Store paketleri masaüstüne
  otomatik kısayol koymaz.
- Paketsiz (taşınabilir .exe): kısayol doğrudan .exe'ye işaret eder.

Her hata sessizce False döndürür — uygulamayı asla çökertmez.
"""

from __future__ import annotations

import ctypes
import os
import sys
import uuid
from ctypes import POINTER, byref, c_int, c_void_p, c_wchar_p, wintypes

_SHORTCUT_NAME = "KobiPass.lnk"
_ERROR_INSUFFICIENT_BUFFER = 122
_CLSCTX_INPROC_SERVER = 1


def current_aumid() -> str | None:
    """Paketli (MSIX) uygulamada AUMID (PFN!AppId); paketsizse None."""
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
    except (AttributeError, OSError):
        return None
    length = ctypes.c_uint32(0)
    rc = kernel32.GetCurrentApplicationUserModelId(byref(length), None)
    if rc != _ERROR_INSUFFICIENT_BUFFER or length.value == 0:
        return None
    buf = ctypes.create_unicode_buffer(length.value)
    rc = kernel32.GetCurrentApplicationUserModelId(byref(length), buf)
    if rc != 0:
        return None
    return buf.value or None


def _icon_path() -> str:
    try:
        from kobipass.resources import asset_path

        ico = asset_path("icon.ico")
        if ico.is_file():
            return str(ico)
    except Exception:
        pass
    return ""


def _guid(text: str) -> ctypes.Structure:
    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    return GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


def _vfun(interface: c_void_p, index: int, restype, argtypes):
    """COM arayüzünün vtable'ındaki index'inci metodu çağrılabilir yapar."""
    vtable = ctypes.cast(interface, POINTER(c_void_p))[0]
    func_ptr = ctypes.cast(vtable, POINTER(c_void_p))[index]
    proto = ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)
    return proto(func_ptr)


def _desktop_dir() -> str | None:
    """OneDrive yönlendirmesini de doğru veren gerçek masaüstü klasörü."""
    folderid_desktop = _guid("B4BFCC3A-DB2C-424C-B029-7FE99A87C641")
    path_ptr = c_wchar_p()
    try:
        ctypes.oledll.shell32.SHGetKnownFolderPath(
            byref(folderid_desktop), 0, None, byref(path_ptr)
        )
    except OSError:
        return None
    result = path_ptr.value
    try:
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)
    except OSError:
        pass
    return result


def _create_lnk(target: str, arguments: str, icon: str) -> bool:
    desktop = _desktop_dir()
    if not desktop:
        return False
    lnk_path = os.path.join(desktop, _SHORTCUT_NAME)

    clsid_shelllink = _guid("00021401-0000-0000-C000-000000000046")
    iid_ishelllinkw = _guid("000214F9-0000-0000-C000-000000000046")
    iid_ipersistfile = _guid("0000010B-0000-0000-C000-000000000046")

    ole32 = ctypes.oledll.ole32
    initialized = False
    try:
        ole32.CoInitialize(None)
        initialized = True
    except OSError:
        # COM zaten (ör. Qt tarafından) başlatılmış — sorun değil, sürdür.
        initialized = False

    try:
        psl = c_void_p()
        ole32.CoCreateInstance(
            byref(clsid_shelllink),
            None,
            _CLSCTX_INPROC_SERVER,
            byref(iid_ishelllinkw),
            byref(psl),
        )
        try:
            set_path = _vfun(psl, 20, wintypes.HRESULT, [c_wchar_p])
            set_arguments = _vfun(psl, 11, wintypes.HRESULT, [c_wchar_p])
            set_icon = _vfun(psl, 17, wintypes.HRESULT, [c_wchar_p, c_int])
            set_desc = _vfun(psl, 7, wintypes.HRESULT, [c_wchar_p])
            query_interface = _vfun(
                psl, 0, wintypes.HRESULT, [c_void_p, POINTER(c_void_p)]
            )
            release_sl = _vfun(psl, 2, wintypes.ULONG, [])

            set_path(psl, target)
            if arguments:
                set_arguments(psl, arguments)
            if icon:
                set_icon(psl, icon, 0)
            set_desc(psl, "KobiPass")

            ppf = c_void_p()
            query_interface(psl, byref(iid_ipersistfile), byref(ppf))
            try:
                save = _vfun(ppf, 6, wintypes.HRESULT, [c_wchar_p, wintypes.BOOL])
                release_pf = _vfun(ppf, 2, wintypes.ULONG, [])
                save(ppf, lnk_path, True)
            finally:
                release_pf(ppf)
        finally:
            release_sl(psl)
        return os.path.exists(lnk_path)
    finally:
        if initialized:
            try:
                ole32.CoUninitialize()
            except OSError:
                pass


def create_desktop_shortcut() -> bool:
    """Masaüstüne KobiPass kısayolu oluşturur (süreç-içi COM). Başarılıysa True."""
    if sys.platform != "win32":
        return False

    aumid = current_aumid()
    if aumid:
        windir = os.environ.get("WINDIR", r"C:\Windows")
        target = os.path.join(windir, "explorer.exe")
        arguments = "shell:AppsFolder\\" + aumid
        icon = _icon_path()
    else:
        target = sys.executable
        arguments = ""
        icon = sys.executable

    try:
        return _create_lnk(target, arguments, icon)
    except Exception:
        return False
