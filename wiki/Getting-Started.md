# Getting Started

This guide walks you through setting up CVECK locally, configuring your model provider, and running either the interactive CLI or the MCP server.

## Prerequisites

- **Python 3.11+** installed and available in your `PATH`.
- A verified candidate profile at `doc/USER_PROFILE.md` (or `doc/USER_PROFILE.example.md`).
- (Optional) An API key for your chosen LLM provider (or a local Ollama instance).

---

## ⚡ 1-Step Automated Installation

### Linux / macOS
```bash
git clone https://github.com/FranciscoOssian/cveck.git && cd cveck
bash setup.sh
```

### Windows (PowerShell)
```powershell
git clone https://github.com/FranciscoOssian/cveck.git; cd cveck
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

### What `setup` does automatically:
1. Verifies Python 3.11+ runtime.
2. Creates isolated `.venv` and installs the package in editable mode (`pip install -e .`).
3. Compiles all internationalization catalogs (`.po` → `.mo`) in `src/cli/locales/`.
4. Generates initial `output/`, `doc/`, and `.env` scaffold.

---

## 🔑 Configure API Keys

Open `.env` in your repository root and add your API key:

```env
DEEPSEEK_API_KEY=sk-...
# Optional providers:
# NVIDIA_API_KEY=nvapi-...
# OPENROUTER_API_KEY=sk-or-...
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GROQ_API_KEY=gsk-...
```

---

## 🚀 Running CVECK

### Mode 1: Interactive Terminal CLI
Activate your virtual environment and launch the CLI:

```bash
# Linux / macOS
source .venv/bin/activate
cveck

# Windows
.venv\Scripts\Activate.ps1
cveck
```

### Mode 2: Model Context Protocol (MCP) Server
Launch the stdio MCP server to connect CVECK tools to Cursor, Claude Desktop, or Windsurf:

```bash
cveck mcp
```