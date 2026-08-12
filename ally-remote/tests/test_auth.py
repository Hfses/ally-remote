"""Autenticação por PIN — /ws (1º frame auth) e /stream (query pin)."""

import pytest
from starlette.websockets import WebSocketDisconnect


def test_ping_without_pin(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"t": "ping"})
        assert ws.receive_json() == {"t": "pong"}


def test_pin_wrong_then_correct(pin_client):
    with pin_client.websocket_connect("/ws") as ws:
        # PIN errado: rejeitado
        ws.send_json({"t": "auth", "pin": "0000"})
        assert ws.receive_json() == {"t": "auth", "ok": False}

        # Antes de autenticar, QUALQUER comando é rejeitado com ok:False
        # (comportamento original preservado)
        ws.send_json({"t": "ping"})
        assert ws.receive_json() == {"t": "auth", "ok": False}

        # PIN correto: autentica e passa a responder
        ws.send_json({"t": "auth", "pin": "4321"})
        assert ws.receive_json() == {"t": "auth", "ok": True}
        ws.send_json({"t": "ping"})
        assert ws.receive_json() == {"t": "pong"}


def test_stream_rejects_wrong_pin(pin_client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with pin_client.websocket_connect("/stream?pin=0000") as ws:
            ws.receive_bytes()
    assert exc.value.code == 4001


def test_stream_accepts_pin(pin_client):
    with pin_client.websocket_connect("/stream?pin=4321&w=320&q=50&fps=5") as ws:
        data = ws.receive_bytes()
        assert data[:2] == b"\xff\xd8"  # magic do JPEG
