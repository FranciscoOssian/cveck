import json
from pathlib import Path
from typing import List, Dict, Any

from mcp.server.mcpserver import MCPServer

from src.core.models.job import JobTerm
from src.core.models.gap import GapItem
from src.core.services.typst import compile_typst_and_extract
from src.core.services.ats import calculate_ats_metrics
from src.core.services.backlog import update_gaps_backlog
from src.core.workflow.evaluators import check_ats_condition
from src.core.workflow.schema import Policies
from src.adapters.mcp.prompt import get_workflow_instructions
from src.core.paths import PROJECT_ROOT, DOC_DIR, OUTPUT_DIR

POLICIES = Policies()

# Inicialização do servidor MCPServer oficial
mcp = MCPServer(
    name="cveck",
    instructions=(
        "Cveck 2.0: Motor autônomo de adequação de currículos e ATS. "
        "DIRETRIZ DE INICIALIZAÇÃO: Ao receber uma vaga, chame a ferramenta 'start_resume_tailoring' "
        "para carregar o perfil factual e as regras do workflow. "
        "IMPORTANTE: Caso você JÁ TENHA RECEBIDO o perfil do usuário (USER_PROFILE.md) e as instruções do workflow "
        "no prompt inicial, DESCONSIDERE 'start_resume_tailoring' e prossiga diretamente para 'submit_job_terms'."
    )
)

# --- PROMPT DO MCP ---

@mcp.prompt(name="tailor_resume")
def tailor_resume(job_description: str) -> str:
    """Inicia o processo de tailoring injetando o perfil real, guia de estilo e o roteiro de ferramentas."""
    return get_workflow_instructions(job_description)

# --- FERRAMENTAS DO MCP ---

@mcp.tool()
def start_resume_tailoring(job_description: str) -> str:
    """CHAME ESTA FERRAMENTA PRIMEIRO ao receber uma vaga alvo para carregar o perfil factual (USER_PROFILE.md), 
    o guia de estilo e a máquina de estados."""
    return get_workflow_instructions(job_description)

