r"""
ally_acpi.py — Acesso ao firmware ASUS via driver ATKACPI (\\.\ATKACPI).

Usa exatamente o mesmo caminho do G-Helper e do Armoury Crate:
  - Escrita:  método WMI "DEVS" (0x53564544)
  - Leitura:  método WMI "DSTS" (0x53545344)
  - IOCTL:    0x0022240C

Endpoints usados aqui (mesmos IDs do kernel Linux asus-wmi e do G-Helper):
  - 0x00120075  Throttle Thermal Policy (modo de desempenho)
                0 = Balanced (Performance no Ally), 1 = Turbo, 2 = Silent
  - 0x00110013  Fan da CPU (leitura). O valor retornado está em unidades
                de ~100 RPM (mesma convenção usada pelo G-Helper).

Requisito: driver "ASUS System Control Interface" instalado (vem de fábrica
no ROG Ally). O processo precisa rodar como Administrador.

ATENÇÃO: este módulo só funciona no Windows do Ally. Não foi possível
testá-lo fora desse hardware — validar conforme o README.
"""

import ctypes
import struct
from ctypes import wintypes

ATK_PATH = r"\\.\ATKACPI"
ATK_IOCTL = 0x0022240C

METHOD_DSTS = 0x53545344  # "DSTS" — ler
METHOD_DEVS = 0x53564544  # "DEVS" — escrever

DEV_PERF_MODE = 0x00120075  # throttle thermal policy
DEV_FAN_CPU = 0x00110013    # fan CPU (leitura, ~x100 RPM)
DEV_CPU_FAN_CURVE = 0x00110024  # curva da fan da CPU (mesma do G-Helper)
DEV_GPU_FAN_CURVE = 0x00110025  # curva da fan da GPU

PERF_MODES = {
    0: "Performance (Balanced)",
    1: "Turbo",
    2: "Silent",
}

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class AllyACPI:
    def __init__(self):
        k32 = ctypes.windll.kernel32
        self._k32 = k32
        self._h = k32.CreateFileW(
            ATK_PATH,
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if self._h == INVALID_HANDLE_VALUE or self._h is None:
            raise OSError(
                "Não consegui abrir \\\\.\\ATKACPI. Verifique se o driver "
                "'ASUS System Control Interface' está instalado e se o "
                "servidor está rodando como Administrador."
            )

    def close(self):
        if getattr(self, "_h", None):
            self._k32.CloseHandle(self._h)
            self._h = None

    def _invoke(self, method_id: int, args: bytes) -> int:
        # Layout do buffer de entrada: uint32 method_id, uint32 tamanho, args
        in_buf = struct.pack("<II", method_id, len(args)) + args
        out_buf = ctypes.create_string_buffer(16)
        returned = wintypes.DWORD(0)
        ok = self._k32.DeviceIoControl(
            self._h,
            ATK_IOCTL,
            in_buf,
            len(in_buf),
            out_buf,
            ctypes.sizeof(out_buf),
            ctypes.byref(returned),
            None,
        )
        if not ok:
            raise OSError(f"DeviceIoControl falhou (erro {ctypes.GetLastError()})")
        return struct.unpack("<I", out_buf.raw[:4])[0]

    def device_get(self, device_id: int) -> int:
        """DSTS. Retorna o valor do endpoint, ou -1 se não suportado."""
        raw = self._invoke(METHOD_DSTS, struct.pack("<II", device_id, 0))
        # Convenção ASUS WMI: bit 0x10000 marca "suportado".
        if raw >= 0x10000:
            return raw - 0x10000
        return -1

    def device_set(self, device_id: int, value: int) -> int:
        """DEVS. Retorna o status do firmware (1 = ok na maioria dos casos)."""
        return self._invoke(METHOD_DEVS, struct.pack("<II", device_id, value))

    # ---- Operações de alto nível -------------------------------------

    def set_performance_mode(self, mode: int) -> dict:
        if mode not in PERF_MODES:
            raise ValueError("Modo inválido. Use 0=Performance, 1=Turbo, 2=Silent.")
        status = self.device_set(DEV_PERF_MODE, mode)
        return {"mode": mode, "label": PERF_MODES[mode], "firmware_status": status}

    def get_performance_mode(self) -> dict:
        v = self.device_get(DEV_PERF_MODE)
        return {"mode": v, "label": PERF_MODES.get(v, "desconhecido")}

    def get_fan_rpm(self) -> dict:
        v = self.device_get(DEV_FAN_CPU)
        if v < 0:
            return {"raw": v, "rpm": None}
        # Mesma convenção do G-Helper: valor em unidades de ~100 RPM.
        return {"raw": v, "rpm": v * 100}

    def set_fan_curve(self, percent: int) -> dict:
        """EXPERIMENTAL: aplica uma curva de fan plana no percentual dado.

        Formato do G-Helper/asus-wmi: 8 temperaturas + 8 velocidades (%).
        Uma curva "plana" no mesmo % em todas as faixas = fan fixa nesse nível.
        Pode não funcionar em todo firmware do Ally — falha de forma segura.
        """
        percent = max(20, min(100, int(percent)))
        temps = bytes([30, 40, 50, 60, 70, 80, 90, 100])
        speeds = bytes([percent] * 8)
        curve = temps + speeds  # 16 bytes
        results = {}
        for name, dev in (("cpu", DEV_CPU_FAN_CURVE), ("gpu", DEV_GPU_FAN_CURVE)):
            try:
                args = struct.pack("<I", dev) + curve
                self._invoke(METHOD_DEVS, args)
                results[name] = "ok"
            except Exception as e:
                results[name] = f"falhou: {e}"
        return {"ok": True, "percent": percent, "zones": results}
