"""
server.py — Ally Remote: controle o ROG Ally pelo celular (rede local).

Rode NO ALLY, como Administrador (o AllyRemote.exe já pede sozinho):
    AllyRemote.exe            (ou: python server.py)
No celular, abra o endereço mostrado no console:  http://<IP-do-Ally>:8765

Segurança (leia!): por padrão NÃO há autenticação — qualquer pessoa na sua
rede Wi-Fi pode mover o mouse, digitar e trocar modo de desempenho do Ally.
Em rede doméstica sua isso costuma ser aceitável, mas se quiser uma trava
mínima, rode com um PIN:
    AllyRemote.exe --pin 4321
O tráfego continua sem criptografia (HTTP puro) — não use fora da sua rede.
"""

import argparse
import asyncio
import ctypes
import json
import platform
import socket
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

try:
    import qrcode  # opcional: QR code no console para abrir no celular
except Exception:
    qrcode = None

# Quando empacotado pelo PyInstaller, os arquivos estáticos ficam em _MEIPASS.
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
IS_WINDOWS = platform.system() == "Windows"

app = FastAPI(title="Ally Remote")
PIN: str | None = None

# ---------------------------------------------------------------------------
# Backend real (Windows) ou mock (para desenvolvimento fora do Ally)
# ---------------------------------------------------------------------------

if IS_WINDOWS:
    from pynput.keyboard import Controller as KeyboardController
    from pynput.keyboard import Key

    import ally_led
    import cursor
    import display
    import games
    import power
    import ram
    import screen
    import stats
    import win_input

    # Sem isso o Windows "virtualiza" as coordenadas do cursor por causa da
    # escala de DPI do Ally, e movimentos pequenos podem ser engolidos.
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

    keyboard = KeyboardController()

    try:
        from ally_acpi import AllyACPI

        acpi = AllyACPI()
        acpi_error = None
    except Exception as e:  # driver ausente / sem admin
        acpi = None
        acpi_error = str(e)

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

    def do_move(dx, dy):
        win_input.move(dx, dy)

    def do_move_abs(nx, ny):
        win_input.move_abs(float(nx), float(ny))

    def do_click(btn, double=False):
        win_input.click(btn, double)

    def do_scroll(dy):
        win_input.scroll(dy)

    def do_drag(on):
        if on:
            win_input.press("left")
        else:
            win_input.release("left")

    def do_text(s):
        keyboard.type(s)

    def do_key(k):
        if k == "altf4":
            with keyboard.pressed(Key.alt):
                keyboard.press(Key.f4)
                keyboard.release(Key.f4)
            return
        key = SPECIAL_KEYS.get(k)
        if key:
            keyboard.press(key)
            keyboard.release(key)

    def do_ram():
        return ram.free_ram()

    def do_perf(mode):
        if not acpi:
            return {"ok": False, "error": f"ATKACPI indisponível: {acpi_error}"}
        r = acpi.set_performance_mode(int(mode))
        return {"ok": True, **r}

    def do_led(r, g, b, mode=0, speed=0xE1):
        return ally_led.set_color(r, g, b, mode=int(mode), speed=int(speed))

    def do_power(action):
        return power.do_power(action)

    def do_pointer(action, value=4):
        if action == "find":
            return {"action": "find", **cursor.find()}
        if action == "size":
            return {"action": "size", **cursor.set_size(value)}
        return {"ok": False, "error": "ação desconhecida"}

    def do_brightness(value):
        return display.set_brightness(int(value))

    def do_monitor(action):
        if action == "off":
            return display.monitor_off()
        if action == "on":
            return display.monitor_on()
        return {"ok": False, "error": "ação desconhecida"}

    def do_fan(action, value=100):
        # "auto" reaplica o modo atual (volta a fan ao controle do firmware)
        if action == "auto":
            if acpi:
                try:
                    cur = acpi.get_performance_mode().get("mode", 0)
                    acpi.set_performance_mode(cur if cur in (0, 1, 2) else 0)
                except Exception:
                    pass
            return {"ok": True, "action": "auto"}
        if action == "max":
            if acpi:
                acpi.set_performance_mode(1)  # Turbo = refrigeração máxima (confiável)
            return {"ok": True, "action": "max"}
        if action == "custom":
            if not acpi:
                return {"ok": False, "error": "ACPI indisponível"}
            return acpi.set_fan_curve(int(value))
        return {"ok": False, "error": "ação desconhecida"}

    def do_games():
        return {"ok": True, "games": games.list_games()}

    def do_launch(gid):
        return games.launch_game(str(gid))

    def do_stats():
        cpu = stats.cpu_percent()
        temp = stats.cpu_temp_c()
        mem = ram.memory_status()
        bat = power.battery_status()
        fan = None
        if acpi:
            try:
                fan = acpi.get_fan_rpm().get("rpm")
            except Exception:
                fan = None
        return {"cpu_pct": cpu, "cpu_temp_c": temp, "fan_rpm": fan,
                "mem_load": mem.get("load_pct"), "mem_avail_mb": mem.get("avail_mb"),
                "battery": bat}

    def do_status():
        st = {"platform": "windows", "acpi": acpi is not None,
              "screen": screen.available()}
        st["memory"] = ram.memory_status()
        st["battery"] = power.battery_status()
        st["brightness"] = display.get_brightness()
        if acpi:
            try:
                st["perf"] = acpi.get_performance_mode()
                st["fan"] = acpi.get_fan_rpm()
            except Exception as e:
                st["acpi_error"] = str(e)
        else:
            st["acpi_error"] = acpi_error
        return st

    def is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def ensure_firewall(port: int):
        """Cria a regra de firewall (uma vez) para o celular conseguir conectar."""
        rule = "Ally Remote"
        try:
            q = subprocess.run(
                ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule}"],
                capture_output=True,
            )
            if q.returncode == 0:
                return  # regra já existe
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={rule}", "dir=in", "action=allow", "protocol=TCP",
                 f"localport={port}", "profile=private,domain"],
                capture_output=True,
            )
            print(f">>> Regra de firewall '{rule}' criada (porta {port}/TCP, rede privada).")
        except Exception as e:
            print(f">>> Não consegui configurar o firewall automaticamente: {e}")
            print(f">>> Libere manualmente a porta {port}/TCP em redes privadas.")

