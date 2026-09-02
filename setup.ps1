$ErrorActionPreference = "Stop"

# 1. Locate Python 3.11+
$py = $null
foreach ($cmd in @("py -3.12", "py -3.11", "py", "python")) {
    try {
        $check = Invoke-Expression "$cmd -c `"import sys; print(sys.version_info >= (3, 11))`"" 2>$null
        if ($check -match "True") { $py = $cmd; break }
    } catch {}
}

if (-not $py) {
    Write-Error "Python 3.11+ is required but was not found in PATH."
    Exit 1
}

# 2. Create venv if the python executable does not exist
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "--> Creating virtual environment (.venv)..."
    Invoke-Expression "$py -m venv .venv"
}

# 3. Install dependencies inside .venv
Write-Host "--> Installing dependencies into .venv..."
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -e . --quiet

# 4. Compile translations inside .venv
Write-Host "--> Compiling i18n translation catalogs..."
& $venvPy -m babel.messages.frontend compile -d src/locales -D cveck --quiet 2>$null

# 5. Ensure required folders and default .env exist
New-Item -ItemType Directory -Force -Path "output", "doc" | Out-Null
if (-not (Test-Path ".env")) {
    Write-Host "--> Creating default .env..."
    @"
DEEPSEEK_API_KEY=
NVIDIA_API_KEY=
OPENROUTER_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
"@ | Out-File -Encoding utf8 ".env"
}

Write-Host "`nSetup completed successfully." -ForegroundColor Green
Write-Host "Run: .venv\Scripts\Activate.ps1; cveck"