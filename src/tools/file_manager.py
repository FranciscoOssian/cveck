import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from src.i18n import _
from src.config import GAPS_JSON_PATH, GAPS_MD_PATH, USER_PROFILE_PATH, PROMPTS_DIR, TEMPLATES_DIR, BASE_DIR
from src.state import GapItem

CATEGORY_LABELS = {
    "backend-arquitetura": "Backend & Architecture",
    "infra-devops": "Infra & DevOps",
    "dados": "Data",
    "seguranca": "Security",
    "frontend-mobile": "Front-End & Mobile",
    "ia": "AI",
    "cloud": "Cloud",
    "pratica-engenharia": "Engineering Practices",
    "outro": "Other",
}


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def load_user_profile() -> str:
    if USER_PROFILE_PATH.exists():
        return read_file(USER_PROFILE_PATH)
    example_path = USER_PROFILE_PATH.parent / "USER_PROFILE.example.md"
    if example_path.exists():
        return read_file(example_path)
    return ""


def resolve_template_skeleton(lang: str) -> Tuple[str, str]:
    lang_clean = (lang or "pt").strip().lower().replace("_", "-")
    lang_prefix = lang_clean.split("-")[0]

    candidates = [
        TEMPLATES_DIR / f"{lang_clean}.typ",
        TEMPLATES_DIR / f"{lang_clean}.example.typ",
        TEMPLATES_DIR / f"{lang_prefix}.typ",
        TEMPLATES_DIR / f"{lang_prefix}.example.typ",
        TEMPLATES_DIR / "pt.typ",
        TEMPLATES_DIR / "pt.example.typ",
        TEMPLATES_DIR / "en.typ",
        TEMPLATES_DIR / "en.example.typ",
    ]

    for path in candidates:
        if path.exists():
            return read_file(path), lang_prefix

    raise FileNotFoundError(
        _("No template found for language '{lang}' in '{dir}'.").format(lang=lang, dir=TEMPLATES_DIR)
    )


def load_prompt(filename: str) -> str:
    return read_file(PROMPTS_DIR / filename)


def _merge_gap_into_data(data: dict, gap: GapItem) -> None:
    term = gap.term.strip().lower()
    occ = {
        "required": gap.required,
        "vaga": gap.vaga,
        "empresa": gap.empresa,
        "data": gap.data,
        "motivo": gap.motivo,
        "sugestao": gap.sugestao or "",
    }
    if term in data:
        exists = any(
            o.get("vaga") == occ["vaga"] and o.get("data") == occ["data"]
            for o in data[term]["occurrences"]
        )
        if not exists:
            data[term]["occurrences"].append(occ)
    else:
        data[term] = {
            "category": gap.category,
            "status": "open",
            "occurrences": [occ],
        }


def _render_gaps_markdown(data: dict) -> str:
    lines = [
        "# Gap Backlog (Studies & Certifications)",
        "",
        "> Curriculum gaps: skills that the market demands (jobs applied) and that still",
        "> **do not exist** in `USER_PROFILE.md`. Organized backlog of studies/certifications.",
        "",
    ]
    for term in sorted(data):
        entry = data[term]
        cat = CATEGORY_LABELS.get(entry.get("category", "outro"), "Outros")
        status = entry.get("status", "open")
        lines.append(f"## {term} _({cat})_")
        lines.append("")
        lines.append(f"- Status: `{status}`")
        for o in entry.get("occurrences", []):
            req = "mandatory" if o.get("required") else "differential"
            lines.append(f"- **{o.get('empresa','')}** — {o.get('vaga','')} ({o.get('data','')}) [{req}]")
            if o.get("motivo"):
                lines.append(f"  - Reason: {o['motivo']}")
            if o.get("sugestao"):
                lines.append(f"  - Study Suggestion: {o['sugestao']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def update_gaps_backlog(new_gaps: List[Any]) -> None:
    if not new_gaps:
        return

    safe_gaps: List[GapItem] = [
        g if isinstance(g, GapItem) else GapItem.model_validate(g)
        for g in new_gaps
    ]

    data: Dict[str, Any] = {}
    if GAPS_JSON_PATH.exists():
        with open(GAPS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    for gap in safe_gaps:
        _merge_gap_into_data(data, gap)

    GAPS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GAPS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    write_file(GAPS_MD_PATH, _render_gaps_markdown(data))