"""Collector de métricas — telemetria single-flight e histórico (FASE 1).

Corrige o problema do antigo stats.py: o cálculo de CPU% usava estado global
(_prev), então com 2+ clientes os deltas se corrompiam mutuamente. Aqui o
estado é POR INSTÂNCIA (CpuTimes) e o MetricsCollector serializa as amostras
com um lock: uma amostra é computada no máximo 1× por intervalo para TODOS
os clientes (push e polling veem a mesma leitura).
"""

import ctypes
import platform
import subprocess
import threading
import time
from collections import deque
from ctypes import wintypes

IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000
_TEMP_TTL_S = 30.0


class _FILETIME(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]


def _u64(ft: _FILETIME) -> int:
    return (ft.high << 32) | ft.low


class CpuTimes:
    """CPU% pela diferença de GetSystemTimes — estado por instância.

    A correção da FASE 1: cada instância tem o seu _prev; o servidor usa uma
    única instância compartilhada (via MetricsCollector), então os deltas
    nunca são corrompidos entre clientes.
    """

    def __init__(self):
        self._prev = {"idle": 0, "total": 0}

    def sample(self) -> float | None:
        if not IS_WINDOWS:
            return None
        idle, kern, user = _FILETIME(), _FILETIME(), _FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
            return None
        i, k, u = _u64(idle), _u64(kern), _u64(user)
        total = k + u  # kernel já inclui o idle
        di = i - self._prev["idle"]
        dt = total - self._prev["total"]
        self._prev["idle"], self._prev["total"] = i, total
        if dt <= 0:
            return None
        return round(max(0.0, min(100.0, (1.0 - di / dt) * 100.0)), 1)


_TEMP_CACHE = {"v": None, "at": 0.0}


def cpu_temp_c() -> float | None:
    """Temperatura via WMI (MSAcpi_ThermalZoneTemperature) com cache TTL.

    O subprocesso do PowerShell custa ~100-300 ms — com TTL de 30 s ele roda
    no máximo uma vez por meio minuto, não a cada poll de cada cliente
    (era um dos pontos frágeis apontados no plano).
    """
    if not IS_WINDOWS:
        return None
    now = time.monotonic()
    if _TEMP_CACHE["v"] is not None and now - _TEMP_CACHE["at"] < _TEMP_TTL_S:
        return _TEMP_CACHE["v"]
    v = _cpu_temp_windows()
    _TEMP_CACHE["v"], _TEMP_CACHE["at"] = v, now
    return v


def _cpu_temp_windows() -> float | None:
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


class MetricsCollector:
    """Amostragem single-flight + anel de histórico (30 min, janelas 1/5/10/30).

    - sample_metrics(): devolve a última amostra (ou computa uma nova se a
      anterior tiver mais de `min_interval` segundos). Thread-safe;
    - history(window_s): pontos recentes para as janelas do protocolo.
    """

    def __init__(self, backend, min_interval: float = 1.0,
                 history_seconds: int = 1800):
        self._backend = backend
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._last_sample: dict | None = None
        self._last_at = 0.0
        # 1800 s a ~1 amostra/s cabe folgado no maxlen (o padrão é 1800 + folga)
        self._ring: deque = deque(maxlen=history_seconds + 64)

    def sample_metrics(self) -> dict:
        with self._lock:
            now = time.monotonic()
            if self._last_sample is not None and now - self._last_at < self._min_interval:
                return dict(self._last_sample)
            m = self._backend.sample_metrics()
            self._last_sample = m
            self._last_at = now
            self._ring.append({"ts": time.time(), **m})
            return dict(m)

    def history(self, window_s: float = 300.0) -> list:
        cutoff = time.time() - window_s
        with self._lock:
            return [dict(p) for p in self._ring if p["ts"] >= cutoff]
