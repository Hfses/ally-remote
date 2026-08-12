"""Teclado virtual (pynput) — extraído do antigo server.py (FASE 1).

Centraliza o Controller e o mapa SPECIAL_KEYS para que o backend real não
duplique a lógica de teclas especiais (ALT+F4, mídia, volume...).
Somente importado no Windows (pynput é dependência com marker win32).
"""

from pynput.keyboard import Controller, Key

SPECIAL_KEYS = {
    "enter": Key.enter, "backspace": Key.backspace, "esc": Key.esc,
    "tab": Key.tab, "space": Key.space, "win": Key.cmd,
    "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
    "delete": Key.delete,
    "volup": Key.media_volume_up, "voldown": Key.media_volume_down,
    "mute": Key.media_volume_mute, "play": Key.media_play_pause,
    "next": Key.media_next, "prev": Key.media_previous,
    "altf4": None,  # tratado à parte
}


def type_text(kb: Controller, s: str) -> None:
    kb.type(s)


def press_key(kb: Controller, k: str) -> None:
    if k == "altf4":
        with kb.pressed(Key.alt):
            kb.press(Key.f4)
            kb.release(Key.f4)
        return
    key = SPECIAL_KEYS.get(k)
    if key:
        kb.press(key)
        kb.release(key)
