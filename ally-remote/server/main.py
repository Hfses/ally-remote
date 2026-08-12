"""Bootstrap do servidor (CLI + firewall + QR + uvicorn) — FASE 1.

Substitui o main() do antigo server.py sem mudar a interface de linha de
comando: --port, --pin e --no-firewall continuam iguais.
"""

import argparse
import ctypes
import platform
import socket
import subprocess

import uvicorn

from .app import create_app
from .config import Config

IS_WINDOWS = platform.system() == "Windows"

try:
    import qrcode  # opcional: QR code no console para abrir no celular
except Exception:
    qrcode = None


def local_ip() -> str:
    """Descobre o IP local (o que o celular deve usar)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "IP-do-Ally"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_firewall(port: int):
    """Cria a regra de firewall (uma vez) para o celular conseguir conectar."""
    rule = "Ally Remote"
    try:
        q = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule}"],
            capture_output=True,
        )
        if q.returncode == 0:
            return  # regra já existe
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             f"name={rule}", "dir=in", "action=allow", "protocol=TCP",
             f"localport={port}", "profile=private,domain"],
            capture_output=True,
        )
        print(f">>> Regra de firewall '{rule}' criada (porta {port}/TCP, rede privada).")
    except Exception as e:
        print(f">>> Não consegui configurar o firewall automaticamente: {e}")
        print(f">>> Libere manualmente a porta {port}/TCP em redes privadas.")


def main(argv=None):
    p = argparse.ArgumentParser(description="Ally Remote — servidor local")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--pin", default=None, help="PIN opcional exigido do celular")
    p.add_argument("--no-firewall", action="store_true",
                   help="não criar regra de firewall automaticamente")
    args = p.parse_args(argv)
    config = Config(port=args.port, pin=args.pin, no_firewall=args.no_firewall)

    print()
    print("  ============================================")
    print("   ALLY REMOTE — controle o Ally pelo celular")
    print("  ============================================")
    print()

    if not IS_WINDOWS:
        print(">>> Rodando em MODO MOCK (fora do Windows): nada é executado de verdade.")
    elif not is_admin():
        print(">>> AVISO: sem privilégios de Administrador.")
        print(">>> RAM e modo de desempenho NÃO vão funcionar. Feche e rode como admin.")
    elif not args.no_firewall:
        ensure_firewall(config.port)

    if config.pin is None:
        print(">>> SEM PIN: qualquer dispositivo na sua rede pode controlar este PC.")
        print(">>> Para exigir um PIN: AllyRemote.exe --pin 4321")

    url = f"http://{local_ip()}:{config.port}"
    print()
    print(f">>> No celular (mesmo Wi-Fi), abra:  {url}")
    if qrcode:
        try:
            qr = qrcode.QRCode(border=1)
            qr.add_data(url)
            qr.print_ascii(invert=True)
        except Exception:
            pass
    print(">>> Deixe esta janela aberta enquanto usa o app. CTRL+C para sair.")
    print()

    uvicorn.run(create_app(config), host="0.0.0.0", port=config.port,
                log_level="warning")


if __name__ == "__main__":
    main()
