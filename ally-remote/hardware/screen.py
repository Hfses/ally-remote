"""
screen.py — Captura da tela do Ally para espelhar no celular (MJPEG).

Estratégia (a mais simples que funciona sem instalar nada no celular):
captura a tela com `mss`, reduz a resolução, comprime em JPEG e envia os
quadros por WebSocket binário. O celular mostra os quadros num <img>.

É honesto dizer: isso é ótimo para desktop, emuladores, RPG, estratégia e
jogos em geral numa rede Wi-Fi boa (5 GHz). Para FPS competitivo, o ideal
continua sendo Moonlight + Sunshine (encoder de vídeo por hardware, latência
menor). Aqui a prioridade é: zero instalação no celular e integração total.

Fora do Windows (modo mock) gera um quadro de teste, para dá pra validar
todo o caminho de streaming sem hardware real.
"""

import io
import platform
import threading
import time

IS_WINDOWS = platform.system() == "Windows"

try:
    from PIL import Image, ImageDraw
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

try:
    import mss
    HAVE_MSS = True
except Exception:
    HAVE_MSS = False


# mss não é thread-safe: cada thread precisa da sua própria instância.
_local = threading.local()


def available() -> bool:
    if not HAVE_PIL:
        return False
    return HAVE_MSS if IS_WINDOWS else True


def _grab_windows():
    sct = getattr(_local, "sct", None)
    if sct is None:
        sct = _local.sct = mss.mss()
    mon = sct.monitors[1]  # monitor principal
    shot = sct.grab(mon)
    return Image.frombytes("RGB", shot.size, shot.rgb), mon["width"], mon["height"]


def _grab_mock():
    # Gradiente + relógio, só para provar que o streaming funciona.
    w, h = 1280, 720
    img = Image.new("RGB", (w, h))
    px = img.load()
    t = int(time.time() * 30) % w
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            r = (x * 255) // w
            g = (y * 255) // h
            b = ((x + t) * 255 // w) % 255
            for dy in range(4):
                for dx in range(4):
                    if x + dx < w and y + dy < h:
                        px[x + dx, y + dy] = (r, g, b)
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 640, 120], fill=(0, 0, 0))
    d.text((60, 60), f"ALLY REMOTE (mock)  frame {int(time.time()*10)%10000}",
           fill=(255, 255, 255))
    return img, w, h


def capture_jpeg(max_width: int = 1024, quality: int = 45) -> tuple[bytes, int, int]:
    """Captura um quadro, reduz para max_width e devolve (jpeg, largura_real, altura_real)."""
    if IS_WINDOWS:
        img, sw, sh = _grab_windows()
    else:
        img, sw, sh = _grab_mock()

    if img.width > max_width:
        scale = max_width / img.width
        img = img.resize((max_width, max(1, int(img.height * scale))), Image.BILINEAR)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=int(quality))
    return buf.getvalue(), sw, sh
