"""Entrada virtual — mouse e teclado (FASE 1).

  win_input.py — injeção de mouse via SendInput (ctypes)
  cursor.py    — tamanho do ponteiro (registro) + "encontrar" (espiral)
  keyboard.py  — teclado pynput + teclas especiais (só Windows)

ATENÇÃO: não importe `virtual_input.keyboard` fora do Windows (pynput é
dependência com marker win32 no requirements.txt).
"""
