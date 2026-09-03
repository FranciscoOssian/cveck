# Pipeline Node Specifications

The CVECK pipeline executes 9 specialized nodes compiled into a LangGraph `StateGraph`.

| Node | Input State | Primary Function | Output Artifact / State Mutation |
| :--- | :--- | :--- | :--- |
| `term_extractor` | `job_description` | Extracts canonical hard skills, tools, required vs. optional criteria, job slug, and language. | `job_terms`, `job_title`, `company_name`, `job_slug`, `job_lang` |
| `gap_finder` | `job_terms`, `USER_PROFILE.md` | Compares required terms against candidate profile to detect real market gaps. | `detected_gaps` |
| `gaps_updater` | `detected_gaps` | Persists detected gaps to markdown and json databases. | Updates `doc/GAPS.md` and `doc/gaps.json` |
| `cv_generator` | `job_terms`, `detected_gaps`, `USER_PROFILE.md` | Generates full Typst source code applying STAR narrative and front-loaded bold formatting. | `typ_content`, `iteration=1` |
| `typst_compiler` | `typ_content`, `job_lang` | Sanitizes syntax locally and compiles `.typ` into vector `.pdf`. Extracts raw text using `pymupdf`. | `pdf_path`, `txt_content`, `typ_error`, `syntax_error_count` |
| `typst_fixer` | `typ_error`, `typ_content` | Repares Typst compilation errors based on compiler traceback. | `typ_content` |
| `ats_validator` | `job_terms`, `txt_content` | Runs deterministic ATS scoring algorithm and validates keyword density. | `ats_report`, `is_approved` |
| `cv_refiner` | `ats_report`, `typ_content`, `USER_PROFILE.md` | Iteratively refines Typst code to increase keyword alignment without hallucinating. | `typ_content`, `iteration += 1` |
| `committer` | `ats_report`, `token_usage`, `pdf_path` | Saves terms JSON, plaintext dump, and renders final technical performance report. | `final_summary`, writes output files |