"""Endpoint /ws — autenticação + despacho por registro (FASE 1).

O fluxo é idêntico ao do antigo server.py:
  - sem PIN: autenticado automaticamente;
  - com PIN: só o 1º frame {t:"auth", pin} é aceito até autenticar;
  - comandos sem resposta rodam direto; com resposta, em asyncio.to_thread;
  - payload inválido → {"t":"error"} (mesmo comportamento anterior).
"""

import json
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from . import protocol


@dataclass
class Ctx:
    """Contexto passado aos handlers do protocolo."""

    ws: WebSocket
    backend: Any
    collector: Any
    telemetry: Any


def make_ws_endpoint(state):
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        authed = state.config.pin is None
        ctx = Ctx(ws=ws, backend=state.backend, collector=state.collector,
                  telemetry=state.telemetry)
        try:
            while True:
                msg = json.loads(await ws.receive_text())
                t = msg.get("t")

                if not authed:
                    if t == "auth" and str(msg.get("pin")) == state.config.pin:
                        authed = True
                        await ws.send_json({"t": "auth", "ok": True})
                    else:
                        await ws.send_json({"t": "auth", "ok": False})
                    continue

                handler = protocol.get_handler(t)
                if handler is not None:
                    await handler(ctx, msg)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            try:
                await ws.send_json({"t": "error", "error": str(e)})
            except Exception:
                pass
        finally:
            state.telemetry.unsubscribe(ws)

    return ws_endpoint
