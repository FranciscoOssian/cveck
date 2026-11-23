from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.models.job import JobTerm
from src.core.models.gap import GapItem
from src.core.models.typst import SubmitTypstCV
from src.core.context import load_user_profile, resolve_template_skeleton
from src.core.paths import DOC_DIR, PROMPTS_DIR, TEMPLATES_DIR


def execute_generate_cv(
    job_terms: List[JobTerm],
    detected_gaps: List[GapItem],
    job_title: str,
    company_name: str,
    job_lang: str,
    llm,
    pruned_profile: str = ""
) -> str:
    profile = pruned_profile.strip() if pruned_profile else load_user_profile(DOC_DIR)
    style_guide = (PROMPTS_DIR / "CV_STYLE_GUIDE.md").read_text(encoding="utf-8")
    prompt = (PROMPTS_DIR / "generate_cv.md").read_text(encoding="utf-8")
    base_template, resolved_lang = resolve_template_skeleton(TEMPLATES_DIR, job_lang)

    terms_str = ", ".join([f"{t.term} ({'mandatory' if t.required else 'optional'})" for t in job_terms])
    gaps_str = ", ".join([g.term for g in detected_gaps]) or "None"

    user_content = (
        f"STYLE GUIDE:\n{style_guide}\n\n"
        f"BASE TEMPLATE (Language: {resolved_lang}):\n{base_template}\n\n"
        f"FACTUAL PROFILE (PRUNED EVIDENCE ONLY):\n{profile}\n\n"
        f"TARGET JOB: {job_title} @ {company_name} ({resolved_lang})\n"
        f"JOB KEYWORDS: {terms_str}\n"
        f"PROHIBITED GAPS (DO NOT HALLUCINATE OR MENTION): {gaps_str}\n\n"
        "Generate the complete Typst code adhering strictly to the pruned profile above and submit it via SubmitTypstCV."
    )

    llm_with_tools = llm.bind_tools([SubmitTypstCV])
    response = llm_with_tools.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=user_content)
    ])

    if response.tool_calls:
        return response.tool_calls[0]["args"].get("typst_code", "")
    return str(response.content)