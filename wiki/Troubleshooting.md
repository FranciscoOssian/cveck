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

### 4. Missing Font / Broken Layout in Output PDF
- **Symptom:** Characters render with missing glyph boxes.
- **Solution:** Typst utilizes system fonts. Ensure fonts like *Liberation Sans*, *Arial*, or Noto CJK fonts (for Chinese `zh`) are installed on your host system:
  ```bash
  sudo apt install fonts-liberation fonts-noto-cjk
  ```