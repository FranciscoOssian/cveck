from langchain_core.messages import SystemMessage, HumanMessage
from src.state import CVState
from src.config import get_llm
from src.nodes.cv_generator import SubmitTypstCV, normalize_typst_code
from src.tools.token_tracker import extract_token_usage, accumulate_tokens


def typst_fixer_node(state: CVState) -> dict:
    """Node dedicated EXCLUSIVELY to fixing Typst compilation errors."""
    llm = get_llm(temperature=0.0)
    llm_with_tools = llm.bind_tools([SubmitTypstCV])

    typ_error = state.get("typ_error", "")
    current_code = state.get("typ_content", "")

    system_prompt = (
        "You are a Typst compiler and syntax expert.\n"
        "The provided Typst code generated a compilation error.\n"
        "Your mission is to ESTRITAMENTE fix the syntax error pointed by the compiler.\n"
        "STRICT RULES:\n"
        "1. DO NOT change the text content or add new information or technologies.\n"
        "2. Ensure all braces, brackets, parentheses and strings are properly closed.\n"
        "3. Keep `#import '../templates/template.typ': columns-2, CV` at the top.\n"
        "4. Submit the fixed code by calling the SubmitTypstCV tool."
    )

    user_content = (
        f"TYPST COMPILER ERROR:\n{typ_error}\n\n"
        f"TYPST CODE WITH ERROR:\n{current_code}\n\n"
        "Fix the syntax error and submit the corrected code."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content)
    ]
    response = llm_with_tools.invoke(messages)

    if response.tool_calls:
        raw_code = response.tool_calls[0]["args"].get("typst_code", "")
    else:
        raw_code = response.content if isinstance(response.content, str) else str(response.content)

    clean_code = normalize_typst_code(raw_code)
    tokens = extract_token_usage(response)
    token_usage = accumulate_tokens(state.get("token_usage"), "typst_fixer", tokens)

    return {
        "typ_content": clean_code,
        "token_usage": token_usage,
        "last_step_tokens": tokens
    }