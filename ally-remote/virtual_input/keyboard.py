"""Teclado virtual do Ally Remote.

Centraliza teclas simples, caracteres e atalhos. A interface web expõe
F1-F12, navegação, mídia, atalhos do Windows e teclas de jogo; todos eles
precisam ter um caminho real de injeção aqui.

O pynput no Windows usa a API nativa de entrada. Mantemos um único Controller
no backend e oferecemos duas operações:
- press_key(): toque curto / atalho completo;
- set_key(): key down / key up, usado pelo modo jogo para permitir segurar
  WASD, Shift, Ctrl, Space etc.
"""

from pynput.keyboard import Controller, Key


SPECIAL_KEYS = {
    "enter": Key.enter,
    "backspace": Key.backspace,
    "esc": Key.esc,
    "escape": Key.esc,
    "tab": Key.tab,
    "space": Key.space,
    "win": Key.cmd,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "delete": Key.delete,
    "home": Key.home,
    "end": Key.end,
    "pageup": Key.page_up,
    "pagedown": Key.page_down,
    "insert": Key.insert,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "alt": Key.alt,
    "capslock": Key.caps_lock,
    "numlock": Key.num_lock,
    "scrolllock": Key.scroll_lock,
    "printscreen": Key.print_screen,
    "f1": Key.f1,
    "f2": Key.f2,
    "f3": Key.f3,
    "f4": Key.f4,
    "f5": Key.f5,
    "f6": Key.f6,
    "f7": Key.f7,
    "f8": Key.f8,
    "f9": Key.f9,
    "f10": Key.f10,
    "f11": Key.f11,
    "f12": Key.f12,
    "volup": Key.media_volume_up,
    "voldown": Key.media_volume_down,
    "mute": Key.media_volume_mute,
    "play": Key.media_play_pause,
    "next": Key.media_next,
    "prev": Key.media_previous,
}


COMBOS = {
    "altf4": (Key.alt, Key.f4),
    "alt_tab": (Key.alt, Key.tab),
    "win_d": (Key.cmd, "d"),
    "win_e": (Key.cmd, "e"),
    "win_l": (Key.cmd, "l"),
    "win_r": (Key.cmd, "r"),
    "win_i": (Key.cmd, "i"),
    "win_tab": (Key.cmd, Key.tab),
    "win_shift_s": (Key.cmd, Key.shift, "s"),
    "win_prtsc": (Key.cmd, Key.print_screen),
    "win_x": (Key.cmd, "x"),
    "win_a": (Key.cmd, "a"),
    "ctrl_z": (Key.ctrl, "z"),
    "ctrl_c": (Key.ctrl, "c"),
    "ctrl_v": (Key.ctrl, "v"),
    "ctrl_x": (Key.ctrl, "x"),
    "ctrl_a": (Key.ctrl, "a"),
    "ctrl_s": (Key.ctrl, "s"),
    "ctrl_f": (Key.ctrl, "f"),
    "ctrl_p": (Key.ctrl, "p"),
    "ctrl_n": (Key.ctrl, "n"),
    "ctrl_t": (Key.ctrl, "t"),
    "ctrl_w": (Key.ctrl, "w"),
    "ctrl_r": (Key.ctrl, "r"),
    "ctrl_shift_t": (Key.ctrl, Key.shift, "t"),
    "alt_left": (Key.alt, Key.left),
    "alt_right": (Key.alt, Key.right),
    "ctrl_shift_esc": (Key.ctrl, Key.shift, Key.esc),
    "taskmanager": (Key.ctrl, Key.shift, Key.esc),
    # O Windows pode bloquear a Secure Attention Sequence em processos comuns,
    # mas manter o combo aqui evita um botão morto e preserva o protocolo.
    "ctrl_alt_del": (Key.ctrl, Key.alt, Key.delete),
}


def type_text(kb: Controller, s: str) -> None:
    """Digita texto Unicode no aplicativo que estiver com foco."""
    if s:
        kb.type(str(s))


def _resolve_key(k: str):
    name = str(k)
    low = name.lower()
    special = SPECIAL_KEYS.get(low)
    if special is not None:
        return special
    # Letras, números e símbolos enviados pelos botões da interface.
    if len(name) == 1:
        return name
    return None


def _tap_combo(kb: Controller, combo) -> None:
    pressed = []
    try:
        for key in combo:
            kb.press(key)
            pressed.append(key)
    finally:
        for key in reversed(pressed):
            try:
                kb.release(key)
            except Exception:
                pass


def press_key(kb: Controller, k: str) -> bool:
    """Pressiona e solta uma tecla/atalho. Retorna False se não for conhecida."""
    name = str(k)
    combo = COMBOS.get(name.lower())
    if combo is not None:
        _tap_combo(kb, combo)
        return True

    key = _resolve_key(name)
    if key is None:
        return False
    kb.press(key)
    kb.release(key)
    return True


def set_key(kb: Controller, k: str, pressed: bool) -> bool:
    """Mantém uma tecla pressionada ou a solta (modo jogo / multi-touch)."""
    key = _resolve_key(str(k))
    if key is None:
        return False
    if pressed:
        kb.press(key)
    else:
        kb.release(key)
    return True
