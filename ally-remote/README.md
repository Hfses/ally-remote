# Ally Remote 🎮📱

Controle o **ROG Ally (Z1 / Z1 Extreme)** pelo celular, na sua rede Wi-Fi:

| Função | O que faz |
|---|---|
| 🖱️ **Mouse** | Touchpad no celular com gestos (mover, clicar, arrastar, rolar) |
| ⌨️ **Teclado** | Digite textos e use teclas especiais (ESC, TAB, WIN, setas, ALT+F4…) |
| 🔊 **Mídia / Volume** | Play/pause, faixa anterior/próxima, volume +/−, mudo |
| 🧹 **Liberar RAM** | Apara working sets + limpa a standby list (como RAMMap/ISLC) |
| ⚡ **Modo de desempenho** | Silent / Performance / Turbo — direto no firmware ASUS (controla a fan) |
| 💡 **LEDs dos analógicos** | Cor, efeitos (estático, pulso, ciclo, arco-íris) e velocidade |
| 🔋 **Bateria** | Porcentagem e status de carga no topo do app |
| ⏻ **Energia** | Suspender, reiniciar, desligar (com confirmação) e cancelar |
| 🖥️ **Espelhar a tela (jogar)** | Vê a tela do Ally no celular e joga por ela (toque = clique) |
| ☀️ **Brilho / economia** | Ajusta o brilho, "tela mínima" e desligar a tela sem parar o jogo |

**Arquitetura:** um servidor Python (FastAPI + WebSocket) roda **no Ally**;
o celular abre uma página que vira **app de tela cheia (PWA)**. Sem cloud,
sem conta, sem instalar nada no celular. Tudo fica na sua rede.

---

## 1. Baixar os aplicativos

O GitHub compila os dois automaticamente a cada atualização deste código
(GitHub Actions):

1. Vá em **[Releases → allyremote-latest](../../releases/tag/allyremote-latest)** e baixe:
   - **`AllyRemote.exe`** → roda **no Ally** (é o servidor);
   - **`AllyRemote.apk`** → aplicativo **para o celular Android** (opcional —
     dá para usar só pelo navegador também, ver seção 3).
2. Se ainda não existir release: vá na aba **Actions** do repositório,
   clique em **"Ally Remote — gerar EXE (Windows)"** → **Run workflow**
   (se o GitHub perguntar, habilite os workflows primeiro — é um clique).
   Em ~5 minutos a release aparece com o `.exe`.

> ⚠️ **Aviso do SmartScreen:** por ser um exe novo sem assinatura digital,
> o Windows pode mostrar "editor desconhecido". Clique em
> **Mais informações → Executar assim mesmo**. O exe é gerado de forma
> transparente pelo próprio GitHub a partir deste código-fonte.

## 2. Instalar no ROG Ally (modo desktop)

1. Copie o `AllyRemote.exe` para qualquer pasta do Ally (ex.: Área de Trabalho).
2. Dê **dois toques** nele. Ele vai pedir **Administrador** — aceite
   (necessário para liberar RAM, trocar modo de desempenho e liberar o firewall).
3. Uma janela preta abre mostrando:
   - o **endereço** para abrir no celular (ex.: `http://192.168.1.42:8765`);
   - um **QR code** — aponte a câmera do celular e pronto.
4. **Deixe essa janela aberta** enquanto usa o app (minimizada funciona).

O programa cria sozinho a regra de firewall (porta 8765/TCP, rede privada)
na primeira execução.

## 3. No celular — duas opções

### Opção A: aplicativo Android (AllyRemote.apk)

1. Baixe o `AllyRemote.apk` no celular e instale (o Android vai pedir para
   permitir "fontes desconhecidas" — permita; o APK é gerado por este
   repositório no GitHub).
   > ⚠️ **Atualizando de uma versão anterior?** Se aparecer "app não instalado",
   > **desinstale o Ally Remote antigo primeiro** e instale de novo (só desta
   > vez — a chave de assinatura passou a ser fixa, então as próximas
   > atualizações instalam por cima normalmente).
2. Abra o app **conectado no mesmo Wi-Fi do Ally** e toque em
   **"🔍 Procurar o Ally na rede"** — ele encontra o servidor sozinho
   (ou digite o IP mostrado na janela do AllyRemote no Ally).
