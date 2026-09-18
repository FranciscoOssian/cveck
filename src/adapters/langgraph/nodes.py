import json
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage

from src.adapters.langgraph.state import LangGraphState
from src.core.models.job import TermExtractorResponse
from src.core.models.gap import RecordGaps
from src.core.models.typst import SubmitTypstCV
from src.core.services.typst import compile_typst_and_extract
from src.core.services.ats import calculate_ats_metrics
from src.core.services.backlog import update_gaps_backlog
from src.core.services.parser import extract_and_parse_json
from src.core.context import load_user_profile, resolve_template_skeleton
from src.adapters.langgraph.providers.registry import get_dynamic_llm
from src.adapters.langgraph.providers.token_tracker import extract_token_usage, accumulate_tokens
from src.core.paths import (
      PROJECT_ROOT,
      DOC_DIR,
      OUTPUT_DIR,
      ASSETS_DIR,
      PROMPTS_DIR,
      TEMPLATES_DIR
  )

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "assets"
PROMPTS_DIR = ASSETS_DIR / "prompts"
TEMPLATES_DIR = ASSETS_DIR / "templates"
DOC_DIR = Path.cwd() / "doc"
OUTPUT_DIR = Path.cwd() / "output"


def _read_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def term_extractor_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.1)
    llm_tools = llm.bind_tools([TermExtractorResponse])
    prompt = _read_prompt("extract_terms.md")

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Descrição da vaga:\n\n{state.job_description}")
    ]
    res = llm_tools.invoke(messages)
    tokens = extract_token_usage(res)

    if res.tool_calls:
        parsed = TermExtractorResponse.model_validate(res.tool_calls[0]["args"])
    else:
        parsed = extract_and_parse_json(str(res.content), TermExtractorResponse)

    return {
        "job_terms": parsed.terms,
        "job_title": parsed.job_title,
        "company_name": parsed.company_name,
        "job_slug": parsed.job_slug,
        "job_lang": parsed.job_lang,
        "token_usage": accumulate_tokens(state.token_usage, "term_extractor", tokens),
        "last_step_tokens": tokens
    }


def gap_finder_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.0)
    llm_tools = llm.bind_tools([RecordGaps])
    profile = load_user_profile(DOC_DIR)
    prompt = _read_prompt("find_gaps.md")

    terms_dump = "\n".join([f"- {t.term} (Obrigatório: {t.required})" for t in state.job_terms])
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"PERFIL:\n{profile}\n\nTERMOS DA VAGA:\n{terms_dump}\n\nData: {state.job_date}")
    ]
    res = llm_tools.invoke(messages)
    tokens = extract_token_usage(res)

    if res.tool_calls:
        parsed = RecordGaps.model_validate(res.tool_calls[0]["args"])
    else:
        parsed = extract_and_parse_json(str(res.content), RecordGaps)

    for g in parsed.real_gaps:
        g.vaga = state.job_title
        g.empresa = state.company_name
        g.data = state.job_date

    return {
        "detected_gaps": parsed.real_gaps,
        "token_usage": accumulate_tokens(state.token_usage, "gap_finder", tokens),
        "last_step_tokens": tokens
    }


def gaps_updater_node(state: LangGraphState) -> dict:
    """Nó determinístico do Core: salva em doc/GAPS.md e doc/gaps.json."""
    update_gaps_backlog(
        state.detected_gaps,
        DOC_DIR / "gaps.json",
        DOC_DIR / "GAPS.md"
    )
    return {}


