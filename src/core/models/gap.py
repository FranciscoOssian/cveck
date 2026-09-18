from typing import List, Optional
from pydantic import BaseModel, Field


class GapItem(BaseModel):
    term: str = Field(default="", description="Nome da tecnologia ou competência faltante")
    category: str = Field(default="other", description="Categoria técnica")
    required: bool = Field(default=False, description="Se é obrigatório na vaga")
    vaga: str = Field(default="", description="Título da vaga")
    empresa: str = Field(default="", description="Empresa contratante")
    data: str = Field(default="", description="Data da aplicação (YYYY-MM-DD)")
    motivo: str = Field(default="", description="Trecho ou motivo da exigência")
    sugestao: Optional[str] = Field(default="", description="Sugestão de estudo ou certificação")


class RecordGaps(BaseModel):
    real_gaps: List[GapItem] = Field(
        default_factory=list,
        description="Lista de lacunas reais comprovadamente ausentes no perfil do candidato"
    )