<div align="center">

# ✦ Cveck

### **Autonomous Agentic Pipeline for ATS-Optimized Resume Tailoring & Gap Tracking**

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange.svg?style=for-the-badge&logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![Typst](https://img.shields.io/badge/typesetting-Typst-239DAD.svg?style=for-the-badge&logo=typst&logoColor=white)](https://typst.app/)
[![i18n](https://img.shields.io/badge/i18n-EN%20%7C%20PT--BR%20%7C%20ZH-success.svg?style=for-the-badge)](https://github.com/FranciscoOssian/cveck)
[![License](https://img.shields.io/badge/license-MIT-purple.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Cveck</b> is an open-source, AI-powered agentic system that adapts software engineering resumes to match target job descriptions with mathematical ATS keyword alignment, strict factual grounding, compiler auto-repair, and continuous gap tracking.
</p>

[Key Features](#-key-features) • [Architecture](#-architecture) • [Quickstart](#-quickstart) • [CLI Commands](#-cli-commands) • [Internationalization](#-internationalization) • [Configuration](#-configuration)

---

</div>

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

---

## 🚀 Quickstart

### Prerequisites

- **Python 3.11+**

### 1. Clone & Install

```bash
git clone https://github.com/FranciscoOssian/cveck.git
cd cveck

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package with dependencies
pip install -e .
```

### 2. Configure Environment

Create a `.env` file in the root directory with your model API keys:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
NVIDIA_API_KEY=your_nvidia_nim_key
OPENROUTER_API_KEY=your_openrouter_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### 3. Setup Your Master Profile

Edit `doc/USER_PROFILE.md` with your factual career history, achievements, and core stack. This file acts as the **single source of truth** for all generations.

### 4. Run the CLI

```bash
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

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

<div align="center">
  <sub>Built with passion for engineers aiming for technical excellence.</sub>
</div>
