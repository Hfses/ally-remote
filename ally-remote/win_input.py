"""
win_input.py — Injeção de mouse via SendInput (ctypes), movimento RELATIVO.

Por que não usar pynput para mover: o pynput move o cursor lendo a posição
atual (GetCursorPos) e gravando uma posição absoluta (SetCursorPos). Com a
escala de DPI do Windows no Ally (150%/200%) e em apps/jogos que capturam o
mouse, isso pode simplesmente não mexer o cursor — os cliques funcionam mas
o movimento não. SendInput com MOUSEEVENTF_MOVE injeta o deslocamento
relativo direto na fila de entrada do Windows, igual a um mouse físico.
"""

import ctypes
from ctypes import wintypes

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def _send(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> bool:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi = MOUSEINPUT(int(dx), int(dy), data & 0xFFFFFFFF, flags, 0, 0)
    return ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1


def move(dx: int, dy: int):
    _send(MOUSEEVENTF_MOVE, dx, dy)


def move_abs(nx: float, ny: float):
    """Move o cursor para uma posição ABSOLUTA na tela principal.

    nx/ny são normalizados 0.0–1.0 (0,0 = topo-esquerda, 1,1 = base-direita).
    Usado ao tocar na tela espelhada: o cursor vai exatamente para o ponto
    tocado. A API usa a escala 0–65535 do monitor principal.
    """
    x = max(0, min(65535, int(nx * 65535)))
    y = max(0, min(65535, int(ny * 65535)))
    _send(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, x, y)


def press(btn: str = "left"):
    _send(MOUSEEVENTF_RIGHTDOWN if btn == "right" else MOUSEEVENTF_LEFTDOWN)


def release(btn: str = "left"):
    _send(MOUSEEVENTF_RIGHTUP if btn == "right" else MOUSEEVENTF_LEFTUP)


def click(btn: str = "left", double: bool = False):
    for _ in range(2 if double else 1):
        press(btn)
        release(btn)


def scroll(dy: int):
    _send(MOUSEEVENTF_WHEEL, data=int(dy) * WHEEL_DELTA)
