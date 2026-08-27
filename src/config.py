import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DOC_DIR = BASE_DIR / "doc"
TEMPLATES_DIR = BASE_DIR / "templates"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output"

USER_PROFILE_PATH = DOC_DIR / "USER_PROFILE.md"
GAPS_MD_PATH = DOC_DIR / "GAPS.md"
GAPS_JSON_PATH = DOC_DIR / "gaps.json"

MAX_ATS_RETRIES = int(os.getenv("MAX_ATS_RETRIES", "3"))
TARGET_ATS_SCORE = float(os.getenv("TARGET_ATS_SCORE", "85.0"))
STUFFING_DENSITY_THRESHOLD = 0.02


def get_llm(temperature: float = 0.1):
    from src.providers import get_dynamic_llm
    return get_dynamic_llm(temperature=temperature)