"""Ponto de entrada de compatibilidade (FASE 1).

O servidor foi reorganizado no pacote `server/` (app, protocolo, backends,
telemetria, descoberta). Este arquivo existe para que `python server.py` e o
build PyInstaller continuem funcionando exatamente como antes.
"""

from server.main import main

if __name__ == "__main__":
    main()
