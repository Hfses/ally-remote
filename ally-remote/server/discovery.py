"""Descoberta do Ally por UDP broadcast (FASE 1).

O celular envia um datagrama "ALLYREMOTE_PROBE" para 255.255.255.255:8765 e o
servidor responde com nome/modelo/porta/versão. A varredura TCP continua como
fallback no app Android.

Regra de ouro: a resposta usa capabilities EM CACHE (capabilities_cached) —
nunca dispara PowerShell nem bloqueia o event loop.
"""

import asyncio
import json

PROBE_MAGIC = b"ALLYREMOTE_PROBE"


class DiscoveryServer(asyncio.DatagramProtocol):
    def __init__(self, config, backend):
        self._config = config
        self._backend = backend
        self._transport = None

    # ---- asyncio.DatagramProtocol ----

    def connection_made(self, transport):
        self._transport = transport

    def datagram_received(self, data, addr):
        if not data.startswith(PROBE_MAGIC):
            return
        caps = self._backend.capabilities_cached()
        payload = {
            "name": "Ally Remote",
            "model": caps.get("model"),
            "port": self._config.port,
            "version": caps.get("version"),
            "needs_pin": self._config.pin is not None,
        }
        try:
            self._transport.sendto(json.dumps(payload).encode("utf-8"), addr)
        except Exception:
            pass

    def error_received(self, exc):
        pass

    def connection_lost(self, exc):
        self._transport = None

    # ---- ciclo de vida ----

    async def start(self):
        loop = asyncio.get_running_loop()
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: self,
                local_addr=("0.0.0.0", self._config.port),
                allow_broadcast=True,
            )
            self._transport = transport
            print(f">>> Descoberta UDP ativa na porta {self._config.port} (broadcast).")
        except Exception as e:
            print(f">>> Descoberta UDP indisponível: {e}")

    async def stop(self):
        if self._transport is not None:
            self._transport.close()
            self._transport = None
