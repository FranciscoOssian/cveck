from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.state import CVState, GapItem
from src.tools.file_manager import load_user_profile
from src.tools.json_parser import extract_and_parse_json, tool_call_args
from src.tools.token_tracker import extract_token_usage, accumulate_tokens
from src.config import get_llm


class RecordGaps(BaseModel):
    real_gaps: List[GapItem] = Field(
        default_factory=list,
        description="Lista de lacunas/gaps reais que não existem no perfil (lista vazia se não houver gaps)"
    )


def _parse_gap_response(response) -> RecordGaps:
    if response.tool_calls:
        return RecordGaps.model_validate(tool_call_args(response, "real_gaps"))
    content = response.content if isinstance(response.content, str) else str(response.content or "")
    return extract_and_parse_json(content, RecordGaps)


def gap_finder_node(state: CVState) -> dict:
    user_profile = load_user_profile()
    llm = get_llm(temperature=0)
    llm_with_tools = llm.bind_tools([RecordGaps])

    system_prompt = (
        "You are a technical fit evaluator between candidate profiles and job postings.\n"
        "Compare the terms extracted from the job posting with the candidate's master profile (`USER_PROFILE.md`).\n"
        "Identify only technologies or skills that are REQUIREMENTS or NICE-TO-HAVES in the job posting "
        "and that have NO mention or factual evidence in the profile.\n"
        "If the candidate already knows the technology or has equivalent experience in the profile, DO NOT mark it as a gap.\n"
        "IMPORTANT: You MUST call the `RecordGaps` tool with the list of gaps found. "
        "If there are no real gaps, send `real_gaps: []`."
    )

    terms = state.get("job_terms") or []
    terms_dump = "\n".join([
        f"- {(t.term if hasattr(t, 'term') else t.get('term', ''))} (Obrigatório: {(t.required if hasattr(t, 'required') else t.get('required', False))})"
        for t in terms
    ])
    
    user_content = (
        f"CANDIDATE PROFILE:\n{user_profile}\n\n"
        f"JOB TERMS ({state.get('job_title', 'Developer')} at {state.get('company_name', 'Company')}):\n{terms_dump}\n\n"
        f"Application date: {state.get('job_date', '')}"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content)
    ]

    response = llm_with_tools.invoke(messages)
    parsed = _parse_gap_response(response)
    
    real_gaps = parsed.real_gaps or []
    for g in real_gaps:
        g.vaga = state.get("job_title", "Developer")
        g.empresa = state.get("company_name", "Company")
        g.data = state.get("job_date", "")

    tokens = extract_token_usage(response)
    token_usage = accumulate_tokens(state.get("token_usage"), "gap_finder", tokens)

    return {
        "detected_gaps": real_gaps,
        "token_usage": token_usage,
        "last_step_tokens": tokens
    }