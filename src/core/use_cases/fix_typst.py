from langchain_core.messages import SystemMessage, HumanMessage
from src.core.models.typst import SubmitTypstCV
from src.core.paths import PROMPTS_DIR


def execute_fix_typst(typ_error: str, typ_content: str, llm) -> str:
    prompt = (PROMPTS_DIR / "fix_typst.md").read_text(encoding="utf-8")
    llm_with_tools = llm.bind_tools([SubmitTypstCV])

    user_content = (
        f"TYPST COMPILER ERROR:\n{typ_error}\n\n"
        f"CODE WITH ERROR:\n{typ_content}\n\n"
        "Fix the syntax error ensuring all delimiters and imports are closed, and resubmit via SubmitTypstCV."
    )
    response = llm_with_tools.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=user_content)
    ])

    if response.tool_calls:
        return response.tool_calls[0]["args"].get("typst_code", "")
    return str(response.content)