def cv_generator_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.1)
    llm_tools = llm.bind_tools([SubmitTypstCV])
    profile = load_user_profile(DOC_DIR)
    style_guide = _read_prompt("CV_STYLE_GUIDE.md")
    prompt = _read_prompt("generate_cv.md")
    base_template, lang = resolve_template_skeleton(TEMPLATES_DIR, state.job_lang)

    terms_str = ", ".join([f"{t.term} ({'obrigatório' if t.required else 'diferencial'})" for t in state.job_terms])
    gaps_str = ", ".join([g.term for g in state.detected_gaps]) or "Nenhum"

    user_content = (
        f"STYLE GUIDE:\n{style_guide}\n\n"
        f"TEMPLATE BASE:\n{base_template}\n\n"
        f"PERFIL REAL:\n{profile}\n\n"
        f"VAGA: {state.job_title} @ {state.company_name} ({lang})\n"
        f"TERMOS: {terms_str}\n"
        f"GAPS PROIBIDOS DE ALUCINAR: {gaps_str}\n\n"
        "Gere o código Typst completo preenchendo o template e envie via SubmitTypstCV."
    )
    res = llm_tools.invoke([SystemMessage(content=prompt), HumanMessage(content=user_content)])
    tokens = extract_token_usage(res)

    code = res.tool_calls[0]["args"].get("typst_code", "") if res.tool_calls else str(res.content)
    return {
        "typ_content": code,
        "iteration": 1,
        "token_usage": accumulate_tokens(state.token_usage, "cv_generator", tokens),
        "last_step_tokens": tokens
    }


def typst_compiler_node(state: LangGraphState) -> dict:
    slug = state.job_slug or "cv-tailored"
    lang = state.job_lang or "en"
    pdf_path = OUTPUT_DIR / f"cv-{slug}-{lang}.pdf"
    typ_path = OUTPUT_DIR / f"cv-{slug}-{lang}.typ"

    result = compile_typst_and_extract(
        typst_code=state.typ_content,
        output_pdf_path=pdf_path,
        output_typ_path=typ_path,
        root_dir=PROJECT_ROOT,  # Ancorado na raiz real do CVECK
        lang=lang
    )

    if not result.success:
        return {
            "typ_error": result.error_message,
            "syntax_error_count": state.syntax_error_count + 1
        }

    return {
        "pdf_path": result.pdf_path,
        "txt_content": result.extracted_text,
        "typ_error": "",
        "syntax_error_count": 0
    }


def typst_fixer_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.0)
    llm_tools = llm.bind_tools([SubmitTypstCV])
    prompt = _read_prompt("fix_typst.md")

    user_content = (
        f"ERRO DO COMPILADOR TYPST:\n{state.typ_error}\n\n"
        f"CÓDIGO COM ERRO:\n{state.typ_content}\n\n"
        "Corrija a sintaxe mantendo todas as chaves e imports fechados e reenvie via SubmitTypstCV."
    )
    res = llm_tools.invoke([SystemMessage(content=prompt), HumanMessage(content=user_content)])
    tokens = extract_token_usage(res)
    code = res.tool_calls[0]["args"].get("typst_code", "") if res.tool_calls else str(res.content)

    return {
        "typ_content": code,
        "token_usage": accumulate_tokens(state.token_usage, "typst_fixer", tokens),
        "last_step_tokens": tokens
    }


def ats_validator_node(state: LangGraphState) -> dict:
    report = calculate_ats_metrics(state.job_terms, state.txt_content)
    is_approved = (not report.hard_fail) and (report.score >= 85.0)
    return {
        "ats_report": report,
        "is_approved": is_approved
    }


