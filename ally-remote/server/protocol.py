"""Registro de comandos do protocolo /ws (FASE 1).

Substitui o dispatcher if/elif do antigo server.py por um registro
(dict `t` → handler). Os nomes `t`, os campos de payload e as respostas são
100% idênticos aos do protocolo original — nada foi renomeado ou removido.

Comandos novos da FASE 1 (telemetry_sub, hist) são aditivos: clientes antigos
ignoram mensagens com `t` desconhecido (a PWA usa um if/else-if e não tem
`default`).
"""

import asyncio
from typing import Any, Awaitable, Callable, Optional

# Handler: (ctx, msg) → opcionalmente responde diretamente via ctx.ws.
Handler = Callable[[Any, dict], Awaitable[None]]

_REGISTRY: dict[str, Handler] = {}

# Janelas do histórico de telemetria (comandos {t:"hist"}).
HIST_WINDOWS = {"1m": 60, "5m": 300, "10m": 600, "30m": 1800}


def register_command(t: str, backend_method: str, threaded: bool = False,
                     parse: Optional[Callable[[dict], tuple]] = None) -> None:
    """Registra um comando executado por um método do backend.

    - backend_method: nome do método em Backend (real e mock têm a MESMA
      assinatura — é isso que elimina a duplicação real×mock);
    - parse: msg → tupla de argumentos posicionais (mesmas conversões do
      dispatcher original: int(), str(), msg.get() com defaults...);
    - threaded: True para comandos com resposta (roda em asyncio.to_thread,
      como o servidor antigo fazia).
    """
    async def handler(ctx: Any, msg: dict) -> None:
        args = parse(msg) if parse else (msg,)
        fn = getattr(ctx.backend, backend_method)
        r = await asyncio.to_thread(fn, *args) if threaded else fn(*args)
        if r is not None:
            await ctx.ws.send_json({"t": t, **r})

    _REGISTRY[t] = handler


def register_plain(t: str, handler: Handler) -> None:
    """Registra um handler livre (camada de conexão: ping, assinaturas...)."""
    _REGISTRY[t] = handler


def get_handler(t: str) -> Optional[Handler]:
    return _REGISTRY.get(t)


def registered() -> list[str]:
    return sorted(_REGISTRY)


# ---------------------------------------------------------------------------
# Handlers da camada de conexão
# ---------------------------------------------------------------------------

async def _handle_ping(ctx: Any, msg: dict) -> None:
    await ctx.ws.send_json({"t": "pong"})


async def _handle_stats(ctx: Any, msg: dict) -> None:
    """{t:"stats"} — amostra ao vivo via collector single-flight (mesmo
    formato de resposta do protocolo original, com o estado global corrigido)."""
    sample = await asyncio.to_thread(ctx.collector.sample_metrics)
    await ctx.ws.send_json({"t": "stats", **sample})


async def _handle_telemetry_sub(ctx: Any, msg: dict) -> None:
    """{t:"telemetry_sub", on:true|false} — assina/cancela o push de telemetria."""
    on = bool(msg.get("on", True))
    if on:
        ctx.telemetry.subscribe(ctx.ws)
    else:
        ctx.telemetry.unsubscribe(ctx.ws)
    await ctx.ws.send_json({"t": "telemetry_sub", "ok": True, "on": on})


async def _handle_hist(ctx: Any, msg: dict) -> None:
    """{t:"hist", window:"1m"|"5m"|"10m"|"30m"} — histórico do collector."""
    window = str(msg.get("window", "5m"))
    seconds = HIST_WINDOWS.get(window, HIST_WINDOWS["5m"])
    points = ctx.collector.history(seconds)
    await ctx.ws.send_json({"t": "hist", "window": window, "points": points})


# ---------------------------------------------------------------------------
# Registro de TODOS os comandos
# ---------------------------------------------------------------------------

def setup_commands() -> None:
    """Registra todos os comandos (idempotente — chamado no bootstrap do app)."""
    if _REGISTRY:
        return

    # ---- Comandos de alta frequência: sem resposta (latência mínima) ----
    register_command("move", "move",
                     parse=lambda m: (int(m["dx"]), int(m["dy"])))
    register_command("moveabs", "move_abs",
                     parse=lambda m: (m.get("x", 0), m.get("y", 0)))
    register_command("scroll", "scroll",
                     parse=lambda m: (int(m["dy"]),))
    register_command("click", "click",
                     parse=lambda m: (m.get("btn", "left"), bool(m.get("double"))))
    register_command("drag", "drag",
                     parse=lambda m: (bool(m.get("on")),))
    register_command("text", "text",
                     parse=lambda m: (str(m.get("s", "")),))
    register_command("key", "key",
                     parse=lambda m: (str(m.get("k", "")),))

    # ---- Comandos com resposta (executados em thread, como no servidor antigo) ----
    register_command("ram", "ram", threaded=True, parse=lambda m: ())
    register_command("perf", "perf", threaded=True,
                     parse=lambda m: (m.get("mode", 0),))
    register_command("led", "led", threaded=True,
                     parse=lambda m: (m.get("r", 255), m.get("g", 255),
                                      m.get("b", 255), m.get("mode", 0),
                                      m.get("speed", 0xE1)))
    register_command("power", "power", threaded=True,
                     parse=lambda m: (str(m.get("action", "")),))
    register_command("pointer", "pointer", threaded=True,
                     parse=lambda m: (str(m.get("action", "")),
                                      int(m.get("value", 4))))
    register_command("brightness", "brightness", threaded=True,
                     parse=lambda m: (m.get("value", 50),))
    register_command("monitor", "monitor", threaded=True,
                     parse=lambda m: (str(m.get("action", "")),))
    register_command("fan", "fan", threaded=True,
                     parse=lambda m: (str(m.get("action", "")),
                                      int(m.get("value", 100))))
    register_command("games", "games", threaded=True, parse=lambda m: ())
    register_command("launch", "launch", threaded=True,
                     parse=lambda m: (m.get("id", ""),))
    register_command("status", "status", threaded=True, parse=lambda m: ())

    # ---- Camada de conexão ----
    register_plain("ping", _handle_ping)
    register_plain("stats", _handle_stats)

    # ---- FASE 1 (aditivo — clientes antigos ignoram t desconhecido) ----
    register_plain("telemetry_sub", _handle_telemetry_sub)
    register_plain("hist", _handle_hist)
