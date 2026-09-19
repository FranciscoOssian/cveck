from pathlib import Path
from src.adapters.langgraph.state import LangGraphState
from src.adapters.langgraph.providers.registry import get_dynamic_llm
from src.adapters.langgraph.providers.token_tracker import extract_token_usage, accumulate_tokens

from src.core.use_cases.extract_terms import execute_extract_terms
from src.core.use_cases.find_gaps import execute_find_gaps
from src.core.use_cases.update_gaps import execute_update_gaps
from src.core.use_cases.generate_cv import execute_generate_cv
from src.core.use_cases.compile_cv import execute_compile_cv
from src.core.use_cases.fix_typst import execute_fix_typst
from src.core.use_cases.validate_ats import execute_validate_ats
from src.core.use_cases.refine_cv import execute_refine_cv
from src.core.use_cases.commit_artifacts import execute_commit_artifacts
from src.core.workflow.schema import WorkflowConfig
from src.core.paths import CORE_DIR


_WORKFLOW_CFG = WorkflowConfig.model_validate(
    __import__("yaml").safe_load((CORE_DIR / "workflow.yaml").read_text(encoding="utf-8"))
)
_POLICIES = _WORKFLOW_CFG.policies


def term_extractor_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.1)
    parsed, tokens = execute_extract_terms(state.job_description, llm)

    return {
        "job_terms": parsed.terms,
        "job_title": parsed.job_title,
        "company_name": parsed.company_name,
        "job_slug": parsed.job_slug,  # Já sanitizado pelo Pydantic!
        "job_lang": parsed.job_lang,  # Já limpo pelo Pydantic!
        "token_usage": accumulate_tokens(state.token_usage, "term_extractor", tokens),
        "last_step_tokens": tokens,
    }


def gap_finder_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.0)
    real_gaps, tokens = execute_find_gaps(
        job_terms=state.job_terms,
        job_title=state.job_title,
        company_name=state.company_name,
        job_date=state.job_date,
        llm=llm
    )

    return {
        "detected_gaps": real_gaps,
        "token_usage": accumulate_tokens(state.token_usage, "gap_finder", tokens),
        "last_step_tokens": tokens,
    }


def gaps_updater_node(state: LangGraphState) -> dict:
    execute_update_gaps(state.detected_gaps)
    return {}


def cv_generator_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.1)
    code = execute_generate_cv(
        job_terms=state.job_terms,
        detected_gaps=state.detected_gaps,
        job_title=state.job_title,
        company_name=state.company_name,
        job_lang=state.job_lang,
        llm=llm
    )
    tokens = extract_token_usage(getattr(llm, "last_response", None))

    return {
        "typ_content": code,
        "iteration": 1,
        "token_usage": accumulate_tokens(state.token_usage, "cv_generator", tokens),
        "last_step_tokens": tokens,
    }


def typst_compiler_node(state: LangGraphState) -> dict:
    result = execute_compile_cv(
        typst_code=state.typ_content,
        job_slug=state.job_slug,
        job_lang=state.job_lang
    )

    if not result.success:
        return {
            "typ_error": result.error_message,
            "syntax_error_count": state.syntax_error_count + 1,
        }

    return {
        "pdf_path": result.pdf_path,
        "txt_content": result.extracted_text,
        "typ_error": "",
        "syntax_error_count": 0,
    }


def typst_fixer_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.0)
    fixed_code = execute_fix_typst(state.typ_error, state.typ_content, llm)
    tokens = extract_token_usage(getattr(llm, "last_response", None))

    return {
        "typ_content": fixed_code,
        "token_usage": accumulate_tokens(state.token_usage, "typst_fixer", tokens),
        "last_step_tokens": tokens,
    }


def ats_validator_node(state: LangGraphState) -> dict:
    report, is_approved = execute_validate_ats(
        job_terms=state.job_terms,
        resume_text=state.txt_content,
        target_score=_POLICIES.target_ats_score,
        stuffing_threshold=_POLICIES.stuffing_density_threshold
    )

    return {
        "ats_report": report,
        "is_approved": is_approved,
    }


def cv_refiner_node(state: LangGraphState) -> dict:
    llm = get_dynamic_llm(temperature=0.1)
    refined_code = execute_refine_cv(state.typ_content, state.ats_report, llm)
    tokens = extract_token_usage(getattr(llm, "last_response", None))

    return {
        "typ_content": refined_code,
        "iteration": state.iteration + 1,
        "token_usage": accumulate_tokens(state.token_usage, "cv_refiner", tokens),
        "last_step_tokens": tokens,
    }


def committer_node(state: LangGraphState) -> dict:
    slug = state.job_slug or "cv-tailored"
    lang = state.job_lang or "en"

    execute_commit_artifacts(
        job_slug=slug,
        job_terms=state.job_terms,
        txt_content=state.txt_content
    )

    return {
        "job_title": state.job_title,
        "company_name": state.company_name,
        "job_slug": slug,
        "job_lang": lang,
        "pdf_path": state.pdf_path,
        "typ_error": state.typ_error,
        "syntax_error_count": state.syntax_error_count,
        "ats_report": state.ats_report,
        "is_approved": state.is_approved,
        "iteration": state.iteration,
        "detected_gaps": state.detected_gaps,
        "token_usage": state.token_usage,
    }