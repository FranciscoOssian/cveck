<div align="center">

# ✦ Cveck

### **Autonomous Agentic Pipeline for ATS-Optimized Resume Tailoring & Gap Tracking**

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange.svg?style=for-the-badge&logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![Typst](https://img.shields.io/badge/typesetting-Typst-239DAD.svg?style=for-the-badge&logo=typst&logoColor=white)](https://typst.app/)
[![Wiki Documentation](https://img.shields.io/badge/docs-GitHub%20Wiki-blueviolet.svg?style=for-the-badge&logo=github&logoColor=white)](https://github.com/FranciscoOssian/cveck/wiki)
[![i18n](https://img.shields.io/badge/i18n-EN%20%7C%20PT--BR%20%7C%20ZH-success.svg?style=for-the-badge)](https://github.com/FranciscoOssian/cveck)
[![License](https://img.shields.io/badge/license-MIT-purple.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Cveck</b> is an open-source, AI-powered agentic system that adapts software engineering resumes to match target job descriptions with mathematical ATS keyword alignment, strict factual grounding, compiler auto-repair, and continuous gap tracking.
</p>

[📖 Documentation Wiki](https://github.com/FranciscoOssian/cveck/wiki) • [Key Features](#-key-features) • [Architecture](#-architecture) • [Quickstart](#-quickstart) • [CLI Commands](#-cli-commands) • [Internationalization](#-internationalization) • [Configuration](#-configuration)

---

</div>

> 📚 **Looking for in-depth technical documentation?**
>
> If you want to understand all the architectural decisions, LangGraph node specifications, mathematical ATS formulas, and deep system invariants **without needing to dig through the raw source code**, visit our **[Official GitHub Wiki](https://github.com/FranciscoOssian/cveck/wiki)**!
>
> - **[System Architecture & Invariants](https://github.com/FranciscoOssian/cveck/wiki/Architecture)**
> - **[Pipeline Node Specifications](https://github.com/FranciscoOssian/cveck/wiki/Pipeline)**
> - **[LangGraph Cyclic Routing & State](https://github.com/FranciscoOssian/cveck/wiki/LangGraph)**
> - **[ATS Scoring Engine & Anti-Stuffing Formula](https://github.com/FranciscoOssian/cveck/wiki/ATS)**

---

## 💡 Why Cveck?

Traditional AI resume tools suffer from three fatal flaws:

1. **Hallucinations & Resume Inflation:** They invent technologies and fake metrics you never worked with.
2. **Fragile Typesetting:** They produce broken Markdown or bloated LaTeX templates that fail to compile.
3. **Black-box Keyword Stuffing:** They spam keywords blindly without understanding ATS parser weighting or density penalties.

**Cveck solves this with an agentic state-machine built on LangGraph and Typst:**

```
                  ┌────────────────────────────────────────┐
                  │          Job Description (JD)          │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                      [ Node 1: Term Extractor ]
                                      │
                                      ▼
                       [ Node 2: Gap Finder ] ───► (Writes to doc/GAPS.md)
                                      │
                                      ▼
                      [ Node 3: Typst Generator ]
                                      │
                                      ▼
                      [ Node 4: Typst Compiler ]
                                      │
                   ┌──────────────────┴──────────────────┐
        (Syntax Error)                                (Success)
                   │                                     │
                   ▼                                     ▼
        [ Node 5: Typst Fixer ]               [ Node 6: ATS Validator ]
                   │                                     │
                   └──────────► (Retry)                  ├─── (Approved) ──► [ Output PDF & TXT ]
                                                         │
                                                  (Score < 85%)
                                                         │
                                                         ▼
                                               [ Node 7: CV Refiner ]
                                                         │
                                                         └───► (Feedback Loop)
```

---

## ✨ Key Features

- 🎯 **Factual Grounding & Anti-Hallucination:** Strictly constrains outputs to your verified `USER_PROFILE.md`. It is physically prevented from inventing skills or metrics.
- 🔄 **Self-Healing Typst Compiler:** If generated code fails compilation, a dedicated syntax fixer analyzes compiler stderr and auto-repairs braces, labels, and show rules in zero human steps.
- 📊 **Deterministic ATS Scoring Engine:** Measures exact keyword coverage, mandatory vs. differential compliance, and flags excessive keyword density penalties (>2% stuffing).
- 🧭 **Automated Skill Gap Backlog (`GAPS.md` / `gaps.json`):** Automatically registers real market requirements missing from your profile into an organized study roadmap.
- ⚡ **Multi-Provider & Multi-Model:** Switch on the fly between **DeepSeek**, **NVIDIA NIM**, **OpenRouter**, **Groq**, **OpenAI**, **Anthropic**, or **Local Ollama**.
- 🌍 **Native Multi-Language (i18n):** Full GNU `gettext` + Babel internationalization with first-class support for English, Portuguese (BR), and Mandarin Chinese (`zh`).

---

## 🏗️ Architecture & StateGraph

The pipeline operates as a cyclic deterministic graph compiled with **LangGraph**:

| Step   | Node             | Functionality                                                                            |
| :----- | :--------------- | :--------------------------------------------------------------------------------------- |
| **01** | `term_extractor` | Parses the job description into canonical hard skills, tools, and mandatory constraints. |
| **02** | `gap_finder`     | Compares extracted terms with `USER_PROFILE.md` to flag unacquired skills as hard gaps.  |
| **03** | `gaps_updater`   | Persists detected gaps into structured `GAPS.md` and `gaps.json` backlog.                |
| **04** | `cv_generator`   | Generates pure Typst source code applying STAR narrative and bold front-loading.         |
| **05** | `typst_compiler` | Compiles `.typ` to vector `.pdf` and extracts layout text via `pymupdf`.                 |
| **06** | `typst_fixer`    | _(Conditional)_ Auto-repairs Typst compilation errors with compiler traceback.           |
| **07** | `ats_validator`  | Runs deterministic ATS scoring algorithm against extracted keywords.                     |
| **08** | `cv_refiner`     | _(Cyclic)_ Reflects on missing keywords and refines Typst code (max 3 retries).          |
| **09** | `committer`      | Produces technical summary report, saves `.txt` parse, terms dump, and final `.pdf`.     |

> 🔍 *For complete state typing schemas, cyclic transitions, and edge routing algorithms, read the [Wiki Architecture Guide](https://github.com/FranciscoOssian/cveck/wiki/Architecture).*

---

## 🚀 Quickstart

### Prerequisites

- **Python 3.11+** installed and available in your PATH.

---

### ⚡ 1-Step Automated Setup

Clone the repository and run the setup script for your operating system:

#### 🐧 Linux / 🍎 macOS
```bash
git clone https://github.com/FranciscoOssian/cveck.git && cd cveck
bash setup.sh
```
#### 🪟 Windows (PowerShell)

```powershell
git clone https://github.com/FranciscoOssian/cveck.git; cd cveck
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

> **What the setup script does automatically:**
> 1. Verifies Python 3.11+ installation.
> 2. Creates a clean `.venv` and installs all dependencies in editable mode (`pip install -e .`).
> 3. Compiles all i18n translation catalogs (`gettext`/Babel).
> 4. Generates your default `.env` and `doc` folder.

---

### 2. Configure & Run

1. Add your LLM API keys to `.env` (or leave empty if using local Ollama):
```env
DEEPSEEK_API_KEY=your_key_here
# Optional: NVIDIA_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
```

2. Activate the virtual environment and start Cveck:
```bash
# Linux / macOS:
source .venv/bin/activate
cveck

# Windows:
.venv\Scripts\Activate.ps1
cveck
```

---

## 💻 CLI Commands & Options

Launch Cveck with specific locales or options:

```bash
# Launch in English (Default)
cveck --lang en

# Launch in Portuguese (Brazil)
cveck --lang pt_BR

# Launch in Mandarin Chinese
cveck --lang zh
```

### In-Session Slash Commands

| Command         | Action                                                                                        |
| :-------------- | :-------------------------------------------------------------------------------------------- |
| **`[ENTER]`**   | Load and adapt job description directly from your clipboard.                                  |
| **`/provider`** | Open dynamic Model & Provider Manager (switch model, fetch API models, add custom endpoints). |
| **`/lang`**     | Change interface language interactively during runtime.                                       |
| **`/clean`**    | Clean generated artifacts in `output/` directory.                                             |
| **`/exit`**     | Exit the CLI.                                                                                 |

---

## 🌐 Internationalization (i18n)

Cveck implements the standard GNU `gettext` architecture. Text extraction, template catalogs, and runtime binaries are managed via **Babel**:

```bash
# Extract strings to template
pybabel extract -F babel.cfg -o src/locales/cveck.pot .

# Update existing language catalogs
pybabel update -i src/locales/cveck.pot -d src/locales -D cveck

# Compile .po catalogs to binary .mo
pybabel compile -d src/locales -D cveck
```

**Officially Supported Locales:**

- 🇺🇸 **English (`en`)** — Source / Default
- 🇧🇷 **Português (`pt_BR`)** — Brazilian Portuguese
- 🇨🇳 **中文 (`zh`)** — Simplified Mandarin Chinese

---

## 📁 Repository Structure

```
cveck/
├── doc/
│   ├── USER_PROFILE.md       # Master career profile (Single Source of Truth)
│   ├── GAPS.md               # Structured market gap backlog (Markdown)
│   └── gaps.json             # Programmatic gap database
├── wiki/                     # Documentation-as-Code source for GitHub Wiki
├── output/                   # Generated .pdf, .typ, .txt, and terms JSON
├── prompts/                  # System prompts & CV Style Guide
├── src/
│   ├── locales/              # gettext translation catalogs (.pot, .po, .mo)
│   ├── nodes/                # LangGraph state machine node handlers
│   ├── tools/                # ATS Scorer, Typst Runner, Token Tracker, Parser
│   ├── cli.py                # Interactive Rich CLI application
│   ├── config.py             # Global constants and environment configuration
│   ├── graph.py              # LangGraph StateGraph pipeline definition
│   ├── i18n.py               # gettext runtime internationalization manager
│   ├── providers.py          # Dynamic LLM provider registry and routing
│   └── state.py              # Pydantic schemas and typed state definitions
├── templates/                # Base Typst templates (.typ)
├── babel.cfg                 # Babel extraction rules
└── pyproject.toml            # Project metadata and dependencies
```

---

## 🤖 Tested Models

Models that have been tested and work with no (or almost no) problems during runtime.

- minimax-m3
- nemotron-3-ultra-550b-a55b
- deepseek-v4-flash

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

<div align="center">
  <sub>Built with passion for engineers aiming for technical excellence.</sub>
</div>
```