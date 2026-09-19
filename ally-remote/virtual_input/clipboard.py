"""Área de transferência do Windows via Win32, sem dependências extras."""

import ctypes
import time
from ctypes import wintypes

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
_kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
_kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalLock.restype = ctypes.c_void_p
_kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]

_user32.GetClipboardData.argtypes = [wintypes.UINT]
_user32.GetClipboardData.restype = wintypes.HANDLE
_user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
_user32.SetClipboardData.restype = wintypes.HANDLE


def _open(retries: int = 10, delay: float = 0.02) -> bool:
    for _ in range(max(1, retries)):
        if _user32.OpenClipboard(None):
            return True
        time.sleep(delay)
    return False


def get_text() -> dict:
    if not _open():
        return {"ok": False, "error": "área de transferência ocupada"}
    try:
        if not _user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return {"ok": True, "text": ""}
        handle = _user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return {"ok": False, "error": "não foi possível ler o clipboard"}
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            return {"ok": False, "error": "não foi possível acessar o clipboard"}
        try:
            return {"ok": True, "text": ctypes.wstring_at(ptr)}
        finally:
            _kernel32.GlobalUnlock(handle)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        _user32.CloseClipboard()


def set_text(text: str) -> dict:
    value = str(text)
    if not _open():
        return {"ok": False, "error": "área de transferência ocupada"}

    hmem = None
    ownership_transferred = False
    try:
        if not _user32.EmptyClipboard():
            return {"ok": False, "error": "não foi possível limpar o clipboard"}

        buf = ctypes.create_unicode_buffer(value)
        size = ctypes.sizeof(buf)
        hmem = _kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not hmem:
            return {"ok": False, "error": "falha ao alocar memória para o clipboard"}

        ptr = _kernel32.GlobalLock(hmem)
        if not ptr:
            return {"ok": False, "error": "falha ao bloquear memória do clipboard"}
        try:
            ctypes.memmove(ptr, ctypes.addressof(buf), size)
        finally:
            _kernel32.GlobalUnlock(hmem)

        if not _user32.SetClipboardData(CF_UNICODETEXT, hmem):
            return {"ok": False, "error": "falha ao gravar no clipboard"}
        ownership_transferred = True
        return {"ok": True, "chars": len(value)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        _user32.CloseClipboard()
        if hmem and not ownership_transferred:
            _kernel32.GlobalFree(hmem)
