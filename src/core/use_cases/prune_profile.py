from typing import List, Tuple, Dict
from langchain_core.messages import SystemMessage, HumanMessage

from src.core.models.job import JobTerm
from src.core.models.gap import GapItem
from src.core.models.profile import SubmitPrunedProfile
from src.core.services.parser import extract_and_parse_json
from src.core.services.telemetry import extract_token_usage
from src.core.paths import PROMPTS_DIR


def execute_prune_profile(
    job_terms: List[JobTerm],
    detected_gaps: List[GapItem],
    job_title: str,
    company_name: str,
    raw_profile: str,
    llm
) -> Tuple[str, Dict[str, int]]:
    prompt = (PROMPTS_DIR / "prune_profile.md").read_text(encoding="utf-8")
    llm_with_tools = llm.bind_tools([SubmitPrunedProfile])

    terms_str = ", ".join([f"{t.term} ({'mandatory' if t.required else 'optional'})" for t in job_terms])
    gaps_str = ", ".join([g.term for g in detected_gaps]) or "None"

    user_content = (
        f"TARGET JOB: {job_title} @ {company_name}\n"
        f"JOB KEYWORDS: {terms_str}\n"
        f"CONFIRMED GAPS (DO NOT INCLUDE): {gaps_str}\n\n"
        f"CANDIDATE MASTER PROFILE (RAW):\n{raw_profile}\n\n"
        "Apply the Relevance Razor. Prune all irrelevant complexities and drop redundant personal projects. "
        "Submit the clean pruned Markdown using SubmitPrunedProfile."
    )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=user_content)
    ]
    response = llm_with_tools.invoke(messages)
    tokens = extract_token_usage(response)

    if response.tool_calls:
        pruned_code = response.tool_calls[0]["args"].get("pruned_profile", "")
    else:
        parsed = extract_and_parse_json(str(response.content), SubmitPrunedProfile)
        pruned_code = parsed.pruned_profile or str(response.content)

    return pruned_code.strip(), tokens