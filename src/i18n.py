import gettext
import locale
import os
from pathlib import Path
from typing import Optional

LOCALE_DIR = Path(__file__).resolve().parent / "locales"
DOMAIN = "cveck"

SUPPORTED_LOCALES = {
    "en": "English",
    "pt_BR": "Português (Brasil)",
    "zh": "中文 (简体)",
}

_current_translation = gettext.NullTranslations()

def setup_i18n(lang: Optional[str] = None) -> gettext.NullTranslations:
    global _current_translation
    target_lang = lang

    if not target_lang:
        # Detect from the operating system
        target_lang = os.getenv("LC_ALL") or os.getenv("LC_MESSAGES") or os.getenv("LANG")
        if not target_lang:
            try:
                target_lang, _ = locale.getlocale()
            except Exception:
                target_lang = "en"

    # Normalization (e.g., pt-BR -> pt_BR)
    if target_lang:
        target_lang = target_lang.split(".")[0].replace("-", "_")

    # Mapping / Fallback
    languages = [target_lang] if target_lang else []
    if target_lang and "_" in target_lang:
        languages.append(target_lang.split("_")[0])  # fallback pt_BR -> pt
    languages.append("en")  # fallback final

    try:
        _current_translation = gettext.translation(
            DOMAIN,
            localedir=str(LOCALE_DIR),
            languages=languages,
            fallback=True
        )
    except Exception:
        _current_translation = gettext.NullTranslations()

    _current_translation.install()
    return _current_translation

def _(message: str) -> str:
    return _current_translation.gettext(message)