from typing import List, Optional
from pydantic import BaseModel, Field
from src.core.models.job import JobTerm
from src.core.models.gap import GapItem
from src.core.models.ats import ATSReport


class DomainState(BaseModel):
    """Neutral and pure state of the product state machine."""
    job_description: str = ""
    job_slug: str = ""
    job_title: str = ""
    company_name: str = ""
    job_lang: str = "en"
    job_date: str = ""

    job_terms: List[JobTerm] = Field(default_factory=list)
    detected_gaps: List[GapItem] = Field(default_factory=list)
    pruned_profile: str = ""

    typ_content: str = ""
    pdf_path: str = ""
    txt_content: str = ""
    typ_error: str = ""
    syntax_error_count: int = 0

    ats_report: Optional[ATSReport] = None
    iteration: int = 0
    is_approved: bool = False
    final_summary: str = ""