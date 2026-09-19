from typing import Dict, Any
from pydantic import Field
from src.core.models.state import DomainState


class LangGraphState(DomainState):
    """Extension of domain state with telemetry exclusive to the LangGraph adapter."""
    token_usage: Dict[str, Any] = Field(default_factory=lambda: {
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "by_node": {}
    })
    last_step_tokens: Dict[str, int] = Field(default_factory=dict)