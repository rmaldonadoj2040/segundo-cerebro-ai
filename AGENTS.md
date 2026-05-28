# llm-knowledge-studio Project Documentation

## Project Overview

**llm-knowledge-studio** is a markdown-to-wiki compilation system that transforms raw markdown files into a structured, navigable knowledge base optimized for Spanish-speaking users in [Obsidian](https://obsidian.md/).

**Tech Stack:**
- Python 3.11+ (tomllib support for TOML)
- OpenAI API (gpt-4o-mini default, configurable)
- Markdown + YAML frontmatter
- No databases, no vector search - purely markdown-based

## Architecture

### Core Components

1. **app/config.py**
   - Loads configuration from `config.toml`
   - Supports environment variable overrides
   - Manages paths, LLM settings, and generation defaults

2. **app/wiki_compiler.py**
   - Assigns topics to raw markdown files using LLM extraction
   - Compiles topics into structured wiki notes
   - Generates YAML frontmatter for all notes
   - Auto-generates tension and insight notes from compiled concepts
   - Saves notes to type-specific directories

3. **app/file_utils.py**
   - File I/O helpers (UTF-8 with latin-1 fallback)
   - Directory initialization
   - Markdown file listing
   - Slug generation for filenames

4. **app/llm_client.py**
   - OpenAI-compatible LLM abstraction
   - Supports mock mode via `OPENAI_API_KEY=mock`
   - Configurable base_url for alternative providers

### Scripts

1. **scripts/compile_wiki.py**
   - Main compilation entry point
   - Calls topic extraction → compilation → index building
   - Now includes auto-generation of tensions and insights

2. **scripts/build_index.py**
   - Organizes notes by type (conceptos, tensiones, insights, preguntas)
   - Generates Spanish-language indices
   - Creates source attribution mapping
   - Extracts open questions from content

3. **scripts/run_daily.py**
   - Daily pipeline orchestrator
   - Processes inbox → compiles → indexes → generates insights
   - Logs each run with timestamp

### Data Structure

```
data/
├── raw/                    # Raw markdown source files
├── inbox/                  # Temporary staging for new files
├── wiki/                   # Compiled wiki output
│   ├── conceptos/         # Core concept notes
│   ├── tensiones/         # Auto-generated tension notes
│   ├── insights/          # Auto-generated insight notes
│   ├── preguntas/         # Question notes
│   ├── topics_index.md    # Master index by type
│   ├── sources_index.md   # Source attribution
│   ├── insights_summary.md # Insight listing
│   └── open_questions.md  # Generated questions
├── outputs/
│   ├── summaries/         # LLM-generated summaries
│   └── runs/              # Daily run logs
```

## Recent Improvements (May 14, 2026)

### Spanish-First Implementation ✅

1. **Prompt Updates**
   - Updated `prompts/compile_concept.md` to generate Spanish content
   - All section headings are in Spanish:
     - "## Idea central" (instead of "Definition")
     - "## Por qué importa" (instead of "Key Ideas")
     - "## Cómo funciona" (instead of "How it Works")
     - "## Tensiones relacionadas" (instead of "Tensions")
     - "## Fuentes" (instead of "Sources")

2. **YAML Frontmatter**
   - Every generated note now includes:
   ```yaml
   ---
   type: concepto | tensión | insight | pregunta | output
   audience: spanish
   status: active
   publishable: yes/no
   ---
   ```
   - Enabled by `_generate_frontmatter()` in wiki_compiler.py

3. **Note Type System**
   - **conceptos/** — Core concepts with full structure
   - **tensiones/** — Auto-generated tradeoffs/contradictions
   - **insights/** — Auto-generated profound observations
   - **preguntas/** — Auto-generated open questions
   - **outputs/** — Special outputs/analyses

4. **Automatic Tension Generation**
   - New function: `generate_tensions_from_concepts()`
   - Analyzes compiled concepts to identify 5-10 tensions
   - Examples: "Velocidad vs Comprensión", "Automatización vs Criterio"
   - Saves as separate notes in `tensiones/` directory

5. **Automatic Insight Generation**
   - New function: `generate_insights_from_concepts()`
   - Extracts 5-8 strong, surprising observations
   - Examples: "La IA optimiza conveniencia, no aprendizaje"
   - Saves as separate notes in `insights/` directory

6. **Enhanced Indexing**
   - **topics_index.md** — Organized by type (Conceptos → Tensiones → Insights)
   - **sources_index.md** — Maps source files to generated notes
   - **insights_summary.md** — Quick list of all insights
   - **open_questions.md** — Generated questions for exploration
   - All indices include wikilinks for Obsidian navigation

7. **Wikilink Support**
   - All generated notes include `[[Concepto]]` style wikilinks
   - Enables Obsidian graph visualization
   - Allows interactive knowledge navigation

8. **Configuration Enhancements**
   - New config section: `[generation]`
     - `language = "Spanish"`
     - `audience = "spanish"`
     - `status = "active"`
   - New path configs for type-specific directories
   - Updated `required_sections` to Spanish

### Code Changes

**app/wiki_compiler.py**
- Added `_generate_frontmatter()` function
- Added `_extract_title_from_content()` function
- Updated `compile_topic()` to accept `note_type` parameter
- Updated output paths to use type-specific directories
- Added `generate_tensions_from_concepts()` function
- Added `generate_insights_from_concepts()` function

**app/config.py**
- Added `generation_language`, `generation_audience`, `generation_status` fields
- Added paths for type-specific directories

**app/file_utils.py**
- Updated `ensure_project_dirs()` to create type-specific directories

**scripts/compile_wiki.py**
- Refactored to use type-specific directories
- Now calls `generate_tensions_from_concepts()` and `generate_insights_from_concepts()`
- Logs all generated notes

**scripts/build_index.py**
- Complete rewrite to handle type organization
- New functions for extracting frontmatter metadata
- Spanish-language index generation
- Support for Spanish section headers ("Fuentes" and "Sources")

**app/llm_client.py**
- Updated mock mode to return Spanish content
- Improved mock detection for different prompt types

## Configuration

### config.toml

Key settings:
```toml
[llm]
model = "gpt-4o-mini"    # Change for different LLM

[generation]
language = "Spanish"      # Default content language
audience = "spanish"      # Target audience
status = "active"         # Default note status

[paths]
conceptos_dir = "data/wiki/conceptos"
tensiones_dir = "data/wiki/tensiones"
insights_dir = "data/wiki/insights"
preguntas_dir = "data/wiki/preguntas"

[wiki]
required_sections = [
    "## Idea central",
    "## Por qué importa",
    "## Cómo funciona",
    "## Tensiones relacionadas",
    "## Conexiones con otros conceptos",
    "## Fuentes",
]
```

### Environment Variables

```bash
# LLM Configuration
export OPENAI_API_KEY="sk-..."      # Required for real API calls
export LLM_MODEL="gpt-4o"           # Override default model
export LLM_BASE_URL="https://..."   # For OpenAI-compatible endpoints

# Test Mode
export OPENAI_API_KEY=mock          # Use mock responses (no API cost)
```

## Workflow

### Add Content
```bash
cp my-document.md data/inbox/
# or
cp my-document.md data/raw/
```

### Compile & Index
```bash
# Single execution
python3 scripts/compile_wiki.py
python3 scripts/build_index.py

# Or daily pipeline
python3 scripts/run_daily.py
```

### Verify Results
```bash
# Check conceptos/, tensiones/, insights/ directories
# All notes should have frontmatter and Spanish headings
# topics_index.md should list all notes organized by type
```

### Open in Obsidian
1. Create new vault pointing to `data/wiki/`
2. Open `topics_index.md` as starting point
3. Click wikilinks to navigate
4. Use Graph View to see relationships

## Testing

### With Mock LLM (No API Cost)
```bash
export OPENAI_API_KEY=mock
python3 scripts/compile_wiki.py
python3 scripts/build_index.py
```

### Verification Script
```bash
python3 << 'EOF'
from pathlib import Path
from app.config import get as cfg
from app.file_utils import list_markdown_files, read_text

c = cfg()

# Check frontmatter
for note_dir in [c.conceptos_dir, c.tensiones_dir, c.insights_dir]:
    for note in list_markdown_files(note_dir):
        content = read_text(note)
        assert content.startswith("---\ntype:"), f"Missing frontmatter: {note}"
        assert "[[" in content or note.parent.name == "preguntas", f"No wikilinks: {note}"

print("✅ All notes properly formatted")
EOF
```

## Known Limitations & Future Work

### Current Limitations
- No full-text search (use Obsidian's built-in search)
- No database (everything is markdown files)
- No vector embeddings (relies on LLM for concept extraction)
- Spanish-only content generation (no language switching)

### Potential Improvements
- Add multilingual support
- Implement note versioning
- Add automatic backlink generation
- Create Obsidian plugins for special views
- Add batch processing for large content sets

## Debugging

### Mock mode not returning Spanish content
- Check that `OPENAI_API_KEY=mock` is set before import
- Verify `app/llm_client.py` has updated mock responses

### Frontmatter not appearing in notes
- Check `_generate_frontmatter()` is being called in `compile_topic()`
- Verify `write_text()` is saving the frontmatter + content correctly

### Wikilinks not working in Obsidian
- Ensure wikilinks use `[[Exact Title Name]]` format
- Check that target note titles match the link text
- Use Obsidian's "Link Unlinked Mentions" feature to auto-link

### Missing Spanish section headers
- Verify `prompts/compile_concept.md` uses Spanish headers
- Check that mock response includes Spanish sections
- Ensure LLM model supports Spanish output

## Code Style

- Python 3.11+ type hints
- No external dependencies beyond `openai`
- Markdown-first approach (no special formats)
- Spanish documentation and section headers
- Descriptive variable names in English
- Minimal comments (code is self-documenting)

## Contact & Contributions

Questions about the Spanish wiki system? Check:
1. `SPANISH_WIKI_GUIDE.md` — User guide
2. `AGENTS.md` (this file) — Technical documentation
3. `config.toml` — Configuration reference
4. `prompts/compile_concept.md` — Content generation template
