from pydantic import BaseModel, Field


class SubmitTypstCV(BaseModel):
    typst_code: str = Field(
        description="Full Typst source code, starting with template imports."
    )


class CompilationResult(BaseModel):
    success: bool
    pdf_path: str = ""
    extracted_text: str = ""
    error_message: str = ""