def cv_refiner_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.1)
    llm_tools = llm.bind_tools([SubmitTypstCV])
    prompt = _read_prompt("refine_cv.md")
    style_guide = _read_prompt("CV_STYLE_GUIDE.md")
    profile = load_user_profile(DOC_DIR)
    ats = state.ats_report

    feedback = []
    if ats:
        if ats.missing_required:
            feedback.append(f"• Obrigatórios Ausentes: {', '.join(ats.missing_required)}")
        if ats.missing_optional:
            feedback.append(f"• Diferenciais Ausentes: {', '.join(ats.missing_optional)}")
        if ats.stuffing_flags:
            feedback.append(f"• Alerta de Repetição Excessiva (Stuffing): {ats.stuffing_flags}")
        feedback.append(f"• Nota Atual: {ats.score}/100")

    user_content = (
        f"STYLE GUIDE:\n{style_guide}\n\n"
        f"PERFIL:\n{profile}\n\n"
        f"RELATÓRIO ATS:\n{chr(10).join(feedback)}\n\n"
        f"CÓDIGO ANTERIOR:\n{state.typ_content}\n\n"
        "Ajuste os bullets reescrevendo para incluir termos faltantes que existam no perfil e envie via SubmitTypstCV."
    )
    res = llm_tools.invoke([SystemMessage(content=prompt), HumanMessage(content=user_content)])
    tokens = extract_token_usage(res)
    code = res.tool_calls[0]["args"].get("typst_code", "") if res.tool_calls else str(res.content)

    return {
        "typ_content": code,
        "iteration": state.iteration + 1,
        "token_usage": accumulate_tokens(state.token_usage, "cv_refiner", tokens),
        "last_step_tokens": tokens
    }


def _build_final_summary(state: LangGraphState, slug: str, lang: str) -> str:
    """Relatório estruturado com dados de ATS, Gaps e telemetria da API."""
    ats = state.ats_report
    job_title = state.job_title or "Software Developer"
    company = state.company_name or "Company"
    status_label = "Aprovado" if state.is_approved else "Reprovado"

    missing_req = ", ".join(ats.missing_required) if ats and ats.missing_required else "Nenhum"
    missing_opt = ", ".join(ats.missing_optional) if ats and ats.missing_optional else "Nenhum"

    sep = "=" * 50
    lines = [
        sep,
        f" RELATÓRIO TÉCNICO ATS: {job_title} ({company})",
        sep,
        f"Status: {status_label}",
        f"Pontuação Geral: {ats.score if ats else 0}/100",
        f"Tentativas Realizadas: {max(state.iteration, 1)}",
        f"Cobertura de Requisitos Obrigatórios: {ats.coverage_required_pct if ats else 0}%",
        f"Cobertura Geral de Palavras-chave: {ats.coverage_pct if ats else 0}%",
        "",
        f"Obrigatórios Ausentes: {missing_req}",
        f"Diferenciais Ausentes: {missing_opt}",
    ]

    if ats and ats.stuffing_flags:
        lines.append(f"Alerta de Repetição Excessiva (Stuffing): {ats.stuffing_flags}")

    if state.detected_gaps:
        gap_names = [g.term for g in state.detected_gaps]
        lines.append(f"Gaps Adicionados ao Backlog (doc/GAPS.md): {gap_names}")

    lines.append(f"PDF gerado em: {OUTPUT_DIR}/cv-{slug}-{lang}.pdf")

    # Métrica de telemetria que pertence exclusivamente ao LangGraph
    tokens_info = state.token_usage or {}
    total_tok = tokens_info.get("total_tokens", 0)
    in_tok = tokens_info.get("input_tokens", 0)
    out_tok = tokens_info.get("output_tokens", 0)
    if total_tok > 0:
        lines.append("")
        lines.append(
            f"Consumo Total de Tokens: {total_tok:,} (Prompt: {in_tok:,} | Completion: {out_tok:,})"
        )

    return "\n".join(lines)


def committer_node(state: LangGraphState) -> dict:
    """Nó determinístico: grava artefatos finais em output/ e consolida o relatório."""
    slug = state.job_slug or "cv-tailored"
    lang = state.job_lang or "en"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    terms_data = [t.model_dump() for t in state.job_terms]
    (OUTPUT_DIR / f"job_terms-{slug}.json").write_text(
        json.dumps(terms_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / f"resume-{slug}.txt").write_text(state.txt_content, encoding="utf-8")

    summary = _build_final_summary(state, slug, lang)
    return {"final_summary": summary}