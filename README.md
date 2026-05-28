# llm-knowledge-studio

`llm-knowledge-studio` is an experimental, local-first AI knowledge system. It
ingests Markdown notes, normalizes them into Spanish, extracts a small ontology
of concepts/authors/books/technologies/tensions, and generates an
Obsidian-compatible vault.

It is meant for people who want to turn scattered reading notes, transcripts,
and research fragments into a navigable second brain. It is not a database, a
vector-search product, a private hosted service, or a replacement for careful
source review.

## What It Generates

- `vault/` — the generated Obsidian vault
- `vault/conceptos/` — concept notes
- `vault/autores/` — author/thinker notes
- `vault/libros/` — book or historical idea notes
- `vault/tecnologias/` — technology/platform notes
- `vault/tensiones/` — tension notes such as `Velocidad vs Profundidad`
- `vault/Inicio.md` — dashboard for navigation
- `vault/indice_de_temas.md` — index by node type
- `vault/indice_de_fuentes.md` — source attribution index
- `outputs/` — generated content, answers, daily summaries, and lint reports
- `data/archivo/` — archived originals and normalized captures

Generated files may include text derived from your private notes. Do not commit
`data/`, `vault/`, `outputs/`, or `demo_workspace/` unless you have reviewed
the contents and intentionally want to publish them.

## Install

Requirements:

- Python 3.11+ recommended
- An OpenAI API key, an OpenAI-compatible local endpoint, or mock mode

```bash
git clone <repo-url>
cd llm-knowledge-studio
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

For a zero-cost local run, keep:

```bash
OPENAI_API_KEY=mock
```

For real generation, set:

```bash
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
```

For Ollama, LM Studio, or another OpenAI-compatible server:

```bash
OPENAI_API_KEY=local-placeholder
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3
```

The project uses `tomllib` on Python 3.11+. On Python 3.10, `tomli` is installed
from `requirements.txt`. If you see `tomllib / tomli not available`, install
dependencies or use Python 3.11+.

## Demo

The safest first run is the isolated demo:

```bash
python3 scripts/run_demo.py
```

This writes only to `demo_workspace/`, uses `examples/sample_docs/`, validates
the generated vault, and asks one example question. See [DEMO.md](DEMO.md).

## Basic Workflow

Add Markdown captures:

```bash
python3 scripts/ingest_file.py path/to/note.md
```

Run the pipeline:

```bash
python3 scripts/run_daily.py --verbose
```

Validate the vault:

```bash
python3 scripts/validate_vault.py
```

Ask a grounded question:

```bash
python3 scripts/ask.py "¿Qué tensión aparece entre velocidad y profundidad?"
```

Open `vault/` in Obsidian and start with `Inicio.md`.

## Command Reference

| Command | Purpose |
|---|---|
| `python3 scripts/ingest_file.py <file.md>` | Copy a Markdown file into `data/capturas/` |
| `python3 scripts/run_daily.py --verbose` | Normalize captures, build the vault, generate dashboards, archive processed captures |
| `python3 scripts/build_index.py` | Rebuild dashboards from existing vault entity notes |
| `python3 scripts/validate_vault.py` | Check for broken links, ghost nodes, short notes, and graph config issues |
| `python3 scripts/ask.py "<question>"` | Answer a question using retrieved vault notes |
| `python3 scripts/lint.py` | Write a structural lint report to `outputs/reports/wiki_health.md` |
| `python3 scripts/run_demo.py` | Run a mock demo in `demo_workspace/` |
| `python3 scripts/reset_demo.py` | Reset only `demo_workspace/` |

`scripts/compile_wiki.py` is kept for compatibility and delegates to
`scripts/run_daily.py`.

## Configuration

Defaults live in `config.toml`. Environment variables override the file.

Required or common variables:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | API key. Use `mock` for deterministic offline responses. |
| `LLM_MODEL` | Model name. Defaults to `gpt-4o-mini`. |
| `LLM_BASE_URL` | Optional OpenAI-compatible endpoint. |

Optional path overrides for demos/CI:

| Variable | Default |
|---|---|
| `LLMKS_CAPTURES_DIR` | `data/capturas` |
| `LLMKS_KNOWLEDGE_MAP_DIR` | `vault` |
| `LLMKS_OUTPUTS_DIR` | `outputs` |
| `LLMKS_ARCHIVE_ORIGINALS_DIR` | `data/archivo/originales` |
| `LLMKS_ARCHIVE_NORMALIZED_DIR` | `data/archivo/normalizado` |

## Repository Layout

```text
llm-knowledge-studio/
├── app/                  # Python library code
├── scripts/              # CLI entry points
├── prompts/              # LLM prompts
├── examples/sample_docs/ # Public demo input documents
├── tests/                # Minimal regression tests
├── config.toml           # Default configuration
├── .env.example          # Environment template
├── DEMO.md               # Demo instructions
└── README.md
```

Generated/user-local folders are intentionally gitignored:

```text
data/capturas/
data/archivo/
vault/
outputs/
demo_workspace/
backups/
```

## Reset Generated Data

For the demo only:

```bash
python3 scripts/reset_demo.py
```

For your real workspace, delete generated folders manually only after reviewing
that they contain no data you need:

```bash
rm -rf vault outputs data/archivo
mkdir -p data/capturas data/archivo vault outputs
```

## Safety and Privacy

This project runs locally, but LLM calls may send note content to the configured
API endpoint. Use `OPENAI_API_KEY=mock` for offline testing. Before publishing
or sharing a generated vault, review `vault/`, `outputs/`, and `data/archivo/`
for private names, quotes, URLs, or source text.

Keep `.env` private. Commit `.env.example`, not `.env`.

## Tests

Run the demo validation:

```bash
python3 scripts/run_demo.py
```

Run unit tests:

```bash
python3 -m unittest discover tests
```

## Known Limitations

- Spanish-first output; multilingual workflows are not fully designed.
- Retrieval is keyword-based, not vector search.
- There is no database or hosted UI.
- LLM output quality depends on the model and prompts.
- The ontology planner is intentionally small; large corpora may need batching.
- Generated Markdown can contain sensitive source-derived text.

## Roadmap

- Improve test coverage for ingestion, validation, retrieval, and config.
- Add safer cleanup commands with confirmation.
- Add richer docs for prompt customization.
- Add optional screenshots for the generated Obsidian graph.
- Explore multilingual configuration without breaking the Spanish-first path.

## Troubleshooting

`No hay nuevas capturas para procesar.`
: Add Markdown files to `data/capturas/` or use `scripts/ingest_file.py`.

`No LLM API key found.`
: Set `OPENAI_API_KEY=mock` for local testing or add a real key in `.env`.

`tomllib / tomli not available`
: Use Python 3.11+ or run `pip install -r requirements.txt`.

Validation reports broken links or ghost nodes.
: Re-run `python3 scripts/run_daily.py --verbose`, then `python3 scripts/validate_vault.py`.

Obsidian graph shows dashboard files.
: Run `python3 scripts/build_index.py`; it rewrites `.obsidian/graph.json`.
