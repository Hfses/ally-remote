"""Fábrica do aplicativo FastAPI (FASE 1).

Reúne os endpoints HTTP (/, /needs-pin, /static) e os WebSockets (/ws, /stream)
com o ciclo de vida: telemetria push + descoberta UDP + pré-aquecimento de
capabilities. O comportamento dos endpoints é idêntico ao do antigo server.py.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from monitoring.collector import MetricsCollector

from . import protocol
from .backends import get_backend
from .config import BASE, Config
from .discovery import DiscoveryServer
from .stream import make_stream_endpoint
from .telemetry import TelemetryBroker
from .ws import make_ws_endpoint


class AppState:
    """Estado compartilhado do app (config, backend, collector, telemetria)."""

    def __init__(self, config, backend, collector, telemetry):
        self.config = config
        self.backend = backend
        self.collector = collector
        self.telemetry = telemetry
        self.discovery = None


def create_app(config: Config | None = None) -> FastAPI:
    config = config or Config()
    protocol.setup_commands()

    backend = get_backend()
    collector = MetricsCollector(backend)
    telemetry = TelemetryBroker(collector)
    state = AppState(config, backend, collector, telemetry)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        telemetry.start()
        discovery = DiscoveryServer(config, backend)
        state.discovery = discovery
        await discovery.start()
        # Pré-aquece as capabilities (a 1ª detecção de modelo usa PowerShell)
        # em thread, para não travar o event loop no boot.
        asyncio.create_task(asyncio.to_thread(backend.capabilities))
        yield
        await discovery.stop()
        await telemetry.stop()

    app = FastAPI(title="Ally Remote", lifespan=lifespan)

    app.websocket("/ws")(make_ws_endpoint(state))
    app.websocket("/stream")(make_stream_endpoint(config))

    @app.get("/")
    async def index():
        return FileResponse(BASE / "static" / "index.html")

    @app.get("/needs-pin")
    async def needs_pin():
        return {"pin": config.pin is not None}

    app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

    return app
