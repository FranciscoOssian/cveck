from pydantic import BaseModel, Field


class SubmitTypstCV(BaseModel):
    typst_code: str = Field(
        description="Código-fonte Typst completo, iniciando com os imports do template."
    )


class CompilationResult(BaseModel):
    success: bool
    pdf_path: str = ""
    extracted_text: str = ""
    error_message: str = ""