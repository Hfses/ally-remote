# Ally Remote

Controle remoto para o ASUS ROG Ally: um servidor Windows (Python/FastAPI) que roda no Ally e um aplicativo Android para controlá-lo pela rede local.

Este projeto foi movido do repositório Winlator-Ludashi para cá, pois é um projeto independente e não tem relação com o Winlator.

## Estrutura

| Pasta | Descrição |
|---|---|
| `ally-remote/` | Servidor Windows em Python (FastAPI + PyInstaller). Roda no ROG Ally. Inclui a interface web (PWA) em `static/`. |
| `ally-remote-app/` | Aplicativo Android (cliente nativo) que se conecta ao servidor. |

## Downloads

Os binários são gerados automaticamente pelo GitHub Actions a cada push na `main` e publicados na release **allyremote-latest**:

- **AllyRemote.exe** — servidor para Windows (ROG Ally). O Windows/SmartScreen pode avisar sobre "editor desconhecido"; clique em *Mais informações → Executar assim mesmo*.
- **AllyRemote.apk** — aplicativo Android.

## Como usar

1. Execute o `AllyRemote.exe` no ROG Ally (pede Administrador automaticamente — necessário para RAM, modo de desempenho e firewall).
2. Instale o `AllyRemote.apk` no celular (ou acesse a interface web pelo navegador no endereço mostrado pelo servidor).
3. Conecte o celular e o Ally à mesma rede Wi-Fi e siga as instruções na tela.

Guia completo do servidor: [`ally-remote/README.md`](ally-remote/README.md).
