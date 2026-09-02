import typst
import pymupdf as fitz
from pathlib import Path
from src.i18n import _
from typing import Tuple, cast
from src.config import BASE_DIR


def compile_typst_to_pdf(typ_path: Path, pdf_path: Path) -> Tuple[bool, str]:
    """Compile Typst file to PDF passing --root to repository root."""
    try:
        typst.compile(
            str(typ_path),
            output=str(pdf_path),
            root=str(BASE_DIR),
        )
        return True, ""
    except Exception as e:
         return False, str(e)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from PDF using pdftotext (Poppler)."""
    try:
        with fitz.open(str(pdf_path)) as doc:
            texts: list[str] = []

            for page in doc:
                text = cast(str, page.get_text("text"))
                texts.append(text)

            return "\n".join(texts)

    except Exception as e:
        raise RuntimeError(
            f"{_('Error extracting text from PDF:')} {e}"
        ) from e