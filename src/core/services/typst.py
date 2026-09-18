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
    Detecta onde o template.typ está localizado com fallback imune ao cwd
    e calcula o caminho relativo correto em relação ao diretório do arquivo .typ.
    """
    candidates = [
        ASSETS_DIR / "templates" / "template.typ",
        PROJECT_ROOT / "templates" / "template.typ",
    ]
    template_file = next((p for p in candidates if p.exists()), candidates[0])

    # Diretório base onde o arquivo .typ será gerado
    base_dir = output_typ_path.parent if output_typ_path else OUTPUT_DIR

    try:
        rel_path = os.path.relpath(template_file, base_dir)
        return Path(rel_path).as_posix()
    except ValueError:
        # Fallback para drives distintos no Windows
        return Path(template_file).as_posix()


def sanitize_typst_syntax(content: str, lang: str = "pt", output_typ_path: Optional[Path] = None) -> str:
    """Sanitiza código Typst antes da compilação (Custo: 0 tokens)."""
    if not content:
        return ""

    # 1. Limpa tags <think> e blocos markdown
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    content = re.sub(r"```(?:typst)?", "", content).replace("```", "").strip()

    # 2. Remove alucinações como '#set lang: "pt-br"'
    content = re.sub(r'#set\s+lang\s*[:\(][^\n\)]*[\)\n]?', '', content)

    # 3. Detecta dinamicamente o path real do template.typ em relação ao destino
    template_path = resolve_template_import_path(output_typ_path=output_typ_path)

    # 4. Normaliza qualquer importação de template.typ para o path relativo real
    content = re.sub(
        r'#import\s+[\'"][^\'"]*template\.typ[\'"](?:\s*:\s*([^;\n]+))?',
        rf'#import "{template_path}": columns-2, CV',
        content
    )

    # 5. Converte aspas simples de comandos Typst para aspas duplas
    content = re.sub(r'#link\(\s*\'([^\']+)\'\s*\)', r'#link("\1")', content)
    content = re.sub(r'lang:\s*\'([^\']+)\'', r'lang: "\1"', content)

    # 6. Escapa '@' em pacotes npm para não colidir com rótulos de referência do Typst
    content = re.sub(r'(?<![\w\\])@([a-zA-Z0-9_\-\/]+)', r'\\@\1', content)

    # 7. Garante import e show rule no topo
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
    """Grava o .typ, compila com Typst e extrai texto plano com PyMuPDF."""
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
            error_message=f"Falha ao extrair texto do PDF gerado: {e}"
        )