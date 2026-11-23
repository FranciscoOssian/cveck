from src.core.models.state import DomainState
from src.core.workflow.schema import Policies
from src.core.workflow.evaluators import check_compilation_condition, check_ats_condition


def route_after_typst_compiler(state: DomainState, policies: Policies) -> str:
    """Routes to typst_fixer, ats_validator, or aborts at committer."""
    return check_compilation_condition(state, policies)


def route_after_ats(state: DomainState, policies: Policies) -> str:
    """Routes to committer (approval), unfixable gaps short-circuit, or cv_refiner."""
    return check_ats_condition(state, policies)