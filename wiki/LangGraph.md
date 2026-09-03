# LangGraph Workflow & State Model

CVECK utilizes **LangGraph** to model resume generation as a deterministic cyclic graph with state validation and conditional edge routing.

## State Schema (`CVState`)

```python
class CVState(TypedDict, total=False):
    job_description: str
    job_slug: str
    job_title: str
    company_name: str
    job_lang: str
    job_date: str
    
    # Extraction & Gaps
    job_terms: List[JobTerm]
    detected_gaps: List[GapItem]
    
    # Content & Compilation
    typ_content: str
    pdf_path: str
    txt_content: str
    typ_error: str
    syntax_error_count: int
    
    # Validation & Retry
    ats_report: ATSReport
    iteration: int
    is_approved: bool
    final_summary: str
    
    # Token Metrics
    token_usage: Dict[str, Any]
    last_step_tokens: Dict[str, int]
```

---

## Routing & Conditional Edges

CVECK defines two core conditional routers in `src/graph.py`:

### 1. Compiler Router (`route_after_typst_compiler`)
```python
def route_after_typst_compiler(state: CVState) -> str:
    typ_error = state.get("typ_error")
    syntax_errors = state.get("syntax_error_count", 0)

    if typ_error:
        if syntax_errors >= 3:
            return "committer"  # Abort on persistent compilation failure
        return "typst_fixer"     # Attempt automatic repair

    return "ats_validator"      # Proceed to ATS scoring
```

### 2. ATS Reflection Router (`route_after_ats`)
```python
def route_after_ats(state: CVState) -> str:
    if state.get("is_approved"):
        return "committer"

    if state.get("iteration", 0) >= MAX_ATS_RETRIES:
        return "committer"

    # Short-Circuit: If all missing required keywords are known Gaps, do not loop
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
```