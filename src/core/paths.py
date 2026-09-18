import os
from pathlib import Path
from typing import Optional


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Localiza dinamicamente a raiz do pacote CVECK procurando por marcadores
    como 'pyproject.toml' ou '.git'. Se não encontrar via subida de diretórios,
    usa a hierarquia física baseada neste arquivo (__file__ -> src/core/paths.py -> parents[2]).
    """
    current = (start_path or Path(__file__)).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent

    # Fallback estrutural: src/core/paths.py -> parents[2] é a raiz do repositório
    return Path(__file__).resolve().parents[2]


# Raiz absoluta e diretórios canônicos do sistema
PROJECT_ROOT = find_project_root()
DOC_DIR = PROJECT_ROOT / "doc"
OUTPUT_DIR = PROJECT_ROOT / "output"
SRC_DIR = PROJECT_ROOT / "src"
CORE_DIR = SRC_DIR / "core"
ASSETS_DIR = CORE_DIR / "assets"
PROMPTS_DIR = ASSETS_DIR / "prompts"

# Fallback inteligente para templates (dentro de assets ou na raiz do projeto)
if (ASSETS_DIR / "templates").exists():
    TEMPLATES_DIR = ASSETS_DIR / "templates"
elif (PROJECT_ROOT / "templates").exists():
    TEMPLATES_DIR = PROJECT_ROOT / "templates"
else:
    TEMPLATES_DIR = ASSETS_DIR / "templates"