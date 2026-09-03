# Development & Contribution Guide

## Project Architecture

```text
cveck/
├── doc/                      # USER_PROFILE.md, GAPS.md, gaps.json
├── output/                   # Generated .pdf, .typ, .txt, JSON artifacts
├── prompts/                  # Markdown system prompts and style guides
├── src/
│   ├── locales/              # gettext translation catalogs (.pot, .po, .mo)
│   ├── nodes/                # LangGraph node functions
│   ├── tools/                # ATS Scorer, Typst Runner, Token Tracker
│   ├── cli.py                # Rich-based interactive CLI
│   ├── config.py             # Global constants and paths
│   ├── graph.py              # LangGraph StateGraph compilation
│   ├── i18n.py               # Runtime localization manager
│   ├── providers.py          # Dynamic LLM provider registry
│   └── state.py              # Pydantic schemas and typed state definitions
├── templates/                # Typst resume templates (.typ)
└── babel.cfg                 # Babel extraction configuration
```


---

## Working with Internationalization (i18n)

CVECK uses standard GNU `gettext` via Babel.

```bash
# 1. Extract translatable strings from source
pybabel extract -F babel.cfg -o src/locales/cveck.pot .

# 2. Update existing catalogs (pt_BR, zh, en)
pybabel update -i src/locales/cveck.pot -d src/locales -D cveck

# 3. Compile catalogs to binary format (.mo)
pybabel compile -d src/locales -D cveck
```

---

## Adding a New Typst Template

1. Place your base template in `templates/{lang}.typ` or `templates/{lang}.example.typ`.
2. Ensure the template exports a `#show: CV.with(...)` rule and `#columns-2` helper.
3. Test compilation locally:
```bash
python -c "from src.tools.typst_runner import compile_typst_to_pdf; from pathlib import Path; compile_typst_to_pdf(Path('templates/en.example.typ'), Path('output/test.pdf'))"
```