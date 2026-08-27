import re
from src.state import CVState
from src.tools.file_manager import write_file
from src.tools.typst_runner import compile_typst_to_pdf, extract_text_from_pdf
from src.config import OUTPUT_DIR

def sanitize_typst_syntax(content: str, lang: str = "pt") -> str:
    """Automatically fixes common syntax issues before compiling (Cost: 0 tokens)."""
    if not content:
        return ""

    # 1. Remove invalid hallucinations like '#set lang: "pt-br"' or '#set lang(...)'
    content = re.sub(r'#set\s+lang\s*[:\(][^\n\)]*[\)\n]?', '', content)

    # 2. Normalize template.typ paths and quotes pointing to templates/
    content = re.sub(
        r'#import\s+[\'"].*?template\.typ[\'"](?:\s*:\s*([^;\n]+))?',
        r'#import "../templates/template.typ": columns-2, CV',
        content
    )

    # 3. Convert single quotes into Typst commands for double quotes
    content = re.sub(r'#link\(\s*\'([^\']+)\'\s*\)', r'#link("\1")', content)
    content = re.sub(r'lang:\s*\'([^\']+)\'', r'lang: "\1"', content)

    # 4. Escape '@' in npm/libs packages to avoid collision with Typst reference labels
    content = re.sub(r'(?<![\w\\])@([a-zA-Z0-9_\-\/]+)', r'\\@\1', content)

    # 5. Ensure that the template and show-rule exist at the top of the file if omitted
    if '#import "../templates/template.typ"' not in content:
        content = f'#import "../templates/template.typ": columns-2, CV\n\n#show: CV.with(lang: "{lang}")\n\n' + content
    elif "#show: CV.with" not in content:
        content = re.sub(
            r'(#import\s+"\.\./templates/template\.typ":\s*columns-2,\s*CV)',
            rf'\1\n\n#show: CV.with(lang: "{lang}")',
            content
        )

    return content


def typst_compiler_node(state: CVState) -> dict:
    slug = state.get("job_slug") or "cv-tailored"
    lang = state.get("job_lang") or "pt"
    temp_typ_path = OUTPUT_DIR / f"cv-{slug}-{lang}.typ"
    temp_pdf_path = OUTPUT_DIR / f"cv-{slug}-{lang}.pdf"

    raw_content = state.get("typ_content", "")
    clean_content = sanitize_typst_syntax(raw_content, lang=lang)

    write_file(temp_typ_path, clean_content)

    success, msg = compile_typst_to_pdf(temp_typ_path, temp_pdf_path)
    
    if not success:
        current_errors = state.get("syntax_error_count", 0) + 1
        return {
            "typ_content": clean_content,
            "pdf_path": "",
            "txt_content": "",
            "typ_error": msg,
            "syntax_error_count": current_errors
        }

    try:
        extracted_text = extract_text_from_pdf(temp_pdf_path)
    except Exception as e:
        return {
            "typ_content": clean_content,
            "pdf_path": str(temp_pdf_path),
            "txt_content": "",
            "typ_error": f"Erro ao extrair texto do PDF gerado: {e}",
            "syntax_error_count": state.get("syntax_error_count", 0) + 1
        }

    return {
        "typ_content": clean_content,
        "pdf_path": str(temp_pdf_path),
        "txt_content": extracted_text,
        "typ_error": "",
        "syntax_error_count": 0
    }