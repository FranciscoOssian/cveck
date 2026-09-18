import re
import unicodedata
from typing import List
from pydantic import BaseModel, Field, model_validator


def sanitize_slug(text: str) -> str:
    """Converte qualquer string para kebab-case seguro para nomes de arquivos."""
    if not text:
        return "cv-tailored"
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "cv-tailored"


class JobTerm(BaseModel):
    term: str = Field(default="", description="Nome canônico da tecnologia ou skill")
    required: bool = Field(default=False, description="Se é pré-requisito obrigatório na vaga")
    alternatives: List[str] = Field(default_factory=list, description="Opções equivalentes aceitas (OU)")
    aliases: List[str] = Field(default_factory=list, description="Sinônimos literais ou variações ortográficas")
    category: str = Field(default="other", description="Categoria técnica da habilidade")

    @model_validator(mode="before")
    @classmethod
    def preprocess_term(cls, data):
        if isinstance(data, str):
            return {"term": data}
        return data


class TermExtractorResponse(BaseModel):
    job_title: str = Field(default="Software Developer", description="Título do cargo extraído da vaga")
    company_name: str = Field(default="Company", description="Nome da empresa contratante")
    job_slug: str = Field(default="job-company", description="Slug em kebab-case")
    job_lang: str = Field(default="en", description="Código ISO minúsculo do idioma da vaga")
    terms: List[JobTerm] = Field(default_factory=list, description="Lista estruturada de termos e requisitos")