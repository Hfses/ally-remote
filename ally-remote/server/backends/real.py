"""Backend REAL (Windows — roda no ROG Ally) — FASE 1.

Reimplementa exatamente o bloco Windows do antigo server.py, agora atrás da
interface Backend. Nenhum comando mudou de nome ou de resposta; as chamadas
de hardware (ATKACPI, HID, SendInput, WMI) continuam nos mesmos módulos,
apenas movidos para hardware/ | system/ | virtual_input/.
"""

import ctypes
import platform
import subprocess
import time

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    from pynput.keyboard import Controller as KeyboardController

    from hardware import ally_led, display, games, screen
    from hardware.ally_acpi import AllyACPI
    from system import power, ram
    from virtual_input import cursor, win_input
    from virtual_input.keyboard import press_key
else:
    KeyboardController = None
    ally_led = display = games = screen = None
    power = ram = None
    cursor = win_input = None
    press_key = None

from monitoring.collector import CpuTimes, cpu_temp_c
from server import __version__

from .base import Backend

_NO_WINDOW = 0x08000000


class RealBackend(Backend):
    platform = "windows"

    def __init__(self):
        if not IS_WINDOWS:
            raise RuntimeError(
                "RealBackend só roda no Windows (use MockBackend fora dele).")

        # Sem isso o Windows "virtualiza" as coordenadas do cursor por causa da
        # escala de DPI do Ally, e movimentos pequenos podem ser engolidos.
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        self._keyboard = KeyboardController()
        self._acpi, self._acpi_error = self._init_acpi()
        self._led_available = self._detect_led()
        self._cpu = CpuTimes()
        self._caps: dict | None = None
        self._bri_cache = (None, 0.0)

    # ------------------------------------------------------------------
    # Inicialização / detecção de hardware (regra 14: detectar, não assumir)
    # ------------------------------------------------------------------

    @staticmethod
    def _init_acpi():
        try:
            return AllyACPI(), None
        except Exception as e:  # driver ausente / sem admin
            return None, str(e)

    @staticmethod
    def _detect_led() -> bool:
        """Detecta o HID de iluminação do Ally (VID 0x0B05, PIDs conhecidos)."""
        try:
            return bool(ally_led.list_devices())
        except Exception:
            return False

    @staticmethod
    def _detect_model() -> str | None:
        """Modelo do hardware (ex.: "ROG Ally RC71L") via WMI, uma vez só."""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_ComputerSystem).Model"],
                capture_output=True, text=True, creationflags=_NO_WINDOW,
                timeout=5,
            )
            m = r.stdout.strip()
            return m or None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Entrada (sem resposta)
    # ------------------------------------------------------------------

    def move(self, dx, dy):
        win_input.move(dx, dy)

    def move_abs(self, x, y):
        win_input.move_abs(float(x), float(y))

    def click(self, btn="left", double=False):
        win_input.click(btn, double)

    def scroll(self, dy):
        win_input.scroll(dy)

    def drag(self, on):
        if on:
            win_input.press("left")
        else:
            win_input.release("left")

    def text(self, s):
        self._keyboard.type(s)

    def key(self, k):
        press_key(self._keyboard, k)

    # ------------------------------------------------------------------
    # Ações (com resposta)
    # ------------------------------------------------------------------

    def ram(self):
        return ram.free_ram()

    def perf(self, mode):
        if not self._acpi:
            return {"ok": False, "error": f"ATKACPI indisponível: {self._acpi_error}"}
        r = self._acpi.set_performance_mode(int(mode))
        return {"ok": True, **r}

    def led(self, r, g, b, mode=0, speed=0xE1):
        return ally_led.set_color(r, g, b, mode=int(mode), speed=int(speed))

    def power(self, action):
        return power.do_power(action)

    def pointer(self, action, value=4):
        if action == "find":
            return {"action": "find", **cursor.find()}
        if action == "size":
            return {"action": "size", **cursor.set_size(value)}
        return {"ok": False, "error": "ação desconhecida"}

    def brightness(self, value):
        return display.set_brightness(int(value))

    def monitor(self, action):
        if action == "off":
            return display.monitor_off()
        if action == "on":
            return display.monitor_on()
        return {"ok": False, "error": "ação desconhecida"}

    def fan(self, action, value=100):
        # "auto" reaplica o modo atual (volta a fan ao controle do firmware)
        if action == "auto":
            if self._acpi:
                try:
                    cur = self._acpi.get_performance_mode().get("mode", 0)
                    self._acpi.set_performance_mode(cur if cur in (0, 1, 2) else 0)
                except Exception:
                    pass
            return {"ok": True, "action": "auto"}
        if action == "max":
            if self._acpi:
                self._acpi.set_performance_mode(1)  # Turbo = refrigeração máxima
            return {"ok": True, "action": "max"}
        if action == "custom":
            if not self._acpi:
                return {"ok": False, "error": "ACPI indisponível"}
            return self._acpi.set_fan_curve(int(value))
        return {"ok": False, "error": "ação desconhecida"}

    def games(self):
        return {"ok": True, "games": games.list_games()}

    def launch(self, gid):
        return games.launch_game(str(gid))

    def status(self):
        st = {"platform": "windows", "acpi": self._acpi is not None,
              "screen": screen.available()}
        st["memory"] = ram.memory_status()
        st["battery"] = power.battery_status()
        st["brightness"] = self._brightness_cached()
        if self._acpi:
            try:
                st["perf"] = self._acpi.get_performance_mode()
                st["fan"] = self._acpi.get_fan_rpm()
            except Exception as e:
                st["acpi_error"] = str(e)
        else:
            st["acpi_error"] = self._acpi_error
        st["capabilities"] = self.capabilities()
        return st

    # ------------------------------------------------------------------
    # FASE 1: métricas, capabilities, caches
    # ------------------------------------------------------------------

    def sample_metrics(self):
        cpu = self._cpu.sample()
        temp = cpu_temp_c()  # cache TTL de 30 s (PowerShell caro)
        mem = ram.memory_status()
        bat = power.battery_status()
        fan = None
        if self._acpi:
            try:
                fan = self._acpi.get_fan_rpm().get("rpm")
            except Exception:
                fan = None
        return {"cpu_pct": cpu, "cpu_temp_c": temp, "fan_rpm": fan,
                "mem_load": mem.get("load_pct"), "mem_avail_mb": mem.get("avail_mb"),
                "battery": bat}

    def capabilities(self):
        if self._caps is None:
            self._caps = {
                "platform": "windows",
                "model": self._detect_model(),
                "version": __version__,
                "acpi": self._acpi is not None,
                "tdp": False,               # FASE 2: sem endpoint ATKACPI comprovado (regra 15)
                "hdr": False,               # FASE 2: só detecção/estado
                "vrr": False,               # FASE 2: só detecção/estado
                "virtual_display": False,   # FASE 5: driver IddCx (VirtualDrivers VDD)
                "gamepad": False,           # FASE 4: ViGEmBus (arquivado em 2023)
                "led": self._led_available,
                "mirror": screen.available(),
                "h264": False,              # FASE 3: encoder AMD VCN (h264_amf)
                "telemetry": True,
                "discovery_udp": True,
            }
        return dict(self._caps)

    def capabilities_cached(self):
        """Sem bloqueio: usado pelo discovery UDP, que roda no event loop."""
        if self._caps is not None:
            return dict(self._caps)
        return {"platform": "windows", "model": None, "version": __version__,
                "pending": True}

    def _brightness_cached(self):
        """Leitura de brilho via PowerShell com cache TTL de 2 s (status é
        pollado por todos os clientes a cada 8 s)."""
        now = time.monotonic()
        if self._bri_cache[0] is not None and now - self._bri_cache[1] < 2.0:
            return self._bri_cache[0]
        try:
            v = display.get_brightness()
        except Exception:
            v = None
        self._bri_cache = (v, now)
        return v
