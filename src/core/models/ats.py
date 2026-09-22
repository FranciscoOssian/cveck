from typing import List, Dict, Any
from pydantic import BaseModel, Field


class ATSReport(BaseModel):
    score: float = 0.0
    coverage_pct: float = 0.0
    coverage_required_pct: float = 0.0
    matched: List[Dict[str, Any]] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    missing_optional: List[str] = Field(default_factory=list)
    stuffing_flags: List[Dict[str, Any]] = Field(default_factory=list)
    hard_fail: bool = False