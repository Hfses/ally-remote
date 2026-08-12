"""Interface única do backend (real × mock) — FASE 1.

Cada comando do protocolo vira um método; os backends real (Windows) e mock
implementam a MESMA assinatura, então o dispatcher (server/protocol.py) não
precisa saber em qual plataforma está rodando. Isso elimina a duplicação
if IS_WINDOWS / else do antigo server.py.
"""

from abc import ABC, abstractmethod


class Backend(ABC):
    """Fachada executada pelos handlers do protocolo."""

    platform = "base"

    # ---- Entrada (sem resposta) ----
    def move(self, dx: int, dy: int) -> None:
        raise NotImplementedError

    def move_abs(self, x: float, y: float) -> None:
        raise NotImplementedError

    def scroll(self, dy: int) -> None:
        raise NotImplementedError

    def click(self, btn: str = "left", double: bool = False) -> None:
        raise NotImplementedError

    def drag(self, on: bool) -> None:
        raise NotImplementedError

    def text(self, s: str) -> None:
        raise NotImplementedError

    def key(self, k: str) -> None:
        raise NotImplementedError

    # ---- Ações (com resposta) ----
    def ram(self) -> dict:
        raise NotImplementedError

    def perf(self, mode) -> dict:
        raise NotImplementedError

    def led(self, r, g, b, mode=0, speed=0xE1) -> dict:
        raise NotImplementedError

    def power(self, action: str) -> dict:
        raise NotImplementedError

    def pointer(self, action: str, value=4) -> dict:
        raise NotImplementedError

    def brightness(self, value) -> dict:
        raise NotImplementedError

    def monitor(self, action: str) -> dict:
        raise NotImplementedError

    def fan(self, action: str, value=100) -> dict:
        raise NotImplementedError

    def games(self) -> dict:
        raise NotImplementedError

    def launch(self, gid: str) -> dict:
        raise NotImplementedError

    def status(self) -> dict:
        raise NotImplementedError

    # ---- FASE 1 ----
    @abstractmethod
    def capabilities(self) -> dict:
        """Mapa de capacidades do hardware (regra 14: detectar, não assumir)."""

    def capabilities_cached(self) -> dict:
        """Versão sem bloqueio (usada pelo discovery UDP no event loop)."""
        return self.capabilities()

    def sample_metrics(self) -> dict:
        """Amostra ao vivo de métricas (consumida pelo collector single-flight)."""
        raise NotImplementedError
