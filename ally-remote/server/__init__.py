"""Ally Remote — pacote do servidor (refatoração FASE 1).

O antigo server.py monolítico foi extraído aqui: `server/app.py` monta o
FastAPI, `server/protocol.py` registra os comandos, `server/backends/` define
os backends real (Windows) e mock, `server/telemetry.py` e
`server/discovery.py` são as novidades da FASE 1.

O ponto de entrada continua `python server.py` (shim na raiz) — o protocolo
WebSocket/HTTP não mudou.
"""

__version__ = "0.2.0"
