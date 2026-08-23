"""Comandos do protocolo /ws — todos os `t` originais preservados.

A FASE 1 não renomeia nem remove comando nenhum: este arquivo é a garantia
de regressão disso.
"""

from server import protocol

# Conjunto EXATO de comandos do protocolo (originais + aditivos da FASE 1).
EXPECTED_COMMANDS = {
    "move", "moveabs", "scroll", "click", "drag", "text", "key",
    "ram", "perf", "led", "power", "pointer", "brightness", "monitor",
    "fan", "games", "launch", "stats", "status", "ping",
    # FASE 1 (aditivos — clientes antigos os ignoram)
    "telemetry_sub", "hist",
    # Gamepad virtual (aditivos)
    "gp_btn", "gp_lstick", "gp_rstick", "gp_trigger", "gp_reset", "gp_info",
}


def test_protocol_commands_preserved():
    """Nenhum comando do protocolo original foi removido ou renomeado."""
    protocol.setup_commands()
    assert set(protocol.registered()) == EXPECTED_COMMANDS


def _cmd(client, t, **payload):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"t": t, **payload})
        return ws.receive_json()


def test_response_commands(client):
    r = _cmd(client, "ram")
    assert r["t"] == "ram" and "freed_mb" in r and "standby_purged" in r

    r = _cmd(client, "perf", mode=1)
    assert r["t"] == "perf" and r["ok"] is True and r["mode"] == 1
    assert r["label"] == "Turbo"

    r = _cmd(client, "led", r=255, g=0, b=0)
    assert r["t"] == "led" and r["ok"] is True and r["rgb"] == [255, 0, 0]

    r = _cmd(client, "power", action="sleep")
    assert r["t"] == "power" and r["ok"] is True and r["action"] == "sleep"

    r = _cmd(client, "pointer", action="find")
    assert r["t"] == "pointer" and r["action"] == "find"

    r = _cmd(client, "pointer", action="size", value=8)
    assert r["t"] == "pointer" and r["size"] == 8

    r = _cmd(client, "brightness", value=40)
    assert r["t"] == "brightness" and r["ok"] is True and r["brightness"] == 40

    r = _cmd(client, "monitor", action="off")
    assert r["t"] == "monitor" and r["ok"] is True and r["action"] == "off"

    r = _cmd(client, "fan", action="max")
    assert r["t"] == "fan" and r["ok"] is True and r["action"] == "max"

    r = _cmd(client, "fan", action="custom", value=70)
    assert r["t"] == "fan" and r["percent"] == 70

    r = _cmd(client, "games")
    assert r["t"] == "games" and len(r["games"]) >= 4

    r = _cmd(client, "launch", id="steam:1091500")
    assert r["t"] == "launch" and r["ok"] is True

    r = _cmd(client, "stats")
    assert r["t"] == "stats"
    for k in ("cpu_pct", "cpu_temp_c", "fan_rpm", "mem_load", "mem_avail_mb",
              "battery"):
        assert k in r


def test_status_includes_capabilities(client):
    r = _cmd(client, "status")
    assert r["t"] == "status"
    assert r["platform"] == "mock"
    caps = r["capabilities"]
    # regra 15: capacidades não implementadas reportam false, nunca fake
    assert caps["tdp"] is False
    assert caps["gamepad"] is False
    assert caps["virtual_display"] is False
    assert caps["telemetry"] is True
    assert caps["discovery_udp"] is True
    assert caps["mirror"] is True  # mock gera quadro de teste


def test_no_response_commands_do_not_crash(client):
    """Comandos de alta frequência não respondem e não quebram a conexão."""
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"t": "move", "dx": 5, "dy": -3})
        ws.send_json({"t": "moveabs", "x": 0.5, "y": 0.25})
        ws.send_json({"t": "scroll", "dy": -1})
        ws.send_json({"t": "click", "btn": "left"})
        ws.send_json({"t": "click", "btn": "right", "double": True})
        ws.send_json({"t": "drag", "on": True})
        ws.send_json({"t": "drag", "on": False})
        ws.send_json({"t": "text", "s": "olá"})
        ws.send_json({"t": "key", "k": "enter"})
        ws.send_json({"t": "key", "k": "altf4"})
        ws.send_json({"t": "comando-desconhecido"})  # ignorado silenciosamente
        ws.send_json({"t": "ping"})
        assert ws.receive_json() == {"t": "pong"}


def test_bad_payload_reports_error(client):
    """Payload inválido → {"t":"error"} (comportamento original preservado)."""
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"t": "move"})  # falta dx/dy
        r = ws.receive_json()
        assert r["t"] == "error"
