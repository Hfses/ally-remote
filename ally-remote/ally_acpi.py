"""Shim de compatibilidade (FASE 1) — o módulo foi movido para hardware/.

Uso: `from ally_acpi import AllyACPI` continua funcionando.
"""

from hardware.ally_acpi import *  # noqa: F401,F403
