"""Canal de telemetria PUSH (FASE 1).

O servidor antigo só tinha polling (status a cada 8 s, stats a cada 1,2 s).
Aqui, clientes que assinarem ({t:"telemetry_sub"}) recebem {t:"telemetry"}
broadcast a cada `interval` segundos. Uma única amostra por tick é computada
e compartilhada por todos os clientes (ver monitoring/collector.py) — sem
corromper deltas de CPU% com múltiplos clientes.
"""

import asyncio
import time


class TelemetryBroker:
    def __init__(self, collector, interval: float = 2.0):
        self._collector = collector
        self._interval = interval
        self._subs: set = set()
        self._task: asyncio.Task | None = None

    def subscribe(self, ws) -> None:
        self._subs.add(ws)

    def unsubscribe(self, ws) -> None:
        self._subs.discard(ws)

    def count(self) -> int:
        return len(self._subs)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                sample = await asyncio.to_thread(self._collector.sample_metrics)
            except Exception:
                continue  # nunca derruba o push por causa de uma leitura ruim
            payload = {"t": "telemetry", "ts": time.time(), **sample}
            for ws in list(self._subs):
                try:
                    await ws.send_json(payload)
                except Exception:
                    self._subs.discard(ws)  # cliente morreu: para de enviar
