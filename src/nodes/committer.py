import json
from src.state import CVState
from src.tools.file_manager import write_file
from src.config import OUTPUT_DIR
from src.i18n import _

SEPARATOR = "=" * 50


def _build_failure_summary(state: CVState, syntax_errors: int, typ_error: str) -> str:
    job_title = state.get("job_title", "Software Developer")
    company_name = state.get("company_name", "Company")
    attempts = state.get("iteration", 1)

    return "\n".join([
        SEPARATOR,
        f" ⚠ {_('PROCESS HALTED: TYPST SYNTAX FAILURE')}",
        SEPARATOR,
        f"{_('Job:')} {job_title} ({company_name})",
        f"{_('Compilation attempts:')} {attempts} ({syntax_errors} {_('syntax errors')})",
        "",
        f"{_('REASON:')}",
        _("The current model repeatedly failed to produce valid Typst code."),
        _("This indicates that this specific model may not have strong mastery of Typst syntax."),
        "",
        f"{_('LAST COMPILER ERROR:')}",
        f"{typ_error[:400]}...",
        "",
        f"{_('SUGGESTION:')}",
        _("Switch to a more robust coding model in the /provider menu"),
        _("(e.g., meta/llama-3.3-70b-instruct, claude-3-5-sonnet, or deepseek-chat).")
    ])


def _build_success_summary(state: CVState, ats, slug: str) -> str:
    lang = state.get("job_lang") or "pt"
    job_title = state.get("job_title", "Software Developer")
    company_name = state.get("company_name", "Company")
    status_label = _("Approved") if state.get("is_approved") else _("Rejected")

    missing_req = (
        ", ".join(ats.missing_required)
        if ats and ats.missing_required
        else _("None")
    )
    missing_opt = (
        ", ".join(ats.missing_optional)
        if ats and ats.missing_optional
        else _("None")
    )

    summary_lines = [
        SEPARATOR,
        f" {_('ATS TECHNICAL REPORT:')} {job_title} ({company_name})",
        SEPARATOR,
        f"{_('Status:')} {status_label}",
        f"{_('Overall Score:')} {ats.score if ats else 0}/100",
        f"{_('Attempts Made:')} {state.get('iteration', 1)}",
        f"{_('Mandatory Requirements Coverage:')} {ats.coverage_required_pct if ats else 0}%",
        f"{_('Overall Keywords Coverage:')} {ats.coverage_pct if ats else 0}%",
        "",
        f"{_('Missing Mandatory:')} {missing_req}",
        f"{_('Missing Differentiators:')} {missing_opt}",
    ]

    if ats and ats.stuffing_flags:
        summary_lines.append(f"{_('Keyword Stuffing Alert:')} {ats.stuffing_flags}")

    detected_gaps = state.get("detected_gaps", [])
    if detected_gaps:
        gap_names = [g.term if hasattr(g, "term") else g.get("term", "") for g in detected_gaps]
        summary_lines.append(f"{_('Gaps Added to Backlog (doc/GAPS.md):')} {gap_names}")

    summary_lines.append(f"{_('PDF generated at:')} {OUTPUT_DIR}/cv-{slug}-{lang}.pdf")

    tokens_info = state.get("token_usage") or {}
    total_tok = tokens_info.get("total_tokens", 0)
    in_tok = tokens_info.get("input_tokens", 0)
    out_tok = tokens_info.get("output_tokens", 0)

    summary_lines.append("")
    summary_lines.append(
        f"{_('Total Token Consumption:')} {total_tok:,} ({_('Prompt:')} {in_tok:,} | {_('Completion:')} {out_tok:,})"
    )

    return "\n".join(summary_lines)


def committer_node(state: CVState) -> dict:
    slug = state.get("job_slug") or "cv-tailored"
    ats = state.get("ats_report")
    syntax_errors = state.get("syntax_error_count", 0)
    typ_error = state.get("typ_error", "")

    if syntax_errors >= 3 or (typ_error and not state.get("pdf_path")):
        return {"final_summary": _build_failure_summary(state, syntax_errors, typ_error)}

    terms_file = OUTPUT_DIR / f"job_terms-{slug}.json"
    raw_terms = state.get("job_terms", [])
    terms_data = [
        t.model_dump() if hasattr(t, "model_dump") else t
        for t in raw_terms
    ]
    write_file(terms_file, json.dumps(terms_data, ensure_ascii=False, indent=2))

    txt_file = OUTPUT_DIR / f"resume-{slug}.txt"
    write_file(txt_file, state.get("txt_content", ""))

    return {"final_summary": _build_success_summary(state, ats, slug)}