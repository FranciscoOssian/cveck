# Development & Contribution Guide

## Repository Structure

```text
cveck/
├── doc/                            # USER_PROFILE.md, GAPS.md, gaps.json
├── output/                         # Generated .pdf, .typ, .txt, profile_pruned.md, terms.json
├── src/
│   ├── core/                       # Pure Business Logic & Domain
│   │   ├── assets/                 # Prompts (Markdown) & Typst templates
│   │   │   ├── prompts/            # extract_terms, find_gaps, prune_profile, generate_cv, etc.
│   │   │   └── templates/          # template.typ, en/pt/zh example skeletons
│   │   ├── models/                 # Pure Pydantic domain models
│   │   │   ├── job.py              # JobTerm, TermExtractorResponse
│   │   │   ├── gap.py              # GapItem, RecordGaps
│   │   │   ├── profile.py          # SubmitPrunedProfile
│   │   │   ├── typst.py            # SubmitTypstCV, CompilationResult
│   │   │   ├── ats.py              # ATSReport
│   │   │   └── state.py            # DomainState (includes pruned_profile)
│   │   ├── services/               # Stateless services (ATS, Typst, Parser, Backlog, Telemetry)
│   │   ├── use_cases/              # Granular domain use cases
│   │   │   ├── extract_terms.py
│   │   │   ├── find_gaps.py
│   │   │   ├── update_gaps.py
│   │   │   ├── prune_profile.py    
│   │   │   ├── generate_cv.py      
│   │   │   ├── compile_cv.py
│   │   │   ├── fix_typst.py
│   │   │   ├── validate_ats.py
│   │   │   ├── refine_cv.py        
│   │   │   └── commit_artifacts.py 
│   │   ├── workflow/               # Declarative workflow schema and evaluators
│   │   ├── context.py              # User profile & template loader
│   │   ├── paths.py                # Dynamic root and directory resolution
│   │   └── workflow.yaml           # Declarative pipeline configuration
│   ├── adapters/                   # Execution Adapters (Adapter Pattern)
│   │   ├── langgraph/              # LangGraph adapter (builder, nodes, router, state)
│   │   └── mcp/                    # Model Context Protocol server adapter (server, prompt)
│   └── cli/                        # Interactive Rich CLI application
│       ├── locales/                # GNU gettext catalogs (.pot, .po, .mo)
│       ├── i18n.py                 # Runtime localization manager
│       ├── ui.py                   # Rich rendering and interactive menus (7-step stream)
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