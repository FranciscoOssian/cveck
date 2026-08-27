import ast
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from typing_extensions import TypedDict


class JobTerm(BaseModel):
    term: str = Field(default="", description="Canonical name of the technology or skill")
    required: bool = Field(default=False, description="Whether it is a mandatory requirement in the JD")
    aliases: List[str] = Field(default_factory=list, description="Strict synonyms or variations")
    category: str = Field(default="other", description="Technical skill category")

    @model_validator(mode="before")
    @classmethod
    def preprocess_term(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"term": data}
        if isinstance(data, dict) and isinstance(data.get("aliases"), str):
            data["aliases"] = _parse_aliases(data["aliases"])
        return data


def _parse_aliases(aliases_val: str) -> list:
    try:
        return json.loads(aliases_val)
    except Exception:
        pass
    try:
        return ast.literal_eval(aliases_val)
    except Exception:
        pass
    return [aliases_val] if aliases_val else []


class GapItem(BaseModel):
    term: str = Field(default="", description="Name of the missing skill or competency")
    category: str = Field(default="other", description="Technical skill category")
    required: bool = Field(default=False, description="Whether it is a mandatory requirement in the JD")
    vaga: str = Field(default="", description="Job title")
    empresa: str = Field(default="", description="Hiring company name")
    data: str = Field(default="", description="Application date")
    motivo: str = Field(default="", description="Reason or quote from requirement")
    sugestao: Optional[str] = Field(default="", description="Study suggestion or certification")


class ATSReport(BaseModel):
    coverage_pct: float = 0.0
    coverage_required_pct: float = 0.0
    matched: List[Dict[str, Any]] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    missing_optional: List[str] = Field(default_factory=list)
    stuffing_flags: List[Dict[str, Any]] = Field(default_factory=list)
    hard_fail: bool = False
    score: float = 0.0


class CVState(TypedDict, total=False):
    job_description: str
    job_slug: str
    job_title: str
    company_name: str
    job_lang: str
    job_date: str
    
    # Extraction & Gaps
    job_terms: List[JobTerm]
    detected_gaps: List[GapItem]
    
    # Content & Compilation
    typ_content: str
    pdf_path: str
    txt_content: str
    typ_error: str
    syntax_error_count: int
    
    # Validation & Retry
    ats_report: ATSReport
    iteration: int
    is_approved: bool
    final_summary: str
    
    # Token Metrics
    token_usage: Dict[str, Any]
    last_step_tokens: Dict[str, int]