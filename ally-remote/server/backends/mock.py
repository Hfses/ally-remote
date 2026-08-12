"""Backend MOCK (fora do Windows — desenvolvimento e testes) — FASE 1.

Reimplementa exatamente o bloco mock do antigo server.py: nada é executado
de verdade, os comandos são impressos no console e as respostas imitam o
comportamento esperado. É o alvo da suíte de testes (pytest) e do CI.
"""

from server import __version__

from .base import Backend


class MockBackend(Backend):
    platform = "mock"

    def __init__(self):
        self._perf = {"mode": 0, "label": "Performance (Balanced)"}
        self._bri = {"v": 70}
        self._cpu = {"v": 34.0}
        self._caps: dict | None = None

    # ---- Entrada (sem resposta) ----

    def move(self, dx, dy):
        print(f"[mock] move {dx},{dy}")

    def move_abs(self, x, y):
        print(f"[mock] move_abs {float(x):.3f},{float(y):.3f}")

    def click(self, btn="left", double=False):
        print(f"[mock] click {btn} double={double}")

    def scroll(self, dy):
        print(f"[mock] scroll {dy}")

    def drag(self, on):
        print(f"[mock] drag {'on' if on else 'off'}")

    def text(self, s):
        print(f"[mock] type {s!r}")

    def key(self, k):
        print(f"[mock] key {k}")

    # ---- Ações (com resposta) ----

    def ram(self):
        return {"before_avail_mb": 4200, "after_avail_mb": 6900, "freed_mb": 2700,
                "processes_trimmed": 87, "standby_purged": True,
                "total_mb": 16384, "load_pct": 58}

    def perf(self, mode):
        labels = {0: "Performance (Balanced)", 1: "Turbo", 2: "Silent"}
        self._perf.update(mode=int(mode), label=labels[int(mode)])
        return {"ok": True, **self._perf, "firmware_status": 1}

    def led(self, r, g, b, mode=0, speed=0xE1):
        return {"ok": True, "device": "mock", "rgb": [r, g, b],
                "mode": mode, "speed": speed}

    def power(self, action):
        print(f"[mock] power {action}")
        return {"ok": True, "action": action}

    def pointer(self, action, value=4):
        print(f"[mock] pointer {action} {value}")
        return {"ok": True, "action": action, "size": value}

    def brightness(self, value):
        self._bri["v"] = max(0, min(100, int(value)))
        print(f"[mock] brightness {self._bri['v']}")
        return {"ok": True, "brightness": self._bri["v"]}

    def monitor(self, action):
        print(f"[mock] monitor {action}")
        return {"ok": True, "action": action}

    def fan(self, action, value=100):
        print(f"[mock] fan {action} {value}")
        return {"ok": True, "action": action, "percent": value}

    def games(self):
        return {"ok": True, "games": [
            {"id": "steam:1091500", "name": "Cyberpunk 2077", "source": "Steam"},
            {"id": "steam:1245620", "name": "Elden Ring", "source": "Steam"},
            {"id": "steam:271590", "name": "GTA V", "source": "Steam"},
            {"id": "lnk:C:/atalho.lnk", "name": "RetroArch", "source": "Atalho"},
        ]}

    def launch(self, gid):
        print(f"[mock] launch {gid}")
        return {"ok": True}

    def status(self):
        st = {"platform": "mock", "acpi": True, "perf": dict(self._perf),
              "fan": {"raw": 31, "rpm": 3100}, "screen": self._screen_available(),
              "memory": {"total_mb": 16384, "avail_mb": 6100, "load_pct": 62},
              "battery": {"percent": 76, "charging": False},
              "brightness": self._bri["v"]}
        st["capabilities"] = self.capabilities()
        return st

    # ---- FASE 1 ----

    def sample_metrics(self):
        # Animação simples (mesma do mock antigo) para a telemetria "mexer".
        self._cpu["v"] = (self._cpu["v"] + 7) % 90 + 5
        return {"cpu_pct": round(self._cpu["v"], 1), "cpu_temp_c": 62.0,
                "fan_rpm": 3100, "mem_load": 62, "mem_avail_mb": 6100,
                "battery": {"percent": 76, "charging": False}}

    def capabilities(self):
        if self._caps is None:
            self._caps = {
                "platform": "mock",
                "model": "Mock (não é um Ally real)",
                "version": __version__,
                "acpi": True,
                "tdp": False,               # regra 15: sem implementação falsa
                "hdr": False,
                "vrr": False,
                "virtual_display": False,
                "gamepad": False,
                "led": True,
                "mirror": self._screen_available(),  # quadro de teste funciona
                "h264": False,
                "telemetry": True,
                "discovery_udp": True,
            }
        return dict(self._caps)

    @staticmethod
    def _screen_available():
        from hardware import screen
        return screen.available()
