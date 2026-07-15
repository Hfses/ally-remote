"""
stats.py — Métricas ao vivo do Ally (uso de CPU e temperatura).

- cpu_percent(): uso de CPU pela diferença de GetSystemTimes entre chamadas
  (idle/kernel/user), sem dependências externas.
- cpu_temp_c(): temperatura via WMI MSAcpi_ThermalZoneTemperature (em
  décimos de Kelvin). Nem todo firmware expõe; se não houver, devolve None.

Observação honesta sobre FPS: medir o FPS real de dentro de um jogo exige um
"hook" no jogo (RTSS/PresentMon/Armoury Crate). Não dá para obter isso só com
WMI, então o painel mostra o que é confiável (CPU, temperatura, RAM, fan,
bateria). O FPS aparece como "—" a menos que uma ferramenta dessas esteja
ativa.
"""

import ctypes
import platform
import subprocess
from ctypes import wintypes

IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000

_prev = {"idle": 0, "total": 0}


class _FILETIME(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]


def _u64(ft: _FILETIME) -> int:
    return (ft.high << 32) | ft.low


def cpu_percent() -> float | None:
    if not IS_WINDOWS:
        return None
    idle, kern, user = _FILETIME(), _FILETIME(), _FILETIME()
    if not ctypes.windll.kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
        return None
    i, k, u = _u64(idle), _u64(kern), _u64(user)
    total = k + u  # kernel já inclui o idle
    di = i - _prev["idle"]
    dt = total - _prev["total"]
    _prev["idle"], _prev["total"] = i, total
    if dt <= 0:
        return None
    return round(max(0.0, min(100.0, (1.0 - di / dt) * 100.0)), 1)


def cpu_temp_c() -> float | None:
    if not IS_WINDOWS:
        return None
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi "
             "-EA SilentlyContinue | Select-Object -First 1).CurrentTemperature"],
            capture_output=True, text=True, creationflags=_NO_WINDOW,
        )
        s = r.stdout.strip()
        if s.isdigit():
            c = int(s) / 10.0 - 273.15
            if 0 < c < 120:
                return round(c, 1)
    except Exception:
        pass
    return None