@mcp.tool()
def submit_job_terms(
    job_title: str,
    company_name: str,
    job_slug: str,
    job_lang: str,
    terms: List[Dict[str, Any]]
) -> str:
    """Registra os termos técnicos, cargo, empresa e idioma identificados na vaga alvo."""
    slug = job_slug or "cv-tailored"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parsed_terms = [JobTerm.model_validate(t) for t in terms]
    terms_file = OUTPUT_DIR / f"job_terms-{slug}.json"
    terms_file.write_text(
        json.dumps([t.model_dump() for t in parsed_terms], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    req_count = sum(1 for t in parsed_terms if t.required)
    opt_count = len(parsed_terms) - req_count

    return (
        f"✔ Vaga '{job_title}' @ '{company_name}' registrada com sucesso.\n"
        f"Total de {len(parsed_terms)} termos ({req_count} obrigatórios, {opt_count} diferenciais) salvos em {terms_file.name}.\n"
        "Próximo passo: Chame 'record_gaps' se houver lacunas reais, ou passe para a geração e chame 'compile_typst'."
    )

@mcp.tool()
def record_gaps(gaps: List[Dict[str, Any]], job_title: str = "", company_name: str = "") -> str:
    """Registra lacunas técnicas reais no backlog de estudos (doc/GAPS.md e doc/gaps.json)."""
    if not gaps:
        return "Nenhum gap fornecido. Prossiga para a geração do código Typst e chame 'compile_typst'."

    parsed_gaps = [
        GapItem(
            term=g.get("term", ""),
            category=g.get("category", "other"),
            required=g.get("required", False),
            vaga=job_title or g.get("vaga", ""),
            empresa=company_name or g.get("empresa", ""),
            data=g.get("data", ""),
            motivo=g.get("motivo", ""),
            sugestao=g.get("sugestao", "")
        )
        for g in gaps
    ]

    update_gaps_backlog(parsed_gaps, DOC_DIR / "gaps.json", DOC_DIR / "GAPS.md")
    gap_names = [g.term for g in parsed_gaps]

    return (
        f"✔ {len(parsed_gaps)} gap(s) registrados no backlog doc/GAPS.md: {gap_names}.\n"
        "Lembrete de conformidade: É PROIBIDO incluir essas competências no currículo gerado.\n"
        "Próximo passo: Escreva o código Typst seguindo o CV_STYLE_GUIDE.md e chame 'compile_typst'."
    )

@mcp.tool()
def compile_typst(typst_code: str, job_slug: str = "cv-tailored", lang: str = "en") -> str:
    """Compila o código Typst localmente, sanitiza a sintaxe e extrai o texto plano do PDF."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_DIR / f"cv-{job_slug}-{lang}.pdf"
    typ_path = OUTPUT_DIR / f"cv-{job_slug}-{lang}.typ"
    txt_path = OUTPUT_DIR / f"resume-{job_slug}.txt"

    res = compile_typst_and_extract(
        typst_code=typst_code,
        output_pdf_path=pdf_path,
        output_typ_path=typ_path,
        root_dir=PROJECT_ROOT,
        lang=lang
    )

    if not res.success:
        return (
            "❌ ERRO DE COMPILAÇÃO TYPST:\n"
            f"{res.error_message}\n\n"
            "Ação obrigatória: Corrija o código Typst mantendo todos os fechamentos de chaves e aspas "
            "e chame 'compile_typst' novamente com a versão corrigida."
        )

    txt_path.write_text(res.extracted_text, encoding="utf-8")

    return (
        f"✔ PDF compilado com sucesso!\n"
        f"- Arquivo: {pdf_path}\n"
        f"- Texto extraído: {len(res.extracted_text)} caracteres salvos em {txt_path.name}.\n"
        "Próximo passo: Chame 'validate_ats' para testar a aderência matemática dos termos da vaga."
    )

@mcp.tool()
def validate_ats(job_slug: str = "cv-tailored") -> str:
    """Calcula pontuação matemática ATS e verifica alertas de keyword stuffing (> 2%)."""
    terms_file = OUTPUT_DIR / f"job_terms-{job_slug}.json"
    txt_file = OUTPUT_DIR / f"resume-{job_slug}.txt"

    if not terms_file.exists():
        return f"Erro: Arquivo '{terms_file.name}' não encontrado. Chame 'submit_job_terms' primeiro."
    if not txt_file.exists():
        return f"Erro: Arquivo '{txt_file.name}' não encontrado. Chame 'compile_typst' com sucesso primeiro."

    raw_terms = json.loads(terms_file.read_text(encoding="utf-8"))
    job_terms = [JobTerm.model_validate(t) for t in raw_terms]
    resume_text = txt_file.read_text(encoding="utf-8")

    report = calculate_ats_metrics(
        job_terms=job_terms,
        resume_text=resume_text,
        stuffing_threshold=POLICIES.stuffing_density_threshold
    )

    from src.core.models.state import DomainState
    dummy_state = DomainState(ats_report=report)
    condition = check_ats_condition(dummy_state, POLICIES)

    msg = [
        "📊 RELATÓRIO TÉCNICO ATS:",
        f"- Pontuação Geral: {report.score}/100 (Meta mínima: {POLICIES.target_ats_score})",
        f"- Cobertura de Requisitos Obrigatórios: {report.coverage_required_pct}%",
        f"- Cobertura Geral de Palavras-chave: {report.coverage_pct}%",
    ]

    if report.missing_required:
        msg.append(f"- Obrigatórios Ausentes: {', '.join(report.missing_required)}")
    if report.missing_optional:
        msg.append(f"- Diferenciais Ausentes: {', '.join(report.missing_optional)}")
    if report.stuffing_flags:
        msg.append(f"⚠ Alerta de Keyword Stuffing (>2%): {report.stuffing_flags}")

    if condition == "approved":
        msg.append("\n🎉 RESULTADO: APROVADO! Meta atingida com zero requisitos obrigatórios ausentes.")
        msg.append("Ação: Chame 'commit_cv' para consolidar o relatório final.")
    elif condition == "unfixable_gaps":
        msg.append("\n🛑 RESULTADO: APROVAÇÃO POR SHORT-CIRCUIT.")
        msg.append("Todos os termos obrigatórios faltantes são Gaps reais comprovados no perfil. O currículo atingiu o limite factual.")
        msg.append("Ação: Chame 'commit_cv' para consolidar o relatório final.")
    else:
        msg.append("\n↻ RESULTADO: NECESSITA REFINAMENTO.")
        msg.append("Ação: Reescreva bullets existentes no Typst para incluir os termos faltantes (caso existam no perfil) e chame 'compile_typst'.")

    return "\n".join(msg)

@mcp.tool()
def commit_cv(job_slug: str = "cv-tailored", lang: str = "en") -> str:
    """Consolida os artefatos finais no diretório output/ e emite o resumo de encerramento."""
    pdf_path = OUTPUT_DIR / f"cv-{job_slug}-{lang}.pdf"
    txt_path = OUTPUT_DIR / f"resume-{job_slug}.txt"
    terms_path = OUTPUT_DIR / f"job_terms-{job_slug}.json"

    if not pdf_path.exists():
        return f"Erro: PDF final '{pdf_path.name}' não encontrado. Certifique-se de compilar o currículo antes."

    return (
        "✦ PROCESSO CONCLUÍDO COM SUCESSO!\n"
        f"- PDF Vetorial: {pdf_path}\n"
        f"- Texto Plaintext: {txt_path}\n"
        f"- Termos JSON: {terms_path}\n"
        "Todos os artefatos foram salvos localmente. O currículo está pronto para envio!"
    )

def run_mcp_server():
    """Inicia o servidor MCP via stdio."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    run_mcp_server()