import os
import re
from pathlib import Path
from typing import Optional
import typst
import pymupdf as fitz

from src.core.models.typst import CompilationResult
from src.core.paths import PROJECT_ROOT, ASSETS_DIR, OUTPUT_DIR


def resolve_template_import_path(output_typ_path: Optional[Path] = None) -> str:
    """
    Locates where template.typ resides with a cwd-immune fallback
    and computes the correct relative path with respect to the target .typ directory.
    """
    candidates = [
        ASSETS_DIR / "templates" / "template.typ",
        PROJECT_ROOT / "templates" / "template.typ",
    ]
    template_file = next((p for p in candidates if p.exists()), candidates[0])

    # Base directory where the .typ file will be generated
    base_dir = output_typ_path.parent if output_typ_path else OUTPUT_DIR

    try:
        rel_path = os.path.relpath(template_file, base_dir)
        return Path(rel_path).as_posix()
    except ValueError:
        # Fallback for distinct drives on Windows
        return Path(template_file).as_posix()


def sanitize_typst_syntax(content: str, lang: str = "pt", output_typ_path: Optional[Path] = None) -> str:
    """Sanitizes Typst source code prior to compilation (Cost: 0 tokens)."""
    if not content:
        return ""

    # 1. Strip <think> tags and markdown fences
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    content = re.sub(r"```(?:typst)?", "", content).replace("```", "").strip()

    # 2. Remove hallucinations like '#set lang: "pt-br"'
    content = re.sub(r'#set\s+lang\s*[:\(][^\n\)]*[\)\n]?', '', content)

    # 3. Dynamically detect actual relative path to template.typ
    template_path = resolve_template_import_path(output_typ_path=output_typ_path)

    # 4. Normalize any template.typ import to the actual relative path
    content = re.sub(
        r'#import\s+[\'"][^\'"]*template\.typ[\'"](?:\s*:\s*([^;\n]+))?',
        rf'#import "{template_path}": columns-2, CV',
        content
    )

    # 5. Convert single quotes in Typst commands to double quotes
    content = re.sub(r'#link\(\s*\'([^\']+)\'\s*\)', r'#link("\1")', content)
    content = re.sub(r'lang:\s*\'([^\']+)\'', r'lang: "\1"', content)

    # 6. Escape '@' in npm packages to prevent collision with Typst reference labels
    content = re.sub(r'(?<![\w\\])@([a-zA-Z0-9_\-\/]+)', r'\\@\1', content)

    # 7. Ensure template import and show rule exist at the top
    if '#show: CV.with' not in content:
        if f'#import "{template_path}"' not in content:
            content = f'#import "{template_path}": columns-2, CV\n\n#show: CV.with(lang: "{lang}")\n\n' + content
        else:
            content = re.sub(
                rf'(#import\s+"{re.escape(template_path)}":\s*columns-2,\s*CV)',
                rf'\1\n\n#show: CV.with(lang: "{lang}")',
                content
            )

    return content.strip()


def compile_typst_and_extract(
    typst_code: str,
    output_pdf_path: Path,
    output_typ_path: Path,
    root_dir: Optional[Path] = None,
    lang: str = "pt"
) -> CompilationResult:
    """Writes the .typ file, compiles via Typst, and extracts plaintext with PyMuPDF."""
    target_root = root_dir or PROJECT_ROOT
    clean_code = sanitize_typst_syntax(typst_code, lang=lang, output_typ_path=output_typ_path)
    output_typ_path.parent.mkdir(parents=True, exist_ok=True)
    output_typ_path.write_text(clean_code, encoding="utf-8")

    try:
        typst.compile(str(output_typ_path), output=str(output_pdf_path), root=str(target_root))
    except Exception as e:
        return CompilationResult(success=False, error_message=str(e))

    try:
        with fitz.open(str(output_pdf_path)) as doc:
            extracted_text = "\n".join(page.get_text("text") for page in doc)
        return CompilationResult(
            success=True,
            pdf_path=str(output_pdf_path),
            extracted_text=extracted_text
        )
    except Exception as e:
        return CompilationResult(
            success=False,
            pdf_path=str(output_pdf_path),
            error_message=f"Failed to extract text from generated PDF: {e}"
        )