#!/usr/bin/env bash
set -euo pipefail

# 1. Locate Python 3.11+
PYTHON=""
for cmd in python3.12 python3.11 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.11+ is required but not found in PATH." >&2
    exit 1
fi

# 2. Create venv if the python binary inside it does not exist
VENV_PY=".venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
    echo "--> Creating virtual environment (.venv)..."
    "$PYTHON" -m venv .venv
fi

# 3. Install dependencies inside .venv
echo "--> Installing dependencies into .venv..."
"$VENV_PY" -m pip install --upgrade pip --quiet
"$VENV_PY" -m pip install -e . --quiet

# 4. Compile translations inside .venv
echo "--> Compiling i18n translation catalogs..."
"$VENV_PY" -m babel.messages.frontend compile -d src/locales -D cveck --quiet 2>/dev/null || true

# 5. Ensure required folders and default .env exist
mkdir -p output doc
if [ ! -f .env ]; then
    echo "--> Creating default .env..."
    cat << 'EOF' > .env
DEEPSEEK_API_KEY=
NVIDIA_API_KEY=
OPENROUTER_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
EOF
fi

echo -e "\nSetup completed successfully."
echo "Run: source .venv/bin/activate && cveck"