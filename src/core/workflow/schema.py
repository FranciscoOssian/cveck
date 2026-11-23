from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field


class BulletBudget(BaseModel):
    min_bullets: int = 8
    max_bullets: int = 13
    max_bullets_per_role: int = 4


class Policies(BaseModel):
    target_ats_score: float = 85.0
    max_ats_retries: int = 3
    max_syntax_retries: int = 3
    stuffing_density_threshold: float = 0.02
    bullet_budget: BulletBudget = Field(default_factory=BulletBudget)


class DirectTransition(BaseModel):
    type: Literal["direct"] = "direct"
    target: str


class ConditionalTransition(BaseModel):
    type: Literal["conditional"] = "conditional"
    condition: str
    target: Dict[str, str]


class EndTransition(BaseModel):
    type: Literal["end"] = "end"


TransitionRule = Union[DirectTransition, ConditionalTransition, EndTransition]


class StepDefinition(BaseModel):
    id: str
    name: str
    type: Literal["cognitive", "deterministic"]
    description: str
    prompt: Optional[str] = None
    schema_name: Optional[str] = Field(default=None, alias="schema")
    process: Optional[str] = None
    transitions: List[TransitionRule]


class WorkflowConfig(BaseModel):
    name: str
    description: str
    policies: Policies
    entrypoint: str
    steps: List[StepDefinition]

    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        return next((s for s in self.steps if s.id == step_id), None)