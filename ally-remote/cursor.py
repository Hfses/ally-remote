"""
cursor.py — Visibilidade do ponteiro do mouse (Windows).

Dois recursos:

1. set_size(step): muda o tamanho do ponteiro (1 = normal … 15 = máximo),
   pelo mesmo caminho das Configurações do Windows (Acessibilidade →
   Ponteiro do mouse): registro HKCU + SystemParametersInfo(SPI_SETCURSORS).

2. find(): "sacode" o ponteiro num espiral que cresce e volta ao ponto
   inicial. Serve para (a) achar o ponteiro na tela e (b) forçar o Windows
   a MOSTRAR o ponteiro — ele fica oculto quando a última entrada foi a
   tela de toque, o que é o caso típico do Ally.
"""

import ctypes
import math
import time
import winreg

import win_input

SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


def set_size(step: int) -> dict:
    step = max(1, min(15, int(step)))
    base = 32 + (step - 1) * 16  # mesma escala do slider das Configurações
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Microsoft\Accessibility") as k:
            winreg.SetValueEx(k, "CursorSize", 0, winreg.REG_DWORD, step)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Control Panel\Cursors") as k:
            winreg.SetValueEx(k, "CursorBaseSize", 0, winreg.REG_DWORD, base)
        ok = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETCURSORS, 0, None, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
        return {"ok": bool(ok), "size": step}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def find() -> dict:
    """Espiral relativa que termina onde começou (deslocamento líquido ~0)."""
    try:
        pts = [(0.0, 0.0)]
        steps = 36
        for i in range(1, steps + 1):
            a = i / steps * math.pi * 6          # 3 voltas
            r = math.sin(i / steps * math.pi) * 120  # cresce e volta a 0
            pts.append((math.cos(a) * r, math.sin(a) * r))
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            win_input.move(int(round(x1 - x0)), int(round(y1 - y0)))
            time.sleep(0.012)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
