import unicodedata
import re
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.state import CVState, JobTerm
from src.tools.file_manager import load_prompt
from src.tools.json_parser import extract_and_parse_json, tool_call_args
from src.tools.token_tracker import extract_token_usage, accumulate_tokens
from src.config import get_llm
from src.i18n import _

def sanitize_slug(text: str) -> str:
    """Convert any text to safe kebab-case for filenames."""
    if not text:
        return "cv-tailored"
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "cv-tailored"


class TermExtractorResponse(BaseModel):
    job_title: str = Field(
        default="Software Developer",
        description="Job title extracted from job description (e.g. Front-End Software Engineer)"
    )
    company_name: str = Field(
        default="Company",
        description="Hiring company name (or 'Confidential' if none)"
    )
    job_slug: str = Field(
        default="job-company",
        description="Short kebab-case slug for files (e.g. digisystem-frontend-senior)"
    )
    job_lang: str = Field(
        default="en",
        description="Lowercase ISO language code of the job (e.g. 'en', 'pt', 'es')"
    )
    terms: List[JobTerm] = Field(
        default_factory=list,
        description="List of hard skills, tools, libraries, and technical practices from the job"
    )


def _parse_term_response(response) -> TermExtractorResponse:
    if response.tool_calls:
        return TermExtractorResponse.model_validate(tool_call_args(response, "terms"))
    content = response.content if isinstance(response.content, str) else str(response.content or "")
    if not content.strip():
        raise ValueError(
            _("The model returned an empty response. Verify that the selected model in providers.json supports Tool Calling or text generation.")
        )
    return extract_and_parse_json(content, TermExtractorResponse)


def term_extractor_node(state: CVState) -> dict:
    system_instruction = load_prompt("extract_terms.md")
    llm = get_llm(temperature=0.1)
    
    llm_with_tools = llm.bind_tools([TermExtractorResponse])

    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=f"Descrição da vaga:\n\n{state['job_description']}")
    ]

    response = llm_with_tools.invoke(messages)
    parsed = _parse_term_response(response)

    title = state.get("job_title") or parsed.job_title
    company = state.get("company_name") or parsed.company_name
    slug = state.get("job_slug") or parsed.job_slug
    raw_lang = state.get("job_lang") or parsed.job_lang or "pt"
    safe_lang = raw_lang.strip().lower()
    
    raw_slug = state.get("job_slug") or slug
    safe_slug = sanitize_slug(raw_slug)

    tokens = extract_token_usage(response)
    token_usage = accumulate_tokens(state.get("token_usage"), "term_extractor", tokens)

    return {
        "job_terms": parsed.terms,
        "job_title": title,
        "company_name": company,
        "job_slug": safe_slug,
        "job_lang": safe_lang,
        "token_usage": token_usage,
        "last_step_tokens": tokens
    }