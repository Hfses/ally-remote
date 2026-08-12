"""
games.py — Encontra e abre jogos no Ally (Windows).

Duas fontes, sem instalar nada:

1. Steam: lê o SteamPath no registro, varre as pastas de biblioteca
   (libraryfolders.vdf) e cada appmanifest_*.acf → nome + appid. Abre com
   o link  steam://rungameid/<appid>  (funciona mesmo com o Steam fechado).

2. Atalhos (.lnk): Área de Trabalho + Menu Iniciar. Pega o que parece jogo
   e ignora desinstaladores/manuais. Abre com os.startfile.

Cada jogo tem um "id" opaco: "steam:APPID" ou "lnk:CAMINHO".
"""

import glob
import os
import platform
import re

IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    import winreg

_IGNORE = re.compile(
    r"(uninstall|desinstal|readme|manual|config|setup|redist|report|"
    r"crash|launcher settings|website|support|eula)", re.I)


def _steam_path():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            return winreg.QueryValueEx(k, "SteamPath")[0]
    except Exception:
        return None


def _steam_libs(steam):
    libs = [steam]
    vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf, encoding="utf-8", errors="ignore") as f:
            for m in re.finditer(r'"path"\s*"([^"]+)"', f.read()):
                libs.append(m.group(1).replace("\\\\", "\\"))
    except Exception:
        pass
    return libs


def _steam_games():
    steam = _steam_path()
    if not steam:
        return []
    out = []
    for lib in _steam_libs(steam):
        for acf in glob.glob(os.path.join(lib, "steamapps", "appmanifest_*.acf")):
            try:
                with open(acf, encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                appid = re.search(r'"appid"\s*"(\d+)"', txt)
                name = re.search(r'"name"\s*"([^"]+)"', txt)
                if appid and name and not _IGNORE.search(name.group(1)):
                    out.append({"id": f"steam:{appid.group(1)}",
                                "name": name.group(1), "source": "Steam"})
            except Exception:
                continue
    return out


def _shortcut_dirs():
    dirs = []
    for var in ("PUBLIC", "USERPROFILE"):
        base = os.environ.get(var)
        if base:
            dirs.append(os.path.join(base, "Desktop"))
    appdata = os.environ.get("APPDATA")
    if appdata:
        dirs.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"))
    pd = os.environ.get("PROGRAMDATA")
    if pd:
        dirs.append(os.path.join(pd, r"Microsoft\Windows\Start Menu\Programs"))
    return dirs


def _shortcut_games():
    out, seen = [], set()
    for d in _shortcut_dirs():
        for lnk in glob.glob(os.path.join(d, "**", "*.lnk"), recursive=True):
            name = os.path.splitext(os.path.basename(lnk))[0]
            key = name.lower()
            if key in seen or _IGNORE.search(name):
                continue
            seen.add(key)
            out.append({"id": f"lnk:{lnk}", "name": name, "source": "Atalho"})
    return out


def list_games() -> list:
    if not IS_WINDOWS:
        return []
    games = _steam_games() + _shortcut_games()
    # remove duplicados por nome, Steam tem prioridade (vem antes)
    seen, uniq = set(), []
    for g in games:
        k = g["name"].lower()
        if k not in seen:
            seen.add(k)
            uniq.append(g)
    uniq.sort(key=lambda g: g["name"].lower())
    return uniq


def launch_game(gid: str) -> dict:
    if not IS_WINDOWS:
        return {"ok": False, "error": "só no Windows"}
    try:
        if gid.startswith("steam:"):
            appid = gid.split(":", 1)[1]
            os.startfile(f"steam://rungameid/{appid}")
            return {"ok": True}
        if gid.startswith("lnk:"):
            path = gid.split(":", 1)[1]
            os.startfile(path)
            return {"ok": True}
        return {"ok": False, "error": "id inválido"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
