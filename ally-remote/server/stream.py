"""Endpoint /stream — espelhamento MJPEG (mantido do antigo server.py).

Envia quadros JPEG binários por WebSocket. Parâmetros pela query:
w (largura máx), q (qualidade JPEG 1–95), fps (quadros/s alvo) e
pin (se o servidor exigir PIN). Na FASE 3 o pipeline H.264 (/stream2)
vai substituí-lo como caminho principal — este endpoint permanece como
fallback e como compatibilidade com clientes antigos.
"""

import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from hardware import screen


def make_stream_endpoint(config):
    async def stream_endpoint(ws: WebSocket):
        await ws.accept()
        q = ws.query_params
        if config.pin is not None and str(q.get("pin")) != config.pin:
            await ws.close(code=4001)
            return
        if not screen.available():
            try:
                await ws.send_json(
                    {"error": "captura de tela indisponível (instale mss/Pillow)"})
            except Exception:
                pass
            await ws.close()
            return

        max_w = max(320, min(1920, int(q.get("w", 1024))))
        quality = max(10, min(95, int(q.get("q", 45))))
        fps = max(1, min(30, int(q.get("fps", 15))))
        interval = 1.0 / fps

        try:
            while True:
                t0 = asyncio.get_running_loop().time()
                jpeg, _, _ = await asyncio.to_thread(screen.capture_jpeg, max_w, quality)
                await ws.send_bytes(jpeg)
                dt = asyncio.get_running_loop().time() - t0
                if dt < interval:
                    await asyncio.sleep(interval - dt)
        except (WebSocketDisconnect, RuntimeError):
            pass
        except Exception:
            try:
                await ws.close()
            except Exception:
                pass

    return stream_endpoint
