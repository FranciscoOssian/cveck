import re
import unicodedata
from typing import List, Dict, Any
from src.state import JobTerm, ATSReport
from src.config import STUFFING_DENSITY_THRESHOLD


def normalize(text: str) -> str:
    """Convert to lowercase and remove accents."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def term_pattern(term: str) -> re.Pattern:
    """Regex word matching with flexible boundary for technical punctuation."""
    escaped = re.escape(normalize(term))
    return re.compile(rf"(?<!\w){escaped}(?!\w)")


def find_term(term: str, aliases: List[str], normalized_resume: str):
    safe_aliases = aliases or []
    candidates = [term] + [a for a in safe_aliases if a and a != term]
    total = 0
    matched_alias = None
    for candidate in candidates:
        pattern = term_pattern(candidate)
        occurrences = len(pattern.findall(normalized_resume))
        if occurrences > 0 and matched_alias is None:
            matched_alias = candidate
        total += occurrences
    return total > 0, total, matched_alias


def _register_match(report, item, occurrences, matched_alias, total_words, stuffing_density):
    report.matched.append({
        "term": item.term,
        "matched_as": matched_alias,
        "occurrences": occurrences,
    })
    density = occurrences / total_words
    if density > stuffing_density:
        report.stuffing_flags.append({
            "term": item.term,
            "occurrences": occurrences,
            "density": round(density * 100, 2),
        })


def _register_miss(report, item):
    if item.required:
        report.missing_required.append(item.term)
    else:
        report.missing_optional.append(item.term)


def _compute_raw_score(coverage_required_pct, required_count, optional_count, hits, required_hits):
    optional_hits = hits - required_hits
    optional_pct = (optional_hits / optional_count * 100) if optional_count > 0 else 0.0
    if required_count > 0 and optional_count > 0:
        return (0.7 * coverage_required_pct) + (0.3 * optional_pct)
    if required_count > 0:
        return coverage_required_pct
    if optional_count > 0:
        return optional_pct
    return 100.0


def calculate_ats_metrics(
    job_terms: List[Any],
    resume_text: str,
    stuffing_density: float = STUFFING_DENSITY_THRESHOLD
) -> ATSReport:
    normalized_resume = normalize(resume_text)
    total_words = len(normalized_resume.split()) or 1

    report = ATSReport()
    if not job_terms:
        report.score = 100.0
        return report

    safe_terms: List[JobTerm] = [
        t if isinstance(t, JobTerm) else JobTerm.model_validate(t)
        for t in job_terms
    ]

    hits = 0
    required_count = sum(1 for t in safe_terms if t.required)
    required_hits = 0

    for item in safe_terms:
        found, occurrences, matched_alias = find_term(item.term, item.aliases, normalized_resume)
        if found:
            hits += 1
            required_hits += item.required
            _register_match(report, item, occurrences, matched_alias, total_words, stuffing_density)
        else:
            _register_miss(report, item)

    total_terms = len(safe_terms)
    report.coverage_pct = round((hits / total_terms) * 100, 1)
    report.coverage_required_pct = (
        round((required_hits / required_count) * 100, 1) if required_count else 100.0
    )
    report.hard_fail = len(report.missing_required) > 0
    report.score = round(_compute_raw_score(
        report.coverage_required_pct,
        required_count, total_terms - required_count, hits, required_hits,
    ), 1)
    return report