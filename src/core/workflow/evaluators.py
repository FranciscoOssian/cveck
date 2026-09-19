import re
import unicodedata
from src.core.models.state import DomainState
from src.core.workflow.schema import Policies


def _normalize_term(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def check_compilation_condition(state: DomainState, policies: Policies) -> str:
    """Returns: 'success', 'syntax_error', or 'max_step_error'."""
    if not state.typ_error:
        return "success"
    if state.syntax_error_count >= policies.max_syntax_retries:
        return "max_step_error"
    return "syntax_error"


def check_ats_condition(state: DomainState, policies: Policies) -> str:
    """Returns: 'approved', 'max_retries', 'unfixable_gaps', or 'needs_refinement'."""
    ats = state.ats_report
    if not ats:
        return "needs_refinement"

    # 1. Approved if score >= target and no mandatory requirements are missing
    if not ats.hard_fail and ats.score >= policies.target_ats_score:
        return "approved"

    # 2. Reached maximum retry limit
    if state.iteration >= policies.max_ats_retries:
        return "max_retries"

    # 3. Short-Circuit: if all missing mandatory skills are confirmed REAL GAPS
    if ats.missing_required:
        gaps_normalized = {
            _normalize_term(g.term) for g in state.detected_gaps
        }
        fixable_missing = []
        for missing_item in ats.missing_required:
            options = [_normalize_term(opt) for opt in re.split(r"\s+(?:OR|OU)\s+", missing_item, flags=re.IGNORECASE)]
            # Only unfixable if ALL options in the OR clause are real gaps
            if not all(opt in gaps_normalized for opt in options):
                fixable_missing.append(missing_item)

        if not fixable_missing:
            return "unfixable_gaps"

    return "needs_refinement"