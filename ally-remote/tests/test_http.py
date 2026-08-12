"""Endpoints HTTP — comportamento idêntico ao do servidor antigo."""


def test_index_serves_pwa(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Ally Remote" in r.text


def test_needs_pin_without_pin(client):
    r = client.get("/needs-pin")
    assert r.status_code == 200
    assert r.json() == {"pin": False}


def test_needs_pin_with_pin(pin_client):
    r = pin_client.get("/needs-pin")
    assert r.json() == {"pin": True}


def test_static_manifest(client):
    r = client.get("/static/manifest.json")
    assert r.status_code == 200
    assert "application/json" in r.headers.get("content-type", "")