3. O IP fica salvo: nas próximas vezes o app conecta direto.
4. Ao **minimizar e voltar**, o app **reconecta sozinho** (não trava mais).
   Para trocar de Ally, toque no **⟲** no canto superior direito ou no botão
   **voltar** do Android — volta à tela de conexão.

### Opção B: navegador (funciona em iPhone também)

1. Conectado no **mesmo Wi-Fi** do Ally, escaneie o QR code (ou digite o
   endereço no navegador).
2. Menu do navegador → **"Adicionar à tela inicial"** → vira um app de tela
   cheia com ícone próprio.

Nas duas opções, a bolinha verde no topo indica **conectado**. Se a conexão
cair (tela do celular apagou etc.), o app **reconecta sozinho**.

## 4. Como usar cada aba

### 🖱️ MOUSE
| Gesto | Ação |
|---|---|
| Arrastar 1 dedo | mover o cursor |
| Toque 1 dedo | clique esquerdo |
| Toque com 2 dedos | clique direito |
| Arrastar com 2 dedos / barra SCROLL | rolagem |
| Toque duplo e arrastar | segurar e arrastar (drag) |

### ⌨️ TECLADO
- Digite no campo e toque **ENVIAR** (ou Enter) — o texto sai no Ally.
- Teclas especiais: ESC, TAB, WIN, DEL, setas, ENTER, BACKSPACE.
- Linha de **mídia**: anterior · play/pause · próxima · volume − · mudo · volume +.
- **ALT+F4** fecha a janela/jogo ativo no Ally.

### ⚙️ SISTEMA
- **MEMÓRIA RAM** — barra mostra o uso atual; **LIBERAR RAM** mostra quantos
  MB foram liberados. Útil quando um jogo reclama de memória.
- **DESEMPENHO / FAN** — Silent / Performance / Turbo, com RPM da fan ao lado.
  Usa o mesmo caminho do G-Helper/Armoury Crate (driver ATKACPI).
- **LED · ANALÓGICOS** — escolha uma cor pronta, uma cor personalizada
  (bolinha colorida), o efeito (estático, pulso, ciclo de cores, arco-íris)
  e a velocidade da animação.
- **ENERGIA** — bateria em tempo real + Suspender / Reiniciar / Desligar
  (pedem confirmação; desligar/reiniciar têm 5 s de tolerância — dá para
  abortar com **CANCELAR**).

### 🖥️ TELA (espelhar e jogar pelo celular)
- Toque em **INICIAR ESPELHAMENTO** para ver a tela do Ally no celular.
- **TOQUE = CLIQUE**: tocar na imagem move o cursor para aquele ponto e clica —
  ótimo para desktop, menus, emuladores, RPG e estratégia.
- **MODO TOUCHPAD**: arrastar move a mira de forma relativa — melhor para jogos
  de câmera/FPS.
- Qualidade **LEVE / MÉDIA / NÍTIDA** (menor = menos atraso e menos Wi-Fi).
- Honestidade: numa rede Wi-Fi 5 GHz boa isso roda bem para a maioria dos jogos.
  Para FPS competitivo com o mínimo de atraso, o ideal ainda é **Moonlight +
  Sunshine** (usa o encoder de vídeo do próprio chip do Ally). Este espelhamento
  ganha em não precisar instalar nada no celular e já vir integrado.

### ☀️ BRILHO / ECONOMIA (apagar a tela sem parar o jogo)
Está jogando pelo celular e quer economizar a bateria do Ally?
- **TELA MÍNIMA** (brilho 0): o painel fica apagado, **mas o jogo continua e o
  espelhamento continua funcionando** — e tocar no Ally não "acorda" nada. É a
  melhor opção enquanto você joga pelo celular.
- **DESLIGAR TELA**: apaga o monitor de vez (economia um pouco maior), porém o
  espelhamento pode pausar e a tela religa ao tocar no Ally. Use quando **não**
  estiver espelhando.

## 5. PIN (recomendado se o Wi-Fi é compartilhado)

Sem PIN, **qualquer aparelho na sua rede pode controlar o Ally** — inclusive
digitar comandos como Administrador. Para exigir um PIN, crie um atalho ou
rode pelo terminal:

```
AllyRemote.exe --pin 4321
```

