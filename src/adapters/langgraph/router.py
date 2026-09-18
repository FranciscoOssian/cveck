from src.core.models.state import DomainState
from src.core.workflow.schema import Policies
from src.core.workflow.evaluators import check_compilation_condition, check_ats_condition


def route_after_typst_compiler(state: DomainState, policies: Policies) -> str:
    """Decide se vai para typst_fixer, ats_validator ou aborta em committer."""
    return check_compilation_condition(state, policies)


def route_after_ats(state: DomainState, policies: Policies) -> str:
    """Decide se aprova (committer), faz curto-circuito de gaps ou refina."""
    return check_ats_condition(state, policies)