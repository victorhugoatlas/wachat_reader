# AGENTS.md — WA Chat Reader

## O que é o projeto

Programa desktop em Python (interface customtkinter) que lê uma conversa de WhatsApp exportada (pasta ou `.zip`, iOS ou Android) e gera **um único arquivo HTML** que reconstrói o chat com layout próximo ao do WhatsApp: fotos, vídeos, áudios, figurinhas e documentos funcionando dentro da conversa.

Prioridades, em ordem: **velocidade**, **layout excelente**, **código simples e limpo**.

## Comandos

```bash
pip install -r requirements.txt   # só customtkinter (+ pytest para testes)
python main.py                    # abre a interface
pytest                            # roda todos os testes
```

## Estrutura

```
wa_reader/
  __init__.py
  parser.py     # detecta o formato e gera objetos Message (generator, uma única leitura)
  media.py      # tipo de mídia, MIME, Base64, links relativos, extração segura de zip
  renderer.py   # gera o HTML em streaming (CSS e JS embutidos)
  gui.py        # interface customtkinter (nenhuma lógica de parsing aqui)
main.py         # ponto de entrada: from wa_reader.gui import run
tests/
  fixtures/     # conversas SINTÉTICAS (nunca dados reais)
  test_parser.py
  test_renderer.py
```

Cada arquivo tem uma responsabilidade. Não misture parsing, renderização e interface.

## Regras de código

- Python 3.10+. Única dependência externa: `customtkinter`. Todo o resto usa biblioteca padrão. `pytest` só para testes.
- Interface do usuário **sempre em português**. Tema escuro.
- Funções pequenas, `dataclass` para dados, type hints, nomes claros em português ou inglês (escolha um padrão e mantenha). Comentários só onde a lógica não é óbvia.
- Sem abstrações "para o futuro", sem camadas ou classes desnecessárias.
- Multiplataforma: nunca chamar `os.startfile` direto. Usar o helper que escolhe `os.startfile` (Windows), `open` (macOS) ou `xdg-open` (Linux).
- Erros são registrados com `logging` e mostrados ao usuário em `messagebox` claro. Nada de `except: pass` silencioso.

## Regras de interface e threads

- Tkinter não é thread-safe. A thread de trabalho **nunca toca em widgets**. Toda atualização de interface (progresso, botões, messagebox) vai por `self.after(0, ...)`.
- Botões ficam desabilitados durante o processamento e são reabilitados sempre ao fim, inclusive em caso de erro.
- A janela nunca pode travar.

## Regras do parser

- Ler o arquivo **uma única vez**, em streaming (generator), `encoding="utf-8-sig"`.
- Remover marcas invisíveis (`\u200e`, `\u200f`, `\u202a`–`\u202e`, `\ufeff`) antes de casar o cabeçalho.
- Linha sem cabeçalho é continuação da mensagem anterior (concatenar com `\n`).
- Mensagem de sistema: `author=None`, `kind="system"`.
- Dia/mês ambíguo: assumir dd/mm (padrão Brasil). Ano de 2 dígitos vira 20xx.
- Se aparecer um formato que o parser não reconhece, **não adivinhe**: adicione o caso como fixture e um novo padrão de cabeçalho.

## Formatos suportados

| Origem | Exemplo |
|---|---|
| iOS | `[12/03/2024, 14:35:22] Nome: texto` |
| Android 24h | `12/03/2024 14:35 - Nome: texto` |
| Android 12h | `3/12/24, 2:35 PM - Nome: texto` (AM/PM, `a. m./p. m.`, espaço fino `\u202f`) |
| Android, ano de 2 dígitos | `12/03/24 14:35 - Nome: texto` |

Separadores de data aceitos: `/`, `.`, `-`.

Anexos: `<anexado: ARQ>`, `<attached: ARQ>`, `ARQ (arquivo anexado)`, `ARQ (file attached)`, `ARQ (archivo adjunto)`.
Mídia omitida: `<Mídia oculta>`, `<Media omitted>`, `<Multimedia omitido>`.
Apagadas e editadas: reconhecidas em português e inglês.

## Regras de mídia

- **Modo Rápido**: caminho **relativo** ao HTML, com `urllib.parse.quote`. Nunca `file:///` absoluto.
- **Modo Portátil**: Base64 `data:` URI, convertido em lotes (~32 arquivos) com `ThreadPoolExecutor.map`, gravado no HTML assim que fica pronto. **Sem cache global em RAM.**
- Falha em um arquivo não derruba o processo: mostrar placeholder "arquivo indisponível".
- Cada arquivo de mídia é processado uma única vez.
- MIME corrigido para `.opus` (audio/ogg), `.m4a` (audio/mp4), `.webp` (image/webp), `.mov` (video/quicktime).
- Zip: validar cada caminho na extração (proteção contra zip-slip).

## Regras do HTML gerado

- Autocontido, **sem dependências externas**, escrito em streaming (um `write` por bloco).
- Escapar **todo** texto (mensagens, autores, nomes de arquivo) com `html.escape` **antes** de aplicar a formatação do WhatsApp.
- `loading="lazy"` em imagens, `preload="none"` em vídeo e áudio.
- Paginação sob demanda (~500 mensagens por página) para chats grandes.
- JS puro, sem bibliotecas.

## Testes

- Fixtures **sempre sintéticas e anonimizadas**. Nunca commitar conversas reais.
- Cobertura mínima: iOS, Android 24h, Android 12h, ano de 2 dígitos, grupo, texto com HTML/`&`/formatação, zip e zip-slip.
- Ao corrigir um bug de formato, primeiro crie a fixture que reproduz o problema.

## Fluxo de trabalho

- Trabalhar em etapas pequenas, um commit Git ao fim de cada etapa.
- Rodar `pytest` antes de cada commit.
- Não adicionar dependências nem funcionalidades não pedidas.