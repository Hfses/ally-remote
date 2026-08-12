"""Shim de compatibilidade (FASE 1).

A implementação foi absorvida por monitoring/collector.py — que corrige o
estado global de CPU% que corrompia deltas com 2+ clientes (o servidor usa
uma única instância compartilhada; este shim mantém a API antiga
cpu_percent()/cpu_temp_c() para quem importava stats diretamente).
"""

from monitoring.collector import CpuTimes, cpu_temp_c as _cpu_temp_c

_cpu = CpuTimes()


def cpu_percent() -> float | None:
    return _cpu.sample()


def cpu_temp_c() -> float | None:
    return _cpu_temp_c()
