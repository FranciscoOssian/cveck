import re
import unicodedata
from typing import List
from pydantic import BaseModel, Field, model_validator, field_validator


def sanitize_slug(text: str) -> str:
    """Converts any string to a safe kebab-case format for filenames."""
    if not text:
        return "cv-tailored"
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "cv-tailored"


class JobTerm(BaseModel):
    term: str = Field(default="", description="Canonical name of the technology or skill")
    required: bool = Field(default=False, description="Whether this is a mandatory requirement for the job")
    alternatives: List[str] = Field(default_factory=list, description="Equivalent accepted alternative terms (OR)")
    aliases: List[str] = Field(default_factory=list, description="Literal synonyms or spelling variations")
    category: str = Field(default="other", description="Technical skill category")

    @model_validator(mode="before")
    @classmethod
    def preprocess_term(cls, data):
        if isinstance(data, str):
            return {"term": data}
        return data


class TermExtractorResponse(BaseModel):
    job_title: str = Field(default="Software Developer", description="Extracted job title")
    company_name: str = Field(default="Company", description="Hiring company name")
    job_slug: str = Field(default="job-company", description="Kebab-case slug")
    job_lang: str = Field(default="en", description="Lowercase ISO language code of the job posting")
    terms: List[JobTerm] = Field(default_factory=list, description="Extracted technical requirements")

    @field_validator("job_slug", mode="after")
    @classmethod
    def clean_slug(cls, v: str) -> str:
        return sanitize_slug(v)

    @field_validator("job_lang", mode="after")
    @classmethod
    def clean_lang(cls, v: str) -> str:
        return (v or "en").strip().lower()