from typing import Tuple, Dict
from langchain_core.messages import SystemMessage, HumanMessage

from src.core.models.job import TermExtractorResponse
from src.core.services.parser import extract_and_parse_json
from src.core.services.telemetry import extract_token_usage
from src.core.paths import PROMPTS_DIR


def execute_extract_terms(job_description: str, llm) -> Tuple[TermExtractorResponse, Dict[str, int]]:
    prompt = (PROMPTS_DIR / "extract_terms.md").read_text(encoding="utf-8")
    llm_with_tools = llm.bind_tools([TermExtractorResponse])

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Job description:\n\n{job_description}")
    ]
    response = llm_with_tools.invoke(messages)
    tokens = extract_token_usage(response)

    if response.tool_calls:
        parsed = TermExtractorResponse.model_validate(response.tool_calls[0]["args"])
    else:
        parsed = extract_and_parse_json(str(response.content), TermExtractorResponse)

    return parsed, tokens