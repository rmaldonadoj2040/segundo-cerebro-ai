# Demo workflow

This demo runs without an API key and does not touch your real notes. It writes
everything to `demo_workspace/`, which is gitignored.

## Run the demo

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/run_demo.py
```

The script will:

- reset `demo_workspace/`
- copy `examples/sample_docs/*.md` into `demo_workspace/capturas/`
- run the daily pipeline with `OPENAI_API_KEY=mock`
- generate a sample Obsidian vault in `demo_workspace/vault/`
- validate the generated vault
- ask one example question against the generated knowledge base
  (`demo_workspace/outputs/respuestas/`)

## Useful follow-up commands

```bash
python3 scripts/validate_vault.py --vault demo_workspace/vault
python3 scripts/ask.py "¿Qué tensión aparece entre velocidad y profundidad?"
python3 scripts/reset_demo.py
```

To ask against the demo vault after `run_demo.py`, set the same path overrides:

```bash
export OPENAI_API_KEY=mock
export LLMKS_KNOWLEDGE_MAP_DIR=demo_workspace/vault
export LLMKS_OUTPUTS_DIR=demo_workspace/outputs
python3 scripts/ask.py "¿Qué relación hay entre memoria externa y criterio?"
```

## Open in Obsidian

Open Obsidian and choose `demo_workspace/vault/` as the vault folder. Start at
`Inicio.md`, then open Graph View.
