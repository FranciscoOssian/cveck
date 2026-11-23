# Troubleshooting & Common Issues

### 1. 401 Authentication Error
- **Symptom:** `❌ Authentication Error (401)` displayed in CLI.
- **Cause:** Missing or invalid API key for the active provider.
- **Solution:** Verify that the environment variable specified in `providers.json` matches your `.env` entry (e.g., `DEEPSEEK_API_KEY=sk-...`).

---

### 2. Typst Syntax Error Loop
- **Symptom:** `PROCESS HALTED: TYPST SYNTAX FAILURE` after 3 attempts.
- **Cause:** The selected model lacks sufficient Typst code generation capability.
- **Solution:** Switch to a stronger coding model using `/provider` (e.g., `claude-3-5-sonnet`, `deepseek-chat`, or `meta/llama-3.3-70b-instruct`).

---

### 3. Clipboard Empty on Linux / Wayland
- **Symptom:** Pasting from clipboard falls back to manual terminal prompt.
- **Cause:** Missing `wl-clipboard` or `xclip` utility.
- **Solution:** Install the clipboard manager for your display server:
  - Wayland: `sudo apt install wl-clipboard`
  - X11: `sudo apt install xclip`

---

### 4. MCP Server Connection Issues
- **Symptom:** MCP client cannot connect or fails on startup.
- **Cause:** Python path in the MCP client configuration is pointing to system Python instead of `.venv`.
- **Solution:** Specify the full path to `.venv/bin/python` (Linux/macOS) or `.venv\Scripts\python.exe` (Windows) in your MCP client configuration (`claude_desktop_config.json` or Cursor settings).