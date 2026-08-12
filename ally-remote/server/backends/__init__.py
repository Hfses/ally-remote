"""Seleção do backend (real × mock) — FASE 1."""

import platform

from .base import Backend
from .mock import MockBackend


def get_backend() -> Backend:
    """Windows → backend real; qualquer outro sistema → mock."""
    if platform.system() == "Windows":
        from .real import RealBackend
        return RealBackend()
    return MockBackend()
