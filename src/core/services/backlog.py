import json
from pathlib import Path
from typing import List, Dict, Any
from src.core.models.gap import GapItem

CATEGORY_LABELS = {
    "backend-architecture": "Backend & Architecture",
    "infra-devops": "Infra & DevOps",
    "data": "Data",
    "security": "Security",
    "frontend-mobile": "Front-End & Mobile",
    "ai": "AI",
    "cloud": "Cloud",
    "engineering-practices": "Engineering Practices",
    "other": "Other",
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
        cat = CATEGORY_LABELS.get(entry.get("category", "other"), "Other")
        status = entry.get("status", "open")
        lines.append(f"## {term} _({cat})_")
        lines.append("")
        lines.append(f"- Status: `{status}`")
        for o in entry.get("occurrences", []):
            req = "mandatory" if o.get("required") else "differential"
            company = o.get("company_name") or o.get("empresa", "")
            job = o.get("job_title") or o.get("vaga", "")
            date = o.get("date") or o.get("data", "")
            reason = o.get("reason") or o.get("motivo", "")
            suggestion = o.get("suggestion") or o.get("sugestao", "")

            lines.append(f"- **{company}** — {job} ({date}) [{req}]")
            if reason:
                lines.append(f"  - Reason: {reason}")
            if suggestion:
                lines.append(f"  - Study Suggestion: {suggestion}")
        lines.append("")
    return "\n".join(lines) + "\n"


def update_gaps_backlog(
    new_gaps: List[GapItem],
    gaps_json_path: Path,
    gaps_md_path: Path
) -> None:
    """Atomically updates and deduplicates the gaps backlog."""
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
            "job_title": gap.job_title,
            "company_name": gap.company_name,
            "date": gap.date,
            "reason": gap.reason,
            "suggestion": gap.suggestion or "",
        }
        if term in data:
            exists = any(
                (o.get("job_title") == occ["job_title"] or o.get("vaga") == occ["job_title"]) and
                (o.get("date") == occ["date"] or o.get("data") == occ["date"])
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