else:
    # -------- MOCK: permite testar o servidor e a interface fora do Ally ----
    _mock_perf = {"mode": 0, "label": "Performance (Balanced)"}

    import screen  # o mock de captura funciona fora do Windows (quadro de teste)

    def do_move(dx, dy): print(f"[mock] move {dx},{dy}")
    def do_move_abs(nx, ny): print(f"[mock] move_abs {nx:.3f},{ny:.3f}")
    def do_click(btn, double=False): print(f"[mock] click {btn} double={double}")
    def do_scroll(dy): print(f"[mock] scroll {dy}")
    def do_drag(on): print(f"[mock] drag {'on' if on else 'off'}")
    def do_text(s): print(f"[mock] type {s!r}")
    def do_key(k): print(f"[mock] key {k}")

    def do_ram():
        return {"before_avail_mb": 4200, "after_avail_mb": 6900, "freed_mb": 2700,
                "processes_trimmed": 87, "standby_purged": True,
                "total_mb": 16384, "load_pct": 58}

    def do_perf(mode):
        labels = {0: "Performance (Balanced)", 1: "Turbo", 2: "Silent"}
        _mock_perf.update(mode=int(mode), label=labels[int(mode)])
        return {"ok": True, **_mock_perf, "firmware_status": 1}

    def do_led(r, g, b, mode=0, speed=0xE1):
        return {"ok": True, "device": "mock", "rgb": [r, g, b],
                "mode": mode, "speed": speed}

    def do_power(action):
        print(f"[mock] power {action}")
        return {"ok": True, "action": action}

    def do_pointer(action, value=4):
        print(f"[mock] pointer {action} {value}")
        return {"ok": True, "action": action, "size": value}

    _mock_bri = {"v": 70}

    def do_brightness(value):
        _mock_bri["v"] = max(0, min(100, int(value)))
        print(f"[mock] brightness {_mock_bri['v']}")
        return {"ok": True, "brightness": _mock_bri["v"]}

    def do_monitor(action):
        print(f"[mock] monitor {action}")
        return {"ok": True, "action": action}

    def do_fan(action, value=100):
        print(f"[mock] fan {action} {value}")
        return {"ok": True, "action": action, "percent": value}

    def do_games():
        return {"ok": True, "games": [
            {"id": "steam:1091500", "name": "Cyberpunk 2077", "source": "Steam"},
            {"id": "steam:1245620", "name": "Elden Ring", "source": "Steam"},
            {"id": "steam:271590", "name": "GTA V", "source": "Steam"},
            {"id": "lnk:C:/atalho.lnk", "name": "RetroArch", "source": "Atalho"},
        ]}

    def do_launch(gid):
        print(f"[mock] launch {gid}")
        return {"ok": True}

    _mock_cpu = {"v": 34.0}

    def do_stats():
        _mock_cpu["v"] = (_mock_cpu["v"] + 7) % 90 + 5
        return {"cpu_pct": round(_mock_cpu["v"], 1), "cpu_temp_c": 62.0,
                "fan_rpm": 3100, "mem_load": 62, "mem_avail_mb": 6100,
                "battery": {"percent": 76, "charging": False}}

    def do_status():
        return {"platform": "mock", "acpi": True, "perf": dict(_mock_perf),
                "fan": {"raw": 31, "rpm": 3100}, "screen": screen.available(),
                "memory": {"total_mb": 16384, "avail_mb": 6100, "load_pct": 62},
                "battery": {"percent": 76, "charging": False},
                "brightness": _mock_bri["v"]}

    def is_admin() -> bool:
        return True

    def ensure_firewall(port: int):
        pass


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    authed = PIN is None
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            t = msg.get("t")

            if not authed:
                if t == "auth" and str(msg.get("pin")) == PIN:
                    authed = True
                    await ws.send_json({"t": "auth", "ok": True})
                else:
                    await ws.send_json({"t": "auth", "ok": False})
                continue

            # Comandos de alta frequência: sem resposta (latência mínima)
            if t == "move":
                do_move(int(msg["dx"]), int(msg["dy"]))
            elif t == "moveabs":
                do_move_abs(msg.get("x", 0), msg.get("y", 0))
            elif t == "scroll":
                do_scroll(int(msg["dy"]))
            elif t == "click":
                do_click(msg.get("btn", "left"), bool(msg.get("double")))
            elif t == "drag":
                do_drag(bool(msg.get("on")))
            elif t == "text":
                do_text(str(msg.get("s", "")))
            elif t == "key":
                do_key(str(msg.get("k", "")))

            # Comandos com resposta (roda em thread p/ não travar o loop)
            elif t == "ram":
                r = await asyncio.to_thread(do_ram)
                await ws.send_json({"t": "ram", **r})
            elif t == "perf":
                r = await asyncio.to_thread(do_perf, msg.get("mode", 0))
                await ws.send_json({"t": "perf", **r})
            elif t == "led":
                r = await asyncio.to_thread(
                    do_led,
                    msg.get("r", 255), msg.get("g", 255), msg.get("b", 255),
                    msg.get("mode", 0), msg.get("speed", 0xE1),
                )
                await ws.send_json({"t": "led", **r})
            elif t == "power":
                r = await asyncio.to_thread(do_power, str(msg.get("action", "")))
                await ws.send_json({"t": "power", **r})
            elif t == "pointer":
                r = await asyncio.to_thread(
                    do_pointer, str(msg.get("action", "")), int(msg.get("value", 4)))
                await ws.send_json({"t": "pointer", **r})
            elif t == "brightness":
                r = await asyncio.to_thread(do_brightness, msg.get("value", 50))
                await ws.send_json({"t": "brightness", **r})
            elif t == "monitor":
                r = await asyncio.to_thread(do_monitor, str(msg.get("action", "")))
                await ws.send_json({"t": "monitor", **r})
            elif t == "fan":
                r = await asyncio.to_thread(
                    do_fan, str(msg.get("action", "")), int(msg.get("value", 100)))
                await ws.send_json({"t": "fan", **r})
            elif t == "games":
                r = await asyncio.to_thread(do_games)
                await ws.send_json({"t": "games", **r})
            elif t == "launch":
                r = await asyncio.to_thread(do_launch, msg.get("id", ""))
                await ws.send_json({"t": "launch", **r})
            elif t == "stats":
                r = await asyncio.to_thread(do_stats)
                await ws.send_json({"t": "stats", **r})
            elif t == "status":
                r = await asyncio.to_thread(do_status)
                await ws.send_json({"t": "status", **r})
            elif t == "ping":
                await ws.send_json({"t": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"t": "error", "error": str(e)})
        except Exception:
            pass