O celular vai pedir o PIN ao conectar. O tráfego é HTTP puro (sem
criptografia) em ambos os casos; **não exponha a porta 8765 para fora da sua
rede/roteador**.

## 6. ROG Ally Z1 Extreme — observações

- O Z1 Extreme (RC71L) usa **os mesmos endpoints de firmware** (ATKACPI
  `0x00120075` para modo de desempenho e `0x00110013` para a fan) e o mesmo
  dispositivo HID de LED (VID `0x0B05`, PID `0x1ABE`) que este projeto usa —
  são os IDs do G-Helper, Handheld Companion e do driver Linux `asus-wmi`.
- Se o **Armoury Crate SE** estiver aberto, ele pode "brigar" com a troca de
  modo/cor e reverter o que você definiu. Se isso acontecer, feche o Armoury
  Crate SE (ou pare os serviços ASUS) enquanto usa o Ally Remote.
- Para o LED: se a cor "voltar sozinha", desative também a **Iluminação
  Dinâmica** do Windows 11 (Configurações → Personalização → Iluminação
  dinâmica).

## 7. Checklist de teste (primeira vez)

1. **Mouse**: arraste no touchpad → cursor mexe. Toque → clique.
2. **Teclado**: abra o Bloco de Notas no Ally e envie um texto.
3. **RAM**: toque LIBERAR RAM → o card mostra os MB liberados. Se aparecer
   "standby FALHOU", o servidor não está como Administrador.
4. **Modo**: toque TURBO → a fan acelera em segundos e o chip FAN sobe o RPM.
5. **LED**: toque numa cor → os anéis dos analógicos mudam.
6. **Bateria**: o chip BAT no topo deve bater com o % do Windows.
7. **Energia**: teste SUSPENDER (acorde no botão de energia do Ally).

## 8. O que foi testado de verdade

- ✅ Servidor, protocolo WebSocket e interface foram testados de ponta a
  ponta em **modo mock** (fora do Windows): conexão, PIN, mouse/teclado/
  RAM/modo/LED/energia chegam corretos ao servidor e as respostas voltam à UI.
- ❌ **Depende do seu hardware** (valide com o checklist): injeção real de
  mouse/teclado (pynput), liberação de RAM, chamadas ATKACPI e pacotes HID
  do LED. As chamadas seguem exatamente o que G-Helper/Handheld Companion e
  o driver `asus-wmi` do Linux fazem.

## 9. Solução de problemas

| Problema | Solução |
|---|---|
| Página não abre no celular | Mesmo Wi-Fi? Rede de "convidado" isola aparelhos. Firewall: porta 8765/TCP em rede privada. |
| "ATKACPI indisponível" | Rode como Administrador; confira se o driver *ASUS System Control Interface* está instalado (vem de fábrica). |
| Modo de desempenho volta sozinho | O Armoury Crate SE está revertendo — feche-o ou pare os serviços ASUS. |
| LED não muda / volta sozinho | Feche o Armoury Crate SE e desative a Iluminação Dinâmica do Windows. Se persistir: `AllyRemote.exe` numa pasta, rode `python ally_led.py --list` (com Python) e abra uma issue com a saída. |
| "standby FALHOU" ao liberar RAM | O servidor não está rodando como Administrador. |
| SmartScreen bloqueia o exe | Mais informações → Executar assim mesmo. |

## 10. Rodar/compilar do código-fonte (opcional)

```bat
:: rodar direto (Python 3.11+, terminal como Admin):
cd ally-remote
pip install -r requirements.txt
python server.py

:: gerar o AllyRemote.exe localmente:
build.bat
```

Fora do Windows o servidor roda em **modo mock** (imprime os comandos em vez
de executá-los) — útil para mexer na interface.

## Estrutura do código

```
ally-remote/
├── server.py        # servidor FastAPI + WebSocket (roda no Ally)
├── ally_acpi.py     # firmware ASUS via driver ATKACPI (modo/fan)
├── ally_led.py      # LEDs dos analógicos via HID (protocolo 0x5D)
├── ram.py           # EmptyWorkingSet + purge da standby list
├── power.py         # bateria + suspender/desligar/reiniciar
├── static/          # interface do celular (PWA)
├── build.bat        # compilar o exe localmente
└── requirements.txt
```
