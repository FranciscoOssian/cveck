# src/core/use_cases/find_gaps.py
from typing import List, Tuple, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.models.job import JobTerm
from src.core.models.gap import RecordGaps, GapItem
from src.core.services.parser import extract_and_parse_json
from src.core.services.telemetry import extract_token_usage
from src.core.context import load_user_profile
from src.core.paths import DOC_DIR, PROMPTS_DIR


def execute_find_gaps(
    job_terms: List[JobTerm],
    job_title: str,
    company_name: str,
    job_date: str,
    llm
) -> Tuple[List[GapItem], Dict[str, int]]:
    profile = load_user_profile(DOC_DIR)
    prompt = (PROMPTS_DIR / "find_gaps.md").read_text(encoding="utf-8")
    llm_with_tools = llm.bind_tools([RecordGaps])

    # Resgate da v1: explicitamos as alternativas no dump para o modelo
    lines = []
    for t in job_terms:
        alts = t.alternatives or []
        alt_str = f" [OR: {', '.join(alts)} - satisfying ANY option is sufficient]" if alts else ""
        lines.append(f"- {t.term}{alt_str} (Mandatory: {t.required})")
    terms_dump = "\n".join(lines)

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"CANDIDATE PROFILE:\n{profile}\n\nJOB TERMS:\n{terms_dump}\n\nApplication Date: {job_date}")
    ]
    response = llm_with_tools.invoke(messages)
    tokens = extract_token_usage(response)

    if response.tool_calls:
        parsed = RecordGaps.model_validate(response.tool_calls[0]["args"])
    else:
        parsed = extract_and_parse_json(str(response.content), RecordGaps)

    real_gaps = parsed.real_gaps or []
    for gap in real_gaps:
        gap.job_title = job_title
        gap.company_name = company_name
        gap.date = job_date

    return real_gaps, tokens