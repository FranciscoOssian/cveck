from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class GapItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    term: str = Field(default="", description="Name of the missing technology or skill")
    category: str = Field(default="other", description="Technical category")
    required: bool = Field(default=False, description="Whether this is mandatory for the job")
    job_title: str = Field(default="", alias="vaga", description="Job title")
    company_name: str = Field(default="", alias="empresa", description="Hiring company")
    date: str = Field(default="", alias="data", description="Application date (YYYY-MM-DD)")
    reason: str = Field(default="", alias="motivo", description="Reason or excerpt describing why this skill was flagged as a gap")
    suggestion: Optional[str] = Field(default="", alias="sugestao", description="Actionable study or certification suggestion")


class RecordGaps(BaseModel):
    real_gaps: List[GapItem] = Field(
        default_factory=list,
        description="List of real gaps confirmed to be absent from the candidate profile"
    )