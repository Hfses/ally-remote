"""Configuração do servidor e resolução de caminhos (incl. PyInstaller)."""

import sys
from dataclasses import dataclass
from pathlib import Path

# Quando empacotado pelo PyInstaller, os arquivos estáticos ficam em _MEIPASS.
# Fora dele: a raiz do servidor (pasta que contém `server/` e `static/`).
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


@dataclass
class Config:
    """Opções de linha de comando (--port, --pin, --no-firewall)."""

    port: int = 8765
    pin: str | None = None
    no_firewall: bool = False
