import json
from typing import List, Dict, Any
from src.core.models.job import JobTerm
from src.core.paths import OUTPUT_DIR


def execute_commit_artifacts(
    job_slug: str,
    job_terms: List[JobTerm],
    txt_content: str,
    pruned_profile: str = ""
) -> Dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = job_slug or "cv-tailored"

    terms_data = [t.model_dump() for t in job_terms]
    terms_path = OUTPUT_DIR / f"job_terms-{slug}.json"
    terms_path.write_text(
        json.dumps(terms_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    txt_path = OUTPUT_DIR / f"resume-{slug}.txt"
    if txt_content:
        txt_path.write_text(txt_content, encoding="utf-8")

    result = {
        "job_slug": slug,
        "terms_file": str(terms_path),
        "txt_file": str(txt_path) if txt_content else ""
    }

    if pruned_profile:
        pruned_path = OUTPUT_DIR / f"profile_pruned-{slug}.md"
        pruned_path.write_text(pruned_profile, encoding="utf-8")
        result["pruned_profile_file"] = str(pruned_path)

    return result