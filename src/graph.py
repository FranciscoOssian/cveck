import unicodedata
from langgraph.graph import StateGraph, START, END
from src.state import CVState
from src.config import MAX_ATS_RETRIES
from src.nodes.term_extractor import term_extractor_node
from src.nodes.gap_finder import gap_finder_node
from src.nodes.gaps_updater import gaps_updater_node
from src.nodes.cv_generator import cv_generator_node
from src.nodes.typst_compiler import typst_compiler_node
from src.nodes.typst_fixer import typst_fixer_node
from src.nodes.ats_validator import ats_validator_node
from src.nodes.cv_refiner import cv_refiner_node
from src.nodes.committer import committer_node


def normalize_term(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def route_after_typst_compiler(state: CVState) -> str:
    """Route after Typst compilation attempt."""
    typ_error = state.get("typ_error")
    syntax_errors = state.get("syntax_error_count", 0)

    if typ_error:
        if syntax_errors >= 3:
            return "committer"
        return "typst_fixer"

    return "ats_validator"


def route_after_ats(state: CVState) -> str:
    """Route after ATS validator."""
    if state.get("is_approved"):
        return "committer"

    if state.get("iteration", 0) >= MAX_ATS_RETRIES:
        return "committer"

    # Short-Circuit: if all missing required are Real Gaps, exit!
    ats = state.get("ats_report")
    if ats and getattr(ats, "missing_required", None):
        raw_gaps = state.get("detected_gaps", [])
        gaps_normalized = {
            normalize_term(g.term if hasattr(g, "term") else g.get("term", ""))
            for g in raw_gaps
        }
        fixable_missing = [
            term for term in ats.missing_required
            if normalize_term(term) not in gaps_normalized
        ]
        if not fixable_missing:
            return "committer"

    return "cv_refiner"


workflow = StateGraph(CVState)

workflow.add_node("term_extractor", term_extractor_node)
workflow.add_node("gap_finder", gap_finder_node)
workflow.add_node("gaps_updater", gaps_updater_node)
workflow.add_node("cv_generator", cv_generator_node)
workflow.add_node("typst_compiler", typst_compiler_node)
workflow.add_node("typst_fixer", typst_fixer_node)
workflow.add_node("ats_validator", ats_validator_node)
workflow.add_node("cv_refiner", cv_refiner_node)
workflow.add_node("committer", committer_node)

workflow.add_edge(START, "term_extractor")
workflow.add_edge("term_extractor", "gap_finder")
workflow.add_edge("gap_finder", "gaps_updater")
workflow.add_edge("gaps_updater", "cv_generator")
workflow.add_edge("cv_generator", "typst_compiler")

workflow.add_conditional_edges(
    "typst_compiler",
    route_after_typst_compiler,
    {
        "typst_fixer": "typst_fixer",
        "ats_validator": "ats_validator",
        "committer": "committer"
    }
)
workflow.add_edge("typst_fixer", "typst_compiler")

workflow.add_conditional_edges(
    "ats_validator",
    route_after_ats,
    {
        "committer": "committer",
        "cv_refiner": "cv_refiner"
    }
)
workflow.add_edge("cv_refiner", "typst_compiler")
workflow.add_edge("committer", END)

app = workflow.compile()