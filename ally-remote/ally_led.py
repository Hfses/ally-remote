"""Shim de compatibilidade (FASE 1) — o módulo foi movido para hardware/.

Uso: `from ally_led import set_color` continua funcionando; o CLI
`python ally_led.py --list` também.
"""

from hardware.ally_led import *  # noqa: F401,F403
from hardware.ally_led import list_devices, set_color  # noqa: F401


if __name__ == "__main__":
    import json
    import sys

    if "--list" in sys.argv:
        print(json.dumps(list_devices(), indent=2))
    else:
        # teste rápido: vermelho
        print(json.dumps(set_color(255, 0, 0), indent=2))
