import json
from pathlib import Path
from typing import List, Dict, Any
from src.core.models.gap import GapItem

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
        cat = CATEGORY_LABELS.get(entry.get("category", "outro"), "Other")
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


def update_gaps_backlog(
    new_gaps: List[GapItem],
    gaps_json_path: Path,
    gaps_md_path: Path
) -> None:
    """Atualiza de forma atômica e deduplicada o backlog de lacunas."""
    if not new_gaps:
        return

    data: Dict[str, Any] = {}
    if gaps_json_path.exists():
        try:
            data = json.loads(gaps_json_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    for gap in new_gaps:
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
                for o in data[term].get("occurrences", [])
            )
            if not exists:
                data[term].setdefault("occurrences", []).append(occ)
        else:
            data[term] = {
                "category": gap.category,
                "status": "open",
                "occurrences": [occ],
            }

    gaps_json_path.parent.mkdir(parents=True, exist_ok=True)
    gaps_json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    gaps_md_path.write_text(_render_gaps_markdown(data), encoding="utf-8")