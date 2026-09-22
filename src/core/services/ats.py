import re
import unicodedata
from typing import List
from src.core.models.job import JobTerm
from src.core.models.ats import ATSReport


def normalize(text: str) -> str:
    """Normalizes text by removing accents and converting to lowercase."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def term_pattern(term: str) -> re.Pattern:
    """Strict word-boundary regex to prevent false positives (e.g. Go inside Google)."""
    escaped = re.escape(normalize(term))
    return re.compile(rf"(?<!\w){escaped}(?!\w)")


def calculate_ats_metrics(
    job_terms: List[JobTerm],
    resume_text: str,
    stuffing_threshold: float = 0.02
) -> ATSReport:
    """Calculates mathematical ATS score, checks keyword stuffing and mandatory requirements."""
    normalized_resume = normalize(resume_text)
    total_words = len(normalized_resume.split()) or 1
    report = ATSReport()

    if not job_terms:
        report.score = 100.0
        return report

    hits = 0
    required_count = sum(1 for t in job_terms if t.required)
    required_hits = 0

    for item in job_terms:
        candidates = [item.term] + [a for a in item.aliases if a] + [alt for alt in item.alternatives if alt]
        total_occurrences = 0
        matched_alias = None

        for cand in candidates:
            pattern = term_pattern(cand)
            occs = len(pattern.findall(normalized_resume))
            if occs > 0 and matched_alias is None:
                matched_alias = cand
            total_occurrences += occs

        if total_occurrences > 0:
            hits += 1
            if item.required:
                required_hits += 1
            report.matched.append({
                "term": item.term,
                "matched_as": matched_alias,
                "occurrences": total_occurrences
            })
            density = total_occurrences / total_words
            if density > stuffing_threshold:
                report.stuffing_flags.append({
                    "term": item.term,
                    "occurrences": total_occurrences,
                    "density": round(density * 100, 2)
                })
        else:
            label = f"{item.term} OR {' OR '.join(item.alternatives)}" if item.alternatives else item.term
            if item.required:
                report.missing_required.append(label)
            else:
                report.missing_optional.append(label)

    total_terms = len(job_terms)
    report.coverage_pct = round((hits / total_terms) * 100, 1)
    report.coverage_required_pct = (
        round((required_hits / required_count) * 100, 1) if required_count else 100.0
    )
    report.hard_fail = len(report.missing_required) > 0

    # Formula: 70% mandatory + 30% optional/differential
    optional_count = total_terms - required_count
    optional_hits = hits - required_hits
    optional_pct = (optional_hits / optional_count * 100) if optional_count > 0 else 0.0

    if required_count > 0 and optional_count > 0:
        raw_score = (0.7 * report.coverage_required_pct) + (0.3 * optional_pct)
    elif required_count > 0:
        raw_score = report.coverage_required_pct
    elif optional_count > 0:
        raw_score = optional_pct
    else:
        raw_score = 100.0

    report.score = round(raw_score, 1)
    return report