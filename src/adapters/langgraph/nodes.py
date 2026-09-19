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


def _read_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def term_extractor_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.1)
    llm_tools = llm.bind_tools([TermExtractorResponse])
    prompt = _read_prompt("extract_terms.md")

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Job description:\n\n{state.job_description}")
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

    terms_dump = "\n".join([f"- {t.term} (Mandatory: {t.required})" for t in state.job_terms])
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"CANDIDATE PROFILE:\n{profile}\n\nJOB TERMS:\n{terms_dump}\n\nApplication Date: {state.job_date}")
    ]
    res = llm_tools.invoke(messages)
    tokens = extract_token_usage(res)

    if res.tool_calls:
        parsed = RecordGaps.model_validate(res.tool_calls[0]["args"])
    else:
        parsed = extract_and_parse_json(str(res.content), RecordGaps)

    for g in parsed.real_gaps:
        g.job_title = state.job_title
        g.company_name = state.company_name
        g.date = state.job_date

    return {
        "detected_gaps": parsed.real_gaps,
        "token_usage": accumulate_tokens(state.token_usage, "gap_finder", tokens),
        "last_step_tokens": tokens
    }


def gaps_updater_node(state: LangGraphState) -> dict:
    """Deterministic Core node: persists gaps to doc/GAPS.md and doc/gaps.json."""
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

    terms_str = ", ".join([f"{t.term} ({'mandatory' if t.required else 'optional'})" for t in state.job_terms])
    gaps_str = ", ".join([g.term for g in state.detected_gaps]) or "None"

    user_content = (
        f"STYLE GUIDE:\n{style_guide}\n\n"
        f"BASE TEMPLATE:\n{base_template}\n\n"
        f"FACTUAL PROFILE:\n{profile}\n\n"
        f"TARGET JOB: {state.job_title} @ {state.company_name} ({lang})\n"
        f"JOB KEYWORDS: {terms_str}\n"
        f"PROHIBITED GAPS (DO NOT HALLUCINATE OR MENTION): {gaps_str}\n\n"
        "Generate the complete Typst code following the style guide and submit it via SubmitTypstCV."
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
        root_dir=PROJECT_ROOT,
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
        f"TYPST COMPILER ERROR:\n{state.typ_error}\n\n"
        f"CODE WITH ERROR:\n{state.typ_content}\n\n"
        "Fix the syntax error ensuring all delimiters and imports are closed, and resubmit via SubmitTypstCV."
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
            feedback.append(f"• Missing Mandatory: {', '.join(ats.missing_required)}")
        if ats.missing_optional:
            feedback.append(f"• Missing Optional: {', '.join(ats.missing_optional)}")
        if ats.stuffing_flags:
            feedback.append(f"• Excessive Repetition Alert (Stuffing): {ats.stuffing_flags}")
        feedback.append(f"• Current Score: {ats.score}/100")

    user_content = (
        f"STYLE GUIDE:\n{style_guide}\n\n"
        f"FACTUAL PROFILE:\n{profile}\n\n"
        f"ATS REPORT:\n{chr(10).join(feedback)}\n\n"
        f"PREVIOUS CODE:\n{state.typ_content}\n\n"
        "Refine the bullets to cover missing terms backed by the profile and submit via SubmitTypstCV."
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


def committer_node(state: LangGraphState) -> dict:
    """Deterministic node: persists artifacts to output/ and returns raw domain state."""
    slug = state.job_slug or "cv-tailored"
    lang = state.job_lang or "en"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    terms_data = [t.model_dump() for t in state.job_terms]
    (OUTPUT_DIR / f"job_terms-{slug}.json").write_text(
        json.dumps(terms_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / f"resume-{slug}.txt").write_text(state.txt_content, encoding="utf-8")

    pdf_file = OUTPUT_DIR / f"cv-{slug}-{lang}.pdf"

    return {
        "job_title": state.job_title,
        "company_name": state.company_name,
        "job_slug": slug,
        "job_lang": lang,
        "pdf_path": str(pdf_file) if pdf_file.exists() and not state.typ_error else "",
        "typ_error": state.typ_error,
        "syntax_error_count": state.syntax_error_count,
        "ats_report": state.ats_report,
        "is_approved": state.is_approved,
        "iteration": state.iteration,
        "detected_gaps": state.detected_gaps,
        "token_usage": state.token_usage,
    }