@app.websocket("/stream")
async def stream_endpoint(ws: WebSocket):
    """Espelhamento da tela: envia quadros JPEG (binário) num ritmo alvo.

    Parâmetros pela query: w (largura máx), q (qualidade JPEG 1–95),
    fps (quadros/s alvo) e pin (se o servidor exigir PIN).
    """
    await ws.accept()
    q = ws.query_params
    if PIN is not None and str(q.get("pin")) != PIN:
        await ws.close(code=4001)
        return
    if not screen.available():
        try:
            await ws.send_json({"error": "captura de tela indisponível (instale mss/Pillow)"})
        except Exception:
            pass
        await ws.close()
        return

    max_w = max(320, min(1920, int(q.get("w", 1024))))
    quality = max(10, min(95, int(q.get("q", 45))))
    fps = max(1, min(30, int(q.get("fps", 15))))
    interval = 1.0 / fps

    try:
        while True:
            t0 = asyncio.get_event_loop().time()
            jpeg, _, _ = await asyncio.to_thread(screen.capture_jpeg, max_w, quality)
            await ws.send_bytes(jpeg)
            dt = asyncio.get_event_loop().time() - t0
            if dt < interval:
                await asyncio.sleep(interval - dt)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception:
        try:
            await ws.close()
        except Exception:
            pass


@app.get("/")
async def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/needs-pin")
async def needs_pin():
    return {"pin": PIN is not None}


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


def local_ip() -> str:
    """Descobre o IP local (o que o celular deve usar)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "IP-do-Ally"


def main():
    global PIN
    p = argparse.ArgumentParser(description="Ally Remote — servidor local")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--pin", default=None, help="PIN opcional exigido do celular")
    p.add_argument("--no-firewall", action="store_true",
                   help="não criar regra de firewall automaticamente")
    args = p.parse_args()
    PIN = args.pin

    print()
    print("  ============================================")
    print("   ALLY REMOTE — controle o Ally pelo celular")
    print("  ============================================")
    print()

    if not IS_WINDOWS:
        print(">>> Rodando em MODO MOCK (fora do Windows): nada é executado de verdade.")
    elif not is_admin():
        print(">>> AVISO: sem privilégios de Administrador.")
        print(">>> RAM e modo de desempenho NÃO vão funcionar. Feche e rode como admin.")
    elif not args.no_firewall:
        ensure_firewall(args.port)

    if PIN is None:
        print(">>> SEM PIN: qualquer dispositivo na sua rede pode controlar este PC.")
        print(">>> Para exigir um PIN: AllyRemote.exe --pin 4321")

    url = f"http://{local_ip()}:{args.port}"
    print()
    print(f">>> No celular (mesmo Wi-Fi), abra:  {url}")
    if qrcode:
        try:
            qr = qrcode.QRCode(border=1)
            qr.add_data(url)
            qr.print_ascii(invert=True)
        except Exception:
            pass
    print(">>> Deixe esta janela aberta enquanto usa o app. CTRL+C para sair.")
    print()

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
