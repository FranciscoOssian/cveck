from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.models.ats import ATSReport
from src.core.models.typst import SubmitTypstCV
from src.core.context import load_user_profile
from src.core.paths import DOC_DIR, PROMPTS_DIR


def execute_refine_cv(
    typ_content: str,
    ats_report: Optional[ATSReport],
    llm,
    pruned_profile: str = ""
) -> str:
    profile = pruned_profile.strip() if pruned_profile else load_user_profile(DOC_DIR)
    style_guide = (PROMPTS_DIR / "CV_STYLE_GUIDE.md").read_text(encoding="utf-8")
    prompt = (PROMPTS_DIR / "refine_cv.md").read_text(encoding="utf-8")

    feedback = []
    if ats_report:
        if ats_report.missing_required:
            feedback.append(f"• Missing Mandatory: {', '.join(ats_report.missing_required)}")
        if ats_report.missing_optional:
            feedback.append(f"• Missing Optional: {', '.join(ats_report.missing_optional)}")
        if ats_report.stuffing_flags:
            feedback.append(f"• Excessive Repetition Alert (Stuffing): {ats_report.stuffing_flags}")
        feedback.append(f"• Current Score: {ats_report.score}/100")

    user_content = (
        f"STYLE GUIDE:\n{style_guide}\n\n"
        f"FACTUAL PROFILE (PRUNED EVIDENCE ONLY):\n{profile}\n\n"
        f"ATS REPORT:\n{chr(10).join(feedback)}\n\n"
        f"PREVIOUS CODE:\n{typ_content}\n\n"
        "Refine the bullets to cover missing terms backed strictly by the pruned profile and submit via SubmitTypstCV."
    )

    llm_with_tools = llm.bind_tools([SubmitTypstCV])
    response = llm_with_tools.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=user_content)
    ])

    if response.tool_calls:
        return response.tool_calls[0]["args"].get("typst_code", "")
    return str(response.content)