# Configuration & Provider Hub

CVECK stores user settings in `providers.json` at the project root and sensitive keys in `.env`.

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

## Environment Variables (`.env`)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MAX_ATS_RETRIES` | Max reflection cycles before committing | `3` |
| `TARGET_ATS_SCORE` | Minimum score threshold for approval | `85.0` |
| `DEEPSEEK_API_KEY` | DeepSeek official API key | — |
| `NVIDIA_API_KEY` | NVIDIA NIM Build API key | — |
| `OPENROUTER_API_KEY`| OpenRouter API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `GROQ_API_KEY` | Groq Cloud API key | — |
| `ZAI_API_KEY` | Z.AI (GLM) API key | — |