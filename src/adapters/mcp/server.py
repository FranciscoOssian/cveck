import json
from pathlib import Path
from typing import List, Dict, Any

from mcp.server.mcpserver import MCPServer

from src.core.models.job import JobTerm
from src.core.models.gap import GapItem
from src.core.services.typst import compile_typst_and_extract
from src.core.services.ats import calculate_ats_metrics
from src.core.services.backlog import update_gaps_backlog
from src.core.workflow.evaluators import check_ats_condition
from src.core.workflow.schema import Policies
from src.adapters.mcp.prompt import get_workflow_instructions
from src.core.paths import PROJECT_ROOT, DOC_DIR, OUTPUT_DIR

POLICIES = Policies()

# Official MCPServer initialization
mcp = MCPServer(
    name="cveck",
    instructions=(
        "Cveck 2.0: Autonomous Resume Tailoring and ATS scoring engine. "
        "INITIALIZATION DIRECTIVE: When receiving a job posting, call the tool 'start_resume_tailoring' "
        "to load the factual profile and workflow rules. "
        "IMPORTANT: If you ALREADY RECEIVED the user profile (USER_PROFILE.md) and workflow instructions "
        "in the initial prompt, SKIP 'start_resume_tailoring' and proceed directly to 'submit_job_terms'."
    )
)

# --- MCP PROMPT ---

@mcp.prompt(name="tailor_resume")
def tailor_resume(job_description: str) -> str:
    """Starts the tailoring process by injecting the real profile, style guide, and tool roadmap."""
    return get_workflow_instructions(job_description)

# --- MCP TOOLS ---

@mcp.tool()
def start_resume_tailoring(job_description: str) -> str:
    """CALL THIS TOOL FIRST upon receiving a target job description to load the factual profile (USER_PROFILE.md), 
    style guide, and state machine."""
    return get_workflow_instructions(job_description)

@mcp.tool()
def submit_job_terms(
    job_title: str,
    company_name: str,
    job_slug: str,
    job_lang: str,
    terms: List[Dict[str, Any]]
) -> str:
    """Registers technical terms, role, company, and language identified in the target job description."""
    slug = job_slug or "cv-tailored"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parsed_terms = [JobTerm.model_validate(t) for t in terms]
    terms_file = OUTPUT_DIR / f"job_terms-{slug}.json"
    terms_file.write_text(
        json.dumps([t.model_dump() for t in parsed_terms], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    req_count = sum(1 for t in parsed_terms if t.required)
    opt_count = len(parsed_terms) - req_count

    return (
        f"✔ Job '{job_title}' @ '{company_name}' registered successfully.\n"
        f"Total of {len(parsed_terms)} terms ({req_count} mandatory, {opt_count} optional/differential) saved to {terms_file.name}.\n"
        "Next step: Call 'record_gaps' if there are real gaps, or proceed to generation and call 'compile_typst'."
    )

@mcp.tool()
def record_gaps(gaps: List[Dict[str, Any]], job_title: str = "", company_name: str = "") -> str:
    """Records confirmed technical gaps into the study backlog (doc/GAPS.md and doc/gaps.json)."""
    if not gaps:
        return "No gaps provided. Proceed to Typst code generation and call 'compile_typst'."

    parsed_gaps = [
        GapItem(
            term=g.get("term", ""),
            category=g.get("category", "other"),
            required=g.get("required", False),
            job_title=job_title or g.get("job_title") or g.get("vaga", ""),
            company_name=company_name or g.get("company_name") or g.get("empresa", ""),
            date=g.get("date") or g.get("data", ""),
            reason=g.get("reason") or g.get("motivo", ""),
            suggestion=g.get("suggestion") or g.get("sugestao", "")
        )
        for g in gaps
    ]

    update_gaps_backlog(parsed_gaps, DOC_DIR / "gaps.json", DOC_DIR / "GAPS.md")
    gap_names = [g.term for g in parsed_gaps]

    return (
        f"✔ {len(parsed_gaps)} gap(s) recorded in backlog doc/GAPS.md: {gap_names}.\n"
        "Compliance reminder: You MUST NOT include these skills in the generated resume.\n"
        "Next step: Write Typst code following CV_STYLE_GUIDE.md and call 'compile_typst'."
    )

@mcp.tool()
def compile_typst(typst_code: str, job_slug: str = "cv-tailored", lang: str = "en") -> str:
    """Compiles Typst code locally, sanitizes syntax, and extracts plaintext from the PDF."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_DIR / f"cv-{job_slug}-{lang}.pdf"
    typ_path = OUTPUT_DIR / f"cv-{job_slug}-{lang}.typ"
    txt_path = OUTPUT_DIR / f"resume-{job_slug}.txt"

    res = compile_typst_and_extract(
        typst_code=typst_code,
        output_pdf_path=pdf_path,
        output_typ_path=typ_path,
        root_dir=PROJECT_ROOT,
        lang=lang
    )

    if not res.success:
        return (
            "❌ TYPST COMPILATION ERROR:\n"
            f"{res.error_message}\n\n"
            "Required action: Fix the Typst code ensuring all matching brackets and quotes are closed, "
            "then call 'compile_typst' again with the corrected code."
        )

    txt_path.write_text(res.extracted_text, encoding="utf-8")

    return (
        f"✔ PDF compiled successfully!\n"
        f"- File: {pdf_path}\n"
        f"- Extracted text: {len(res.extracted_text)} characters saved to {txt_path.name}.\n"
        "Next step: Call 'validate_ats' to evaluate mathematical keyword adherence."
    )

@mcp.tool()
def validate_ats(job_slug: str = "cv-tailored") -> str:
    """Calculates mathematical ATS score and verifies keyword stuffing alerts (> 2%)."""
    terms_file = OUTPUT_DIR / f"job_terms-{job_slug}.json"
    txt_file = OUTPUT_DIR / f"resume-{job_slug}.txt"

    if not terms_file.exists():
        return f"Error: File '{terms_file.name}' not found. Call 'submit_job_terms' first."
    if not txt_file.exists():
        return f"Error: File '{txt_file.name}' not found. Call 'compile_typst' successfully first."

    raw_terms = json.loads(terms_file.read_text(encoding="utf-8"))
    job_terms = [JobTerm.model_validate(t) for t in raw_terms]
    resume_text = txt_file.read_text(encoding="utf-8")

    report = calculate_ats_metrics(
        job_terms=job_terms,
        resume_text=resume_text,
        stuffing_threshold=POLICIES.stuffing_density_threshold
    )

    from src.core.models.state import DomainState
    dummy_state = DomainState(ats_report=report)
    condition = check_ats_condition(dummy_state, POLICIES)

    msg = [
        "📊 ATS TECHNICAL REPORT:",
        f"- Overall Score: {report.score}/100 (Minimum target: {POLICIES.target_ats_score})",
        f"- Mandatory Requirements Coverage: {report.coverage_required_pct}%",
        f"- Overall Keyword Coverage: {report.coverage_pct}%",
    ]

    if report.missing_required:
        msg.append(f"- Missing Mandatory: {', '.join(report.missing_required)}")
    if report.missing_optional:
        msg.append(f"- Missing Optional: {', '.join(report.missing_optional)}")
    if report.stuffing_flags:
        msg.append(f"⚠ Keyword Stuffing Alert (>2%): {report.stuffing_flags}")

    if condition == "approved":
        msg.append("\n🎉 RESULT: APPROVED! Target reached with zero missing mandatory requirements.")
        msg.append("Action: Call 'commit_cv' to finalize the report.")
    elif condition == "unfixable_gaps":
        msg.append("\n🛑 RESULT: SHORT-CIRCUIT APPROVAL.")
        msg.append("All missing mandatory terms are confirmed real gaps in the profile. The resume reached its factual limit.")
        msg.append("Action: Call 'commit_cv' to finalize the report.")
    else:
        msg.append("\n↻ RESULT: REFINEMENT NEEDED.")
        msg.append("Action: Rewrite existing bullet points in Typst to incorporate missing terms (if present in the profile) and call 'compile_typst'.")

    return "\n".join(msg)

@mcp.tool()
def commit_cv(job_slug: str = "cv-tailored", lang: str = "en") -> str:
    """Consolidates final artifacts into the output/ directory and issues the final summary."""
    pdf_path = OUTPUT_DIR / f"cv-{job_slug}-{lang}.pdf"
    txt_path = OUTPUT_DIR / f"resume-{job_slug}.txt"
    terms_path = OUTPUT_DIR / f"job_terms-{job_slug}.json"

    if not pdf_path.exists():
        return f"Error: Final PDF '{pdf_path.name}' not found. Make sure to compile the resume first."

    return (
        "✦ PROCESS COMPLETED SUCCESSFULLY!\n"
        f"- Vector PDF: {pdf_path}\n"
        f"- Plaintext: {txt_path}\n"
        f"- JSON Terms: {terms_path}\n"
        "All artifacts were saved locally. The tailored resume is ready!"
    )

def run_mcp_server():
    """Starts the MCP server via stdio."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    run_mcp_server()