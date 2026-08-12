"""
display.py — Brilho da tela e desligar/ligar o monitor do Ally (Windows).

Dois recursos pensados para economizar bateria SEM parar o jogo:

1. Brilho (0–100%): controla o painel interno do Ally via WMI
   (WmiMonitorBrightnessMethods). Colocar em 0 deixa a tela "apagada"
   (backlight no mínimo) mas o jogo continua rodando E a captura de tela
   para o espelhamento continua funcionando. É a melhor opção enquanto
   você joga pelo celular. Tocar na tela não "acorda" nada porque a tela
   nunca dormiu — só o brilho está no chão.

2. Desligar o monitor (SC_MONITORPOWER): apaga a tela de verdade (economia
   um pouco maior). Porém qualquer entrada de mouse/teclado religa a tela,
   e o espelhamento pode congelar enquanto ela está desligada — use isto
   quando NÃO estiver espelhando.
"""

import ctypes
import subprocess

HWND_BROADCAST = 0xFFFF
WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170

# CREATE_NO_WINDOW: não pisca janela de console ao chamar powershell.
_NO_WINDOW = 0x08000000


def monitor_off() -> dict:
    try:
        ctypes.windll.user32.SendMessageW(
            HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)
        return {"ok": True, "action": "monitor_off"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def monitor_on() -> dict:
    try:
        # "Acorda" o monitor mexendo 1px pra lá e pra cá (não muda a posição).
        from virtual_input import win_input
        win_input.move(1, 0)
        win_input.move(-1, 0)
        return {"ok": True, "action": "monitor_on"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _ps(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True, creationflags=_NO_WINDOW,
    )


def set_brightness(pct: int) -> dict:
    pct = max(0, min(100, int(pct)))
    try:
        r = _ps(
            "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
            f".WmiSetBrightness(1,{pct})"
        )
        if r.returncode != 0:
            return {"ok": False, "brightness": pct,
                    "error": (r.stderr or "WMI de brilho indisponível").strip()}
        return {"ok": True, "brightness": pct}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_brightness() -> int | None:
    try:
        r = _ps(
            "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness)"
            ".CurrentBrightness"
        )
        if r.returncode == 0 and r.stdout.strip().isdigit():
            return int(r.stdout.strip())
    except Exception:
        pass
    return None
