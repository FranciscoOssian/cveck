# LangGraph Workflow & State Model

The LangGraph adapter (`src/adapters/langgraph/`) dynamically maps the declarative `src/core/workflow.yaml` into a cyclic `StateGraph`.

## State Architecture

The adapter builds on top of the pure Core `DomainState` by adding telemetry tracking:

```python
# src/core/models/state.py
class DomainState(BaseModel):
    job_description: str = ""
    job_slug: str = ""
    job_title: str = ""
    company_name: str = ""
    job_lang: str = "en"
    job_date: str = ""
    job_terms: List[JobTerm] = Field(default_factory=list)
    detected_gaps: List[GapItem] = Field(default_factory=list)
    pruned_profile: str = ""
    typ_content: str = ""
    pdf_path: str = ""
    txt_content: str = ""
    typ_error: str = ""
    syntax_error_count: int = 0
    ats_report: Optional[ATSReport] = None
    iteration: int = 0
    is_approved: bool = False
    final_summary: str = ""

# src/adapters/langgraph/state.py
class LangGraphState(DomainState):
    token_usage: Dict[str, Any] = Field(default_factory=lambda: {
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "by_node": {}
    })
    last_step_tokens: Dict[str, int] = Field(default_factory=dict)
```

---

## Dynamic Graph Builder (`builder.py`)

Rather than hardcoding edges, `src/adapters/langgraph/builder.py` parses `workflow.yaml` transitions and binds them dynamically:

- **Direct transitions:** `workflow.add_edge(step.id, trans.target)`
- **Conditional transitions:** Mapped to Core evaluation predicates in `src/core/workflow/evaluators.py`.
- **End transitions:** `workflow.add_edge(step.id, END)`

---

## Routing & Evaluator Predicates

Core transition logic lives in `src/core/workflow/evaluators.py`:

### 1. Compiler Condition (`check_compilation_condition`)
```python
def check_compilation_condition(state: DomainState, policies: Policies) -> str:
    if not state.typ_error:
        return "success"
    if state.syntax_error_count >= policies.max_syntax_retries:
        return "max_step_error"
    return "syntax_error"
```

### 2. ATS Reflection Condition (`check_ats_condition`)
```python
def check_ats_condition(state: DomainState, policies: Policies) -> str:
    ats = state.ats_report
    if not ats:
        return "needs_refinement"

    if not ats.hard_fail and ats.score >= policies.target_ats_score:
        return "approved"

    if state.iteration >= policies.max_ats_retries:
        return "max_retries"

    # Short-Circuit: If all missing mandatory terms are known gaps in USER_PROFILE.md
    if ats.missing_required:
        gaps_normalized = {_normalize_term(g.term) for g in state.detected_gaps}
        fixable_missing = []
        for missing_item in ats.missing_required:
            options = [_normalize_term(opt) for opt in re.split(r"\s+(?:OR|OU)\s+", missing_item, flags=re.IGNORECASE)]
            if not all(opt in gaps_normalized for opt in options):
                fixable_missing.append(missing_item)

        if not fixable_missing:
            return "unfixable_gaps"

    return "needs_refinement"
```