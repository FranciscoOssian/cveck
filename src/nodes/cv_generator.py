import re
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.state import CVState
from src.tools.file_manager import load_prompt, load_user_profile, resolve_template_skeleton
from src.tools.token_tracker import extract_token_usage, accumulate_tokens
from src.config import get_llm


class SubmitTypstCV(BaseModel):
    typst_code: str = Field(
        description="Pure Typst source code, starting with #import '../templates/template.typ': columns-2, CV, and containing all completed sections."
    )


def normalize_typst_code(code: str) -> str:
    if not code:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", code, flags=re.DOTALL).strip()
    cleaned = re.sub(r"```(?:typst)?", "", cleaned).replace("```", "").strip()

    # Normalize any import variation to the templates/ folder
    cleaned = re.sub(
        r'#import\s+[\'"].*?template\.typ[\'"](?:\s*:\s*([^;\n]+))?',
        r'#import "../templates/template.typ": columns-2, CV',
        cleaned
    )

    return cleaned.strip()


def cv_generator_node(state: CVState) -> dict:
    system_prompt = load_prompt("generate_cv.md")
    style_guide = load_prompt("CV_STYLE_GUIDE.md")
    user_profile = load_user_profile()
    
    target_lang = state.get("job_lang", "pt")
    base_template, resolved_lang = resolve_template_skeleton(target_lang)

    llm = get_llm(temperature=0.1)
    llm_with_tools = llm.bind_tools([SubmitTypstCV])

    job_terms = state.get("job_terms") or []
    detected_gaps = state.get("detected_gaps") or []

    terms_summary = ", ".join([
        f"{(t.term if hasattr(t, 'term') else t.get('term', ''))} ({'obrigatório' if (t.required if hasattr(t, 'required') else t.get('required', False)) else 'diferencial'})"
        for t in job_terms
    ])
    
    gaps_summary = ", ".join([
        (g.term if hasattr(g, 'term') else g.get('term', ''))
        for g in detected_gaps
    ]) or "Nenhum"

    user_content = (
        f"STYLE AND WRITING GUIDE:\n{style_guide}\n\n"
        f"BASE TYPST SKELETON (Language: {resolved_lang}):\n{base_template}\n\n"
        f"FACTUAL CANDIDATE PROFILE:\n{user_profile}\n\n"
        f"TARGET JOB: {state.get('job_title', 'Developer')} at {state.get('company_name', 'Company')}\n"
        f"TARGET LANGUAGE: {resolved_lang}\n"
        f"JOB KEYWORDS: {terms_summary}\n"
        f"GAPS THAT DO NOT EXIST IN THE PROFILE (DO NOT MENTION): {gaps_summary}\n\n"
        f"Generate the complete Typst code following the style guide, filling the #show: CV.with(...) header with the candidate's contact information, and submit it via SubmitTypstCV."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content)
    ]
    response = llm_with_tools.invoke(messages)

    if response.tool_calls:
        raw_code = response.tool_calls[0]["args"].get("typst_code", "")
    else:
        raw_code = response.content if isinstance(response.content, str) else str(response.content or "")

    clean_code = normalize_typst_code(raw_code)

    tokens = extract_token_usage(response)
    token_usage = accumulate_tokens(state.get("token_usage"), "cv_generator", tokens)

    return {
        "typ_content": clean_code,
        "iteration": 1,
        "token_usage": token_usage,
        "last_step_tokens": tokens
    }