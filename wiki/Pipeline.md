# Pipeline Node & Step Specifications

The CVECK pipeline is declared in `src/core/workflow.yaml` and executed via dedicated Core use cases. In the LangGraph adapter, these steps form a cyclic `StateGraph`.

| Step / Node | Type | Core Use Case | Primary Function | Output Mutation |
| :--- | :--- | :--- | :--- | :--- |
| `term_extractor` | Cognitive | `execute_extract_terms` | Extracts canonical hard skills, tools, required vs. optional criteria, job slug, and language. | `job_terms`, `job_title`, `company_name`, `job_slug`, `job_lang` |
| `gap_finder` | Cognitive | `execute_find_gaps` | Compares required terms against `USER_PROFILE.md` to identify real market gaps. | `detected_gaps` |
| `gaps_updater` | Deterministic | `execute_update_gaps` | Atomically persists detected gaps to `doc/GAPS.md` and `doc/gaps.json`. | Updates backlog files |
| `profile_pruner` | Cognitive | `execute_prune_profile` | Filters irrelevant technologies at sentence level, omits redundant projects, and preserves employment continuity. | `pruned_profile` |
| `cv_generator` | Cognitive | `execute_generate_cv` | Generates full Typst source code from `pruned_profile`, applying STAR narrative and Checklist Anchors. | `typ_content`, `iteration=1` |
| `typst_compiler` | Deterministic | `execute_compile_cv` | Sanitizes syntax locally via regex, compiles `.typ` into vector `.pdf`, and extracts raw text via `pymupdf`. | `pdf_path`, `txt_content`, `typ_error`, `syntax_error_count` |
| `typst_fixer` | Cognitive | `execute_fix_typst` | Analyzes compiler stderr traceback and auto-repairs syntax without modifying content. | `typ_content` |
| `ats_validator` | Deterministic | `execute_validate_ats` | Runs mathematical ATS scoring, evaluates keyword density, and checks approval criteria. | `ats_report`, `is_approved` |
| `cv_refiner` | Cognitive | `execute_refine_cv` | Iteratively rewrites existing bullets using `pruned_profile` to cover missing terms backed by candidate profile. | `typ_content`, `iteration += 1` |
| `committer` | Deterministic | `execute_commit_artifacts` | Commits `job_terms-{slug}.json`, `resume-{slug}.txt`, `profile_pruned-{slug}.md`, and outputs execution telemetry. | Final artifacts saved |

---

## Workflow Policies (`workflow.yaml`)

The pipeline execution is governed by declarative policies defined in `src/core/workflow.yaml`:

```yaml
policies:
  target_ats_score: 85.0
  max_ats_retries: 3
  max_syntax_retries: 3
  stuffing_density_threshold: 0.02
  bullet_budget:
    min_bullets: 8
    max_bullets: 13
    max_bullets_per_role: 4
```
