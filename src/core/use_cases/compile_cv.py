from pathlib import Path
from src.core.models.typst import CompilationResult
from src.core.services.typst import compile_typst_and_extract
from src.core.paths import PROJECT_ROOT, OUTPUT_DIR


def execute_compile_cv(
    typst_code: str,
    job_slug: str,
    job_lang: str
) -> CompilationResult:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = job_slug or "cv-tailored"
    lang = job_lang or "en"
    pdf_path = OUTPUT_DIR / f"cv-{slug}-{lang}.pdf"
    typ_path = OUTPUT_DIR / f"cv-{slug}-{lang}.typ"

    result = compile_typst_and_extract(
        typst_code=typst_code,
        output_pdf_path=pdf_path,
        output_typ_path=typ_path,
        root_dir=PROJECT_ROOT,
        lang=lang
    )

    # Se teve sucesso, grava o texto plano extraído
    if result.success and result.extracted_text:
        txt_path = OUTPUT_DIR / f"resume-{slug}.txt"
        txt_path.write_text(result.extracted_text, encoding="utf-8")

    return result