"""Descoberta UDP (FASE 1): responder probe, ignorar lixo, sinalizar PIN."""

import json

from server.backends import get_backend
from server.config import Config
from server.discovery import PROBE_MAGIC, DiscoveryServer


class FakeTransport:
    def __init__(self):
        self.sent = []

    def sendto(self, data, addr):
        self.sent.append((data, addr))


def test_discovery_responds_to_probe():
    backend = get_backend()
    srv = DiscoveryServer(Config(port=8765), backend)
    t = FakeTransport()
    srv.connection_made(t)

    srv.datagram_received(PROBE_MAGIC, ("192.168.1.50", 40000))

    assert len(t.sent) == 1
    data, addr = t.sent[0]
    assert addr == ("192.168.1.50", 40000)
    payload = json.loads(data.decode("utf-8"))
    assert payload["name"] == "Ally Remote"
    assert payload["port"] == 8765
    assert payload["needs_pin"] is False
    assert "model" in payload and "version" in payload


def test_discovery_ignores_unknown_datagrams():
    backend = get_backend()
    srv = DiscoveryServer(Config(), backend)
    t = FakeTransport()
    srv.connection_made(t)

    srv.datagram_received(b"qualquer coisa", ("192.168.1.50", 40000))

    assert t.sent == []


def test_discovery_reports_pin():
    backend = get_backend()
    srv = DiscoveryServer(Config(pin="1234"), backend)
    t = FakeTransport()
    srv.connection_made(t)

    srv.datagram_received(PROBE_MAGIC, ("10.0.0.9", 40001))

    payload = json.loads(t.sent[0][0].decode("utf-8"))
    assert payload["needs_pin"] is True
