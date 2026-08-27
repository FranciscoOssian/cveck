from langchain_core.messages import SystemMessage, HumanMessage
from src.state import CVState
from src.tools.file_manager import load_prompt, load_user_profile
from src.tools.token_tracker import extract_token_usage, accumulate_tokens
from src.config import get_llm
from src.nodes.cv_generator import SubmitTypstCV, normalize_typst_code


def cv_refiner_node(state: CVState) -> dict:
    refine_prompt = load_prompt("refine_cv.md")
    style_guide = load_prompt("CV_STYLE_GUIDE.md")
    user_profile = load_user_profile()

    llm = get_llm(temperature=0.1)
    llm_with_tools = llm.bind_tools([SubmitTypstCV])

    ats = state.get("ats_report")

    # Build the formatted ATS report for the model
    feedback_parts = []
    if ats:
        if ats.missing_required:
            feedback_parts.append(f"• Mandatory Requirements Missing in ATS: {', '.join(ats.missing_required)}")
        if ats.missing_optional:
            feedback_parts.append(f"• Missing Differentiators: {', '.join(ats.missing_optional)}")
        if ats.stuffing_flags:
            feedback_parts.append(f"• Excessive Repetition Alert (Stuffing): {ats.stuffing_flags}")
        feedback_parts.append(f"• Current Score: {ats.score}/100 (Mandatory Coverage: {ats.coverage_required_pct}%)")

    feedback_text = "\n".join(feedback_parts) if feedback_parts else "Maximize a cobertura de termos com respaldo factual no perfil."

    user_content = (
        f"STYLE GUIDE:\n{style_guide}\n\n"
        f"FACTUAL CANDIDATE PROFILE:\n{user_profile}\n\n"
        f"ATS ANALYZER REPORT:\n{feedback_text}\n\n"
        f"PREVIOUS TYPST CODE:\n{state['typ_content']}\n\n"
        f"Adjust the Typst code to cover the missing terms (provided they exist in the profile) and submit it via SubmitTypstCV."
    )

    # Correctly inject the refine_prompt into the SystemMessage
    messages = [
        SystemMessage(content=refine_prompt),
        HumanMessage(content=user_content)
    ]
    
    response = llm_with_tools.invoke(messages)

    if response.tool_calls:
        raw_code = response.tool_calls[0]["args"].get("typst_code", "")
    else:
        raw_code = response.content if isinstance(response.content, str) else str(response.content)

    clean_code = normalize_typst_code(raw_code)

    tokens = extract_token_usage(response)
    token_usage = accumulate_tokens(state.get("token_usage"), "cv_refiner", tokens)

    return {
        "typ_content": clean_code,
        "iteration": state.get("iteration", 1) + 1,
        "token_usage": token_usage,
        "last_step_tokens": tokens
    }