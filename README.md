# WA Chat Reader

Programa desktop em Python (customtkinter) que lê conversas exportadas do WhatsApp (iOS/Android, pasta ou .zip) e gera um arquivo HTML autocontido.

## Como usar

```bash
pip install -r requirements.txt
python main.py
```

## Como testar

```bash
pytest
```

## Format exportados

- iOS: `[12/03/2024, 14:35:22] Nome: texto`
- Android 24h: `12/03/2024 14:35 - Nome: texto`
- Android 12h: `3/12/24, 2:35 PM - Nome: texto`
- Android 2 dígitos: `12/03/24 14:35 - Nome: texto`
- Separadores de data: `/`, `.`, `-`

Se encontrar formato real não reconhecido, adicione como fixture em `tests/fixtures/` e atualize `parser.py`.

## Funcionalidades

- Dois modos: Rápido (links relativos) e Portátil (Base64 em lotes)
- Barra de progresso e thread segura
- Mensagens multilinha preservadas
- Texto escapado (sem injeção HTML)
- Busca e tema no HTML gerado
