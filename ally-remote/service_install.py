"""
Ally Remote — Serviço Windows
Instala/desinstala/inicia/para o servidor como serviço do Windows.
Requer: pip install pywin32
Uso:
  python service_install.py install   # instala e inicia
  python service_install.py remove    # para e desinstala
  python service_install.py start     # inicia
  python service_install.py stop      # para
  python service_install.py status    # exibe status
  python service_install.py config    # configura PIN / porta
"""

import sys
import os
import json
import pathlib
import subprocess
import argparse

SERVICE_NAME = "AllyRemote"
SERVICE_DISPLAY = "Ally Remote — Controle pelo Celular"
SERVICE_DESC = "Servidor WebSocket do Ally Remote. Permite controlar o ROG Ally pelo celular via Wi-Fi."

CONFIG_PATH = pathlib.Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "AllyRemote" / "config.json"
DEFAULT_CONFIG = {"port": 8765, "pin": None}


# ── utilidades ──────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text("utf-8"))
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")
    print(f">>> Configuração salva em: {CONFIG_PATH}")


def run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True,
                       creationflags=0x08000000)   # NO_WINDOW
    return r.returncode, (r.stdout + r.stderr).strip()


# ── implementação do serviço ─────────────────────────────────────────────────

def _run_as_service():
    """Ponto de entrada chamado internamente pelo SCM do Windows."""
    try:
        import win32serviceutil
        import win32service
        import win32event
        import servicemanager

        class AllyRemoteService(win32serviceutil.ServiceFramework):
            _svc_name_ = SERVICE_NAME
            _svc_display_name_ = SERVICE_DISPLAY
            _svc_description_ = SERVICE_DESC

            def __init__(self, args):
                super().__init__(args)
                self._stop = win32event.CreateEvent(None, 0, 0, None)
                self._proc = None

            def SvcStop(self):
                self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
                if self._proc:
                    self._proc.terminate()
                win32event.SetEvent(self._stop)

            def SvcDoRun(self):
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, ""),
                )
                cfg = load_config()
                exe = sys.executable
                script = str(pathlib.Path(__file__).parent / "server.py")
                cmd = [exe, script, "--port", str(cfg.get("port", 8765)),
                       "--no-firewall"]
                pin = cfg.get("pin")
                if pin:
                    cmd += ["--pin", str(pin)]
                self._proc = subprocess.Popen(cmd)
                win32event.WaitForSingleObject(self._stop, win32event.INFINITE)

        win32serviceutil.HandleCommandLine(AllyRemoteService)
    except ImportError:
        print("ERRO: pywin32 não instalado. Execute: pip install pywin32")
        sys.exit(1)


# ── comandos CLI ─────────────────────────────────────────────────────────────

def cmd_install():
    print(">>> Instalando serviço...")
    exe = sys.executable
    script = str(pathlib.Path(__file__).resolve())

    # Garante que o arquivo de config existe antes de instalar
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)

    code, out = run([
        "sc", "create", SERVICE_NAME,
        f"binPath= \"{exe}\" \"{script}\" --_service",
        "start=", "auto",
        "DisplayName=", SERVICE_DISPLAY,
    ])
    if code != 0:
        print(f"ERRO ao criar serviço:\n{out}")
        return

    run(["sc", "description", SERVICE_NAME, SERVICE_DESC])
    run(["sc", "failure", SERVICE_NAME, "reset=", "86400",
         "actions=", "restart/5000/restart/10000/restart/30000"])

    code2, out2 = run(["sc", "start", SERVICE_NAME])
    if code2 not in (0, 1056):   # 1056 = já rodando
        print(f"AVISO ao iniciar serviço:\n{out2}")
    else:
        print("✓ Serviço instalado e iniciado com sucesso!")
        print(f"  Porta: {load_config().get('port', 8765)}")
        pin = load_config().get("pin")
        print(f"  PIN:   {pin or '(sem PIN — configure com: python service_install.py config)'}")


def cmd_remove():
    run(["sc", "stop", SERVICE_NAME])
    code, out = run(["sc", "delete", SERVICE_NAME])
    if code == 0:
        print("✓ Serviço removido.")
    else:
        print(f"ERRO: {out}")


def cmd_start():
    code, out = run(["sc", "start", SERVICE_NAME])
    print("✓ Iniciado." if code in (0, 1056) else f"ERRO: {out}")


def cmd_stop():
    code, out = run(["sc", "stop", SERVICE_NAME])
    print("✓ Parado." if code in (0, 1062) else f"ERRO: {out}")


def cmd_status():
    _, out = run(["sc", "query", SERVICE_NAME])
    if "RUNNING" in out:
        print(f"✓ Serviço RODANDO")
    elif "STOPPED" in out:
        print("✗ Serviço PARADO")
    elif "não existe" in out.lower() or "does not exist" in out.lower():
        print("✗ Serviço NÃO INSTALADO")
    else:
        print(out)
    cfg = load_config()
    print(f"  Porta: {cfg.get('port', 8765)}")
    print(f"  PIN:   {cfg.get('pin') or '(sem PIN)'}")
    print(f"  Config: {CONFIG_PATH}")


def cmd_config():
    cfg = load_config()
    print("\n=== CONFIGURAÇÃO DO ALLY REMOTE ===\n")

    porta = input(f"Porta [{cfg.get('port', 8765)}]: ").strip()
    if porta.isdigit():
        cfg["port"] = int(porta)

    print("\nPIN de segurança (deixe em branco para desativar).")
    print("⚠  Sem PIN, qualquer dispositivo na rede pode controlar o Ally!")
    pin = input(f"PIN [{cfg.get('pin') or 'DESATIVADO'}]: ").strip()
    cfg["pin"] = pin if pin else None

    save_config(cfg)
    print("\n✓ Configuração salva.")
    print("  Reinicie o serviço para aplicar: python service_install.py stop && python service_install.py start")


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--_service" in sys.argv:
        sys.argv.remove("--_service")
        _run_as_service()
        sys.exit(0)

    p = argparse.ArgumentParser(description="Gerenciador do serviço Ally Remote")
    p.add_argument("command", choices=["install", "remove", "start", "stop", "status", "config"])
    args = p.parse_args()

    NEEDS_ADMIN = {"install", "remove", "start", "stop"}
    if args.command in NEEDS_ADMIN:
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("⚠  Execute como Administrador para este comando.")
                sys.exit(1)
        except Exception:
            pass

    {"install": cmd_install, "remove": cmd_remove, "start": cmd_start,
     "stop": cmd_stop, "status": cmd_status, "config": cmd_config}[args.command]()
