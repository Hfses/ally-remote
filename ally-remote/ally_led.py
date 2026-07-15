"""
ally_led.py — Controle dos anéis de LED dos analógicos do ROG Ally.

DECISÃO (pesquisada em jul/2026):
- OpenRGB NÃO tem suporte confiável ao Ally (relatos de usuários confirmam
  que não funciona nesse hardware).
- Não existe SDK Aura oficial utilizável para o Ally.
- O caminho confiável hoje é o mesmo usado por G-Helper e Handheld Companion:
  falar direto com o dispositivo HID de iluminação do Ally
  (VID 0x0B05, interface Aura) usando o protocolo 0x5D:
    0xB3 = configurar (modo/cor/velocidade)
    0xB5 = gravar     ("set")
    0xB4 = aplicar    ("apply")
  A ordem B3 -> B5 -> B4 é a documentada como correta para o firmware do Ally.

IMPORTANTE:
- Se o Armoury Crate SE (serviços ASUS) estiver rodando, ele pode sobrescrever
  a cor logo em seguida. Feche/pare os serviços ASUS ou use o G-Helper
  (Extra -> Stop services) se a cor "voltar sozinha".
- "Iluminação Dinâmica" do Windows 11 (Configurações > Personalização)
  também pode interferir; desative para este dispositivo se necessário.
- Este módulo NÃO pôde ser testado fora do hardware real. Se não funcionar
  de primeira, rode `python ally_led.py --list` para ver as interfaces HID
  e me diga a saída.
"""

import hid

ASUS_VID = 0x0B05
# PIDs conhecidos: 0x1ABE (Ally RC71L), 0x1B4C (Ally X RC72LA)
ALLY_PIDS = {0x1ABE, 0x1B4C}
REPORT_ID = 0x5D
REPORT_LEN = 64  # incluindo o report ID
AURA_USAGE_PAGE = 0xFF31


def _candidates():
    devs = hid.enumerate(ASUS_VID)
    # Preferir interface Aura (usage_page 0xFF31) de um PID conhecido do Ally
    ranked = []
    for d in devs:
        score = 0
        if d["product_id"] in ALLY_PIDS:
            score += 2
        if d.get("usage_page") == AURA_USAGE_PAGE:
            score += 3
        ranked.append((score, d))
    ranked.sort(key=lambda x: -x[0])
    return [d for s, d in ranked if s > 0]


def list_devices():
    return [
        {
            "vid": hex(d["vendor_id"]),
            "pid": hex(d["product_id"]),
            "usage_page": hex(d.get("usage_page", 0)),
            "usage": hex(d.get("usage", 0)),
            "path": d["path"].decode(errors="replace"),
            "product": d.get("product_string"),
        }
        for d in hid.enumerate(ASUS_VID)
    ]


def _packet(*payload):
    buf = bytearray(REPORT_LEN)
    buf[0] = REPORT_ID
    for i, b in enumerate(payload, start=1):
        buf[i] = b
    return bytes(buf)


def set_color(r: int, g: int, b: int, mode: int = 0, speed: int = 0xE1) -> dict:
    """
    Cor estática (mode=0) nos anéis dos analógicos.
    Modos do firmware: 0=estático, 1=breathing, 2=color cycle, 3=rainbow.
    speed (para modos animados): 0xE1 lento, 0xEB médio, 0xF5 rápido.
    """
    r, g, b = (max(0, min(255, int(v))) for v in (r, g, b))
    errors = []
    for d in _candidates():
        try:
            dev = hid.device()
            dev.open_path(d["path"])
            try:
                # B3: zona 0 (todas), modo, R, G, B, velocidade, direção
                dev.send_feature_report(_packet(0xB3, 0x00, mode, r, g, b, speed, 0x00))
                dev.send_feature_report(_packet(0xB5))  # set
                dev.send_feature_report(_packet(0xB4))  # apply
                return {
                    "ok": True,
                    "device": d.get("product_string"),
                    "pid": hex(d["product_id"]),
                    "rgb": [r, g, b],
                }
            finally:
                dev.close()
        except Exception as e:  # tenta a próxima interface
            errors.append(f"{hex(d['product_id'])}/{hex(d.get('usage_page', 0))}: {e}")
    return {
        "ok": False,
        "error": "Nenhuma interface HID do Ally aceitou o comando.",
        "details": errors,
        "hint": "Rode 'python ally_led.py --list' e me mande a saída.",
    }


if __name__ == "__main__":
    import json
    import sys

    if "--list" in sys.argv:
        print(json.dumps(list_devices(), indent=2))
    else:
        # teste rápido: vermelho
        print(json.dumps(set_color(255, 0, 0), indent=2))
