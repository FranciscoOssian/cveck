# Development & Contribution Guide

## Repository Structure

```text
cveck/
├── doc/                            # USER_PROFILE.md, GAPS.md, gaps.json
├── output/                         # Generated .pdf, .typ, .txt, JSON artifacts
├── src/
│   ├── core/                       # Pure Business Logic & Domain
│   │   ├── assets/                 # Prompts (Markdown) & Typst templates
│   │   ├── models/                 # Pure Pydantic domain models
│   │   ├── services/               # Stateless services (ATS, Typst, Parser, Backlog)
│   │   ├── use_cases/              # Granular domain use cases
│   │   ├── workflow/               # Declarative workflow schema and evaluators
│   │   ├── context.py              # User profile & template loader
│   │   ├── paths.py                # Dynamic root and directory resolution
│   │   └── workflow.yaml           # Declarative pipeline configuration
│   ├── adapters/                   # Execution Adapters (Adapter Pattern)
│   │   ├── langgraph/              # LangGraph adapter (builder, nodes, router, state)
│   │   └── mcp/                    # Model Context Protocol server adapter
│   └── cli/                        # Interactive Rich CLI application
│       ├── locales/                # GNU gettext catalogs (.pot, .po, .mo)
│       ├── i18n.py                 # Runtime localization manager
│       ├── ui.py                   # Rich rendering and interactive menus
│       └── main.py                 # Typer entrypoint (CLI & MCP commands)
├── babel.cfg                       # Babel extraction configuration (src/cli/**.py)
└── pyproject.toml                  # Project metadata and dependencies
```

---

## Working with Internationalization (i18n)

CVECK uses GNU `gettext` via Babel. All translation catalogs reside in `src/cli/locales/`:

```bash
# 1. Extract translatable strings from CLI source
pybabel extract -F babel.cfg -o src/cli/locales/cveck.pot .

# 2. Update existing catalogs (pt_BR, zh, en)
pybabel update -i src/cli/locales/cveck.pot -d src/cli/locales -D cveck

# 3. Compile catalogs to binary format (.mo)
pybabel compile -d src/cli/locales -D cveck
```

---

## Testing Typst Compilation Locally

```bash
python -c "
from src.core.paths import PROJECT_ROOT, TEMPLATES_DIR, OUTPUT_DIR
from src.core.services.typst import compile_typst_and_extract
res = compile_typst_and_extract(
    (TEMPLATES_DIR / 'en.example.typ').read_text(),
    OUTPUT_DIR / 'test.pdf',
    OUTPUT_DIR / 'test.typ',
    root_dir=PROJECT_ROOT
)
print('Success:', res.success, '| Extracted chars:', len(res.extracted_text))
"
```