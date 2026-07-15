"""
power.py — Bateria e ações de energia (Windows).

- battery_status(): GetSystemPowerStatus (kernel32) — % de bateria e se
  está carregando. No Ally isso reflete o mesmo valor do overlay do Windows.
- do_power(action): suspender / desligar / reiniciar / cancelar.
  Desligar e reiniciar usam `shutdown` com 5 s de tolerância, então o
  botão CANCELAR (shutdown /a) consegue abortar se foi engano.
"""

import ctypes
import subprocess
from ctypes import wintypes


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


def battery_status() -> dict:
    st = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):
        return {"percent": None, "charging": None}
    percent = None if st.BatteryLifePercent == 255 else int(st.BatteryLifePercent)
    charging = None if st.ACLineStatus == 255 else st.ACLineStatus == 1
    return {"percent": percent, "charging": charging}


def do_power(action: str) -> dict:
    try:
        if action == "sleep":
            # SetSuspendState(hibernate=0, force=1, wakeupEventsDisabled=0)
            ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
            return {"ok": True, "action": action}
        if action == "shutdown":
            subprocess.run(["shutdown", "/s", "/t", "5"], check=True)
            return {"ok": True, "action": action, "note": "desligando em 5 s"}
        if action == "restart":
            subprocess.run(["shutdown", "/r", "/t", "5"], check=True)
            return {"ok": True, "action": action, "note": "reiniciando em 5 s"}
        if action == "cancel":
            r = subprocess.run(["shutdown", "/a"], capture_output=True)
            return {"ok": r.returncode == 0, "action": action}
        return {"ok": False, "action": action, "error": "ação desconhecida"}
    except Exception as e:
        return {"ok": False, "action": action, "error": str(e)}
