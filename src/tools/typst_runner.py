import subprocess
from pathlib import Path
from src.i18n import _
from typing import Tuple
from src.config import BASE_DIR


def compile_typst_to_pdf(typ_path: Path, pdf_path: Path) -> Tuple[bool, str]:
    """Compile Typst file to PDF passing --root to repository root."""
    try:
        cmd = [
            "typst", "compile",
            "--root", str(BASE_DIR),
            str(typ_path),
            str(pdf_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"{_('Error compiling Typst:')} {e.stderr}"
    except FileNotFoundError:
         return False, _("The 'typst' binary is not installed in the system PATH.")


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from PDF using pdftotext (Poppler)."""
    try:
        cmd = ["pdftotext", "-layout", str(pdf_path), "-"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"{_('Error extracting text with pdftotext:')} {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError(_("The 'pdftotext' binary is not installed in the system PATH."))