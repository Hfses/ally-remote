import os
import sys

# Garante que a raiz do servidor (ally-remote/) esteja no path, exatamente
# como quando o servidor roda (python server.py).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Config


@pytest.fixture
def app():
    return create_app(Config())


@pytest.fixture
def client(app):
    """Cliente sem PIN (autenticação automática)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def pin_client():
    """Cliente com PIN exigido (--pin 4321)."""
    with TestClient(create_app(Config(pin="4321"))) as c:
        yield c
