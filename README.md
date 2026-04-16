# LLM Knowledge Studio

A CLI-first, markdown-first knowledge management tool.
Drop in raw Markdown notes → get a structured wiki, keyword Q&A, and repurposed content — all powered by an LLM.

No databases.  No web servers.  Just files.

---

## Five-minute quickstart

```bash
# 1. Clone & set up a virtual environment (Python 3.11+ recommended)
git clone <repo-url> && cd llm-knowledge-studio
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=mock  (zero-cost dry-run)
# or  OPENAI_API_KEY=sk-...             (real API)

# 3. Run the full pipeline
python scripts/ingest_file.py examples/sample_raw.md   # copies file to data/raw/
python scripts/compile_wiki.py                          # builds wiki pages in data/wiki/
python scripts/build_index.py                           # indexes topics + open questions
python scripts/ask.py "What is retrieval augmented generation?"
python scripts/lint.py                                  # quality-checks the wiki
```

That's it.  All outputs land in `data/`.

---

## Folder layout

```
llm-knowledge-studio/
├── config.toml          ← paths, model name, topic seeds, quality thresholds
├── .env                 ← your API key (gitignored)
├── app/                 ← library modules (import these, don't run directly)
│   ├── config.py        ← config loader (reads config.toml + env vars)
│   ├── llm_client.py    ← OpenAI-compatible LLM wrapper (mock-safe)
│   ├── file_utils.py    ← I/O helpers
│   ├── retriever.py     ← keyword retrieval (stop-word filtered, ranked)
│   ├── summarizer.py    ← summarize raw notes
│   ├── wiki_compiler.py ← compile raw notes → structured wiki pages
│   ├── wiki_linter.py   ← structural quality checks on wiki pages
│   ├── qa_engine.py     ← answer questions from wiki context
│   └── content_generator.py ← repurpose wiki content (IG, X thread, insight)
├── scripts/             ← CLI entry-points (run these directly)
│   ├── ingest_file.py
│   ├── summarize.py
│   ├── compile_wiki.py
│   ├── build_index.py
│   ├── ask.py
│   ├── generate_content.py
│   ├── lint.py
│   └── test_llm.py
├── prompts/             ← plain-text LLM system prompts (edit freely)
├── data/
│   ├── raw/             ← your raw Markdown notes (input)
│   ├── wiki/            ← compiled wiki pages (auto-generated)
│   └── outputs/
│       ├── answers/     ← saved Q&A responses
│       ├── content/     ← generated content pieces
│       ├── summaries/   ← file summaries
│       └── reports/     ← wiki health reports
└── examples/            ← sample files to try the pipeline
```

---

## Scripts reference

| Script | What it does |
|---|---|
| `ingest_file.py <path> [--name]` | Copy a Markdown file into `data/raw/` |
| `summarize.py [--source <file>]` | Summarize raw notes → `data/outputs/summaries/` |
| `compile_wiki.py [--source <file>]` | Compile notes → wiki pages in `data/wiki/` |
| `build_index.py` | Build topic/source index + open questions |
| `ask.py "<question>"` | Answer a question from wiki context |
| `generate_content.py "<topic>"` | Generate IG reel, X thread, and insight |
| `lint.py` | Check wiki pages for missing sections/empty content |
| `test_llm.py` | Smoke-test the LLM connection |

---

## Configuration

`config.toml` is the single source of truth for all settings:

```toml
[paths]
raw_dir     = "data/raw"
wiki_dir    = "data/wiki"
outputs_dir = "data/outputs"

[llm]
model       = "gpt-4o-mini"
timeout     = 30
max_retries = 2

[topics]
# Files whose H1 heading matches a seed label skip the LLM topic call.
seed_labels = ["Artificial Intelligence", "Productivity", ...]

[wiki]
required_sections = ["## Definition", "## Key Ideas", ...]
min_page_words    = 30
max_context_chars = 4000
```

Environment variables always override `config.toml`:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | API key (`mock` for dry-run) |
| `LLM_MODEL` | Model name override |
| `LLM_BASE_URL` | Base URL for OpenAI-compatible proxies / local servers |

---

## Using a local model (Ollama, LM Studio, etc.)

```bash
# In .env:
OPENAI_API_KEY=ollama   # any non-empty non-"mock" string
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3
```

The client is a thin wrapper around `openai.OpenAI`, which is compatible
with any server that implements the OpenAI chat-completions API.

---

## Topic grouping

Files are grouped into wiki topics using a two-tier strategy:

1. **Seed label match** (deterministic) — if the file's `# Heading` matches
   an entry in `config.toml [topics] seed_labels`, that label is used with
   no LLM call.
2. **LLM fallback** — for unmatched files, the LLM returns a 1-3 word label
   which is normalised (title-cased, truncated) before grouping.

Add domain-specific labels to `seed_labels` to make grouping stable and
free for your most common topics.

---

## Mock mode (no API key required)

Set `OPENAI_API_KEY=mock` in `.env` or the shell.  All LLM calls return
deterministic stub responses so you can validate the full pipeline locally
without spending tokens.

---

## Adding your own notes

```bash
python scripts/ingest_file.py ~/notes/my-topic.md
python scripts/compile_wiki.py --source data/raw/my-topic.md
python scripts/build_index.py
python scripts/ask.py "What is my topic about?"
```
