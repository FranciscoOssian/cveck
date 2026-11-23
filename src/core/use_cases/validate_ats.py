from typing import List, Optional
from src.core.models.job import JobTerm
from src.core.models.ats import ATSReport
from src.core.services.ats import calculate_ats_metrics


def execute_validate_ats(
    job_terms: List[JobTerm],
    resume_text: str,
    target_score: float = 85.0,
    stuffing_threshold: float = 0.02
) -> tuple[ATSReport, bool]:
    report = calculate_ats_metrics(
        job_terms=job_terms,
        resume_text=resume_text,
        stuffing_threshold=stuffing_threshold
    )
    is_approved = (not report.hard_fail) and (report.score >= target_score)
    return report, is_approved