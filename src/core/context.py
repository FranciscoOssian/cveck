from pathlib import Path
from typing import Tuple


def load_user_profile(doc_dir: Path) -> str:
    """Carrega USER_PROFILE.md com fallback automático para USER_PROFILE.example.md."""
    profile_path = doc_dir / "USER_PROFILE.md"
    if profile_path.exists():
        return profile_path.read_text(encoding="utf-8")
    example_path = doc_dir / "USER_PROFILE.example.md"
    if example_path.exists():
        return example_path.read_text(encoding="utf-8")
    return ""


def resolve_template_skeleton(templates_dir: Path, lang: str = "en") -> Tuple[str, str]:
    """Localiza o template Typst correto com fallbacks seguros."""
    lang_clean = (lang or "en").strip().lower().replace("_", "-")
    lang_prefix = lang_clean.split("-")[0]

    candidates = [
        templates_dir / f"{lang_clean}.typ",
        templates_dir / f"{lang_clean}.example.typ",
        templates_dir / f"{lang_prefix}.typ",
        templates_dir / f"{lang_prefix}.example.typ",
        templates_dir / "en.typ",
        templates_dir / "en.example.typ",
        templates_dir / "pt.typ",
        templates_dir / "pt.example.typ",
    ]

    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8"), lang_prefix

    raise FileNotFoundError(f"Nenhum template Typst encontrado para o idioma '{lang}' em {templates_dir}.")