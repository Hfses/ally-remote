"""/stream MJPEG — parâmetros de query e conteúdo binário."""


def test_stream_sends_jpeg_frames(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"t": "status"})
        st = ws.receive_json()
        assert st["t"] == "status" and st["screen"] is True

    with client.websocket_connect("/stream?w=320&q=50&fps=5") as ws:
        data = ws.receive_bytes()
        assert data[:2] == b"\xff\xd8"  # magic do JPEG
        assert len(data) > 100


def test_stream_clamps_params(client):
    # w/q/fps são limitados (320–1920, 10–95, 1–30) sem quebrar
    with client.websocket_connect("/stream?w=99999&q=1&fps=999") as ws:
        data = ws.receive_bytes()
        assert data[:2] == b"\xff\xd8"
