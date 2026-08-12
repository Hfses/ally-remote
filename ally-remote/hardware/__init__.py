"""Pacote de módulos de hardware do ROG Ally (FASE 1).

Os módulos foram movidos da raiz para cá sem alteração de comportamento:
  ally_acpi.py   — firmware ASUS via driver ATKACPI (modo de desempenho, fan)
  ally_led.py    — LEDs dos analógicos via HID (protocolo 0x5D)
  display.py     — brilho (WMI) e desligar/ligar o monitor
  screen.py      — captura para espelhamento MJPEG (fallback legado)
  games.py       — jogos Steam + atalhos .lnk

Shims na raiz (ally_acpi.py etc.) re-exportam estes módulos para quem
importava pelo caminho antigo.
"""
