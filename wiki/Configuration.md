# Configuration & Provider Hub

CVECK stores user provider configurations in `providers.json` at the project root, workflow policies in `src/core/workflow.yaml`, and sensitive keys in `.env`.

## Managing Providers via CLI

Open the dynamic Model & Provider Manager during runtime:
```text
> /provider
```

This menu allows you to:
1. Switch active models on the fly.
2. Query `/models` endpoints to fetch live model lists from your provider.
3. Register custom OpenAI-compatible or Anthropic-compatible endpoints (e.g., local vLLM, LM Studio, Ollama).

---

## Running the Model Context Protocol (MCP) Server

CVECK provides a built-in MCP server adapter (`src/adapters/mcp/`):

```bash
cveck mcp
```

To configure with **Claude Desktop** or **Cursor**, add the server to your MCP configuration:

```json
{
  "mcpServers": {
    "cveck": {
      "command": "python",
      "args": ["-m", "src.adapters.mcp.server"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-..."
      }
    }
  }
}
```

---

## Workflow Policies (`src/core/workflow.yaml`)

Core engine policies can be adjusted directly in `workflow.yaml`:

| Policy | Description | Default |
| :--- | :--- | :--- |
| `target_ats_score` | Minimum score threshold for approval | `85.0` |
| `max_ats_retries` | Max reflection cycles before committing | `3` |
| `max_syntax_retries`| Max Typst compiler auto-repair retries | `3` |
| `stuffing_density_threshold` | Max keyword density before flagging stuffing | `0.02` (2%) |
| `bullet_budget.min_bullets` | Minimum recommended bullets across the CV | `8` |
| `bullet_budget.max_bullets` | Maximum recommended bullets across the CV | `13` |
| `bullet_budget.max_bullets_per_role` | Max bullets allocated per job position | `4` |

---

## Environment Variables (`.env`)

| Variable | Description |
| :--- | :--- |
| `DEEPSEEK_API_KEY` | DeepSeek official API key |
| `NVIDIA_API_KEY` | NVIDIA NIM Build API key |
| `OPENROUTER_API_KEY`| OpenRouter API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GROQ_API_KEY` | Groq Cloud API key |
| `ZAI_API_KEY` | Z.AI (GLM) API key |