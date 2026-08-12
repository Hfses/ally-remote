"""Telemetria push (FASE 1): assinatura, broadcast e histórico."""


def test_telemetry_push(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"t": "telemetry_sub"})
        assert ws.receive_json() == {"t": "telemetry_sub", "ok": True, "on": True}
        # aguarda o 1º push (intervalo de 2 s)
        msg = ws.receive_json()
        assert msg["t"] == "telemetry"
        for k in ("cpu_pct", "cpu_temp_c", "fan_rpm", "mem_load",
                  "mem_avail_mb", "battery"):
            assert k in msg


def test_telemetry_unsubscribe(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"t": "telemetry_sub", "on": False})
        assert ws.receive_json() == {"t": "telemetry_sub", "ok": True, "on": False}
        # Sem assinatura não há push; o pong sempre chega (pode haver um push
        # em trânsito no caso de corrida com o tick de 2 s — descarta até achar).
        ws.send_json({"t": "ping"})
        msg = ws.receive_json()
        while msg["t"] == "telemetry":
            msg = ws.receive_json()
        assert msg == {"t": "pong"}


def test_hist_window(client):
    with client.websocket_connect("/ws") as ws:
        # garante pelo menos uma amostra no anel
        ws.send_json({"t": "stats"})
        assert ws.receive_json()["t"] == "stats"

        ws.send_json({"t": "hist", "window": "1m"})
        r = ws.receive_json()
        assert r["t"] == "hist" and r["window"] == "1m"
        assert isinstance(r["points"], list)
        assert len(r["points"]) >= 1
        assert "cpu_pct" in r["points"][0] and "ts" in r["points"][0]


def test_hist_unknown_window_defaults(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"t": "hist", "window": "99x"})
        r = ws.receive_json()
        assert r["t"] == "hist" and r["window"] == "99x"
        assert isinstance(r["points"], list)
