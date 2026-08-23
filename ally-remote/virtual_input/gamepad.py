"""
Gamepad virtual — usa vgamepad (ViGEmBus) quando disponível.
Fallback: emula com teclado (WASD + setas).
"""

import platform
import threading

IS_WINDOWS = platform.system() == "Windows"

# ── tenta carregar vgamepad ──────────────────────────────────────────────────
try:
    import vgamepad as vg
    _VIGEM = True
except Exception:
    _VIGEM = False

# ── mapeamento de botões Xbox → vgamepad ─────────────────────────────────────
if _VIGEM:
    _BTN_MAP = {
        "a":      vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
        "b":      vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
        "x":      vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
        "y":      vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
        "lb":     vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
        "rb":     vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
        "start":  vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
        "back":   vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
        "l3":     vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
        "r3":     vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        "dup":    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
        "ddown":  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
        "dleft":  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
        "dright": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        "guide":  vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    }

# ── fallback de teclado ───────────────────────────────────────────────────────
_KB_FALLBACK = {
    "a": "x", "b": "c", "x": "z", "y": "v",
    "lb": "q", "rb": "e", "start": "return", "back": "escape",
    "dup": "up", "ddown": "down", "dleft": "left", "dright": "right",
    "lt": None, "rt": None,
}


class GamepadController:
    """Controla um gamepad virtual Xbox 360 ou emula via teclado."""

    def __init__(self):
        self._pad = None
        self._lock = threading.Lock()
        self._kb = None
        self._pressed = set()

        if _VIGEM and IS_WINDOWS:
            try:
                self._pad = vg.VX360Gamepad()
                self._pad.reset()
                self._pad.update()
            except Exception:
                self._pad = None

        if self._pad is None:
            # fallback teclado
            try:
                from pynput.keyboard import Controller
                self._kb = Controller()
            except Exception:
                pass

    @property
    def available(self) -> bool:
        return self._pad is not None or self._kb is not None

    @property
    def mode(self) -> str:
        if self._pad:
            return "vigem"
        if self._kb:
            return "keyboard"
        return "none"

    # ── botões ────────────────────────────────────────────────────────────────

    def button(self, name: str, pressed: bool):
        name = name.lower()
        with self._lock:
            if self._pad:
                btn = _BTN_MAP.get(name)
                if btn is None:
                    return
                if pressed:
                    self._pad.press_button(btn)
                else:
                    self._pad.release_button(btn)
                self._pad.update()
            elif self._kb:
                key = _KB_FALLBACK.get(name)
                if not key:
                    return
                from pynput.keyboard import Key, KeyCode
                _KEY = {
                    "return": Key.enter, "escape": Key.esc,
                    "up": Key.up, "down": Key.down,
                    "left": Key.left, "right": Key.right,
                }
                k = _KEY.get(key, KeyCode.from_char(key))
                if pressed:
                    self._kb.press(k)
                    self._pressed.add(name)
                else:
                    self._kb.release(k)
                    self._pressed.discard(name)

    # ── analógicos ────────────────────────────────────────────────────────────

    def left_stick(self, x: float, y: float):
        """x, y em [-1.0, 1.0]"""
        with self._lock:
            if self._pad:
                ix = int(max(-1, min(1, x)) * 32767)
                iy = int(max(-1, min(1, y)) * 32767)
                self._pad.left_joystick(ix, iy)
                self._pad.update()
            elif self._kb:
                self._stick_kb("ls", x, y)

    def right_stick(self, x: float, y: float):
        """x, y em [-1.0, 1.0]"""
        with self._lock:
            if self._pad:
                ix = int(max(-1, min(1, x)) * 32767)
                iy = int(max(-1, min(1, y)) * 32767)
                self._pad.right_joystick(ix, iy)
                self._pad.update()
            elif self._kb:
                self._stick_kb("rs", x, y)

    def _stick_kb(self, stick: str, x: float, y: float):
        """Emula stick analógico com teclas WASD ou setas."""
        from pynput.keyboard import Key, KeyCode
        keys = {
            "ls": {"up": KeyCode.from_char("w"), "down": KeyCode.from_char("s"),
                   "left": KeyCode.from_char("a"), "right": KeyCode.from_char("d")},
            "rs": {"up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right},
        }
        mapping = keys.get(stick, {})
        DEAD = 0.25
        dirs = {
            "up":    y > DEAD,
            "down":  y < -DEAD,
            "left":  x < -DEAD,
            "right": x > DEAD,
        }
        for d, active in dirs.items():
            k = mapping.get(d)
            if not k:
                continue
            tag = f"{stick}_{d}"
            if active and tag not in self._pressed:
                self._kb.press(k)
                self._pressed.add(tag)
            elif not active and tag in self._pressed:
                self._kb.release(k)
                self._pressed.discard(tag)

    # ── gatilhos ──────────────────────────────────────────────────────────────

    def trigger(self, side: str, value: float):
        """side: 'lt'|'rt', value: [0.0, 1.0]"""
        with self._lock:
            if self._pad:
                v = int(max(0, min(1, value)) * 255)
                if side == "lt":
                    self._pad.left_trigger(v)
                else:
                    self._pad.right_trigger(v)
                self._pad.update()

    # ── reset ─────────────────────────────────────────────────────────────────

    def reset(self):
        with self._lock:
            if self._pad:
                self._pad.reset()
                self._pad.update()
            if self._kb:
                from pynput.keyboard import Key, KeyCode
                for tag in list(self._pressed):
                    # libera tudo que ficou pressionado
                    try:
                        part = tag.split("_")[-1]
                        _KEYS = {"up": Key.up, "down": Key.down,
                                 "left": Key.left, "right": Key.right}
                        k = _KEYS.get(part, KeyCode.from_char(part))
                        self._kb.release(k)
                    except Exception:
                        pass
                self._pressed.clear()


# Singleton global
_gamepad: GamepadController | None = None
_gp_lock = threading.Lock()


def get_gamepad() -> GamepadController:
    global _gamepad
    with _gp_lock:
        if _gamepad is None:
            _gamepad = GamepadController()
    return _gamepad
