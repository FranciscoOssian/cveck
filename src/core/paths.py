import os
from pathlib import Path
from typing import Optional


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Dynamically locates the CVECK package root by searching for project markers
    such as 'pyproject.toml' or '.git'. If not found by walking up directories,
    falls back to the physical file hierarchy (__file__ -> src/core/paths.py -> parents[2]).
    """
    current = (start_path or Path(__file__)).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent

    # Structural fallback: src/core/paths.py -> parents[2] is the repository root
    return Path(__file__).resolve().parents[2]


# Absolute project root and canonical system directories
PROJECT_ROOT = find_project_root()
DOC_DIR = PROJECT_ROOT / "doc"
OUTPUT_DIR = PROJECT_ROOT / "output"
SRC_DIR = PROJECT_ROOT / "src"
CORE_DIR = SRC_DIR / "core"
ASSETS_DIR = CORE_DIR / "assets"
PROMPTS_DIR = ASSETS_DIR / "prompts"

# Smart fallback for templates (inside assets or in project root)
if (ASSETS_DIR / "templates").exists():
    TEMPLATES_DIR = ASSETS_DIR / "templates"
elif (PROJECT_ROOT / "templates").exists():
    TEMPLATES_DIR = PROJECT_ROOT / "templates"
else:
    TEMPLATES_DIR = ASSETS_DIR / "templates"