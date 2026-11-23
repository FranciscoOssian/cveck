import json
from pathlib import Path
from typing import List, Dict, Any

from mcp.server.mcpserver import MCPServer

from src.core.models.job import JobTerm
from src.core.models.gap import GapItem
from src.core.models.state import DomainState
from src.core.use_cases.compile_cv import execute_compile_cv
from src.core.use_cases.validate_ats import execute_validate_ats
from src.core.use_cases.update_gaps import execute_update_gaps
from src.core.use_cases.commit_artifacts import execute_commit_artifacts
from src.core.workflow.evaluators import check_ats_condition
from src.core.workflow.schema import WorkflowConfig
from src.adapters.mcp.prompt import get_workflow_instructions
from src.core.paths import OUTPUT_DIR, CORE_DIR, PROMPTS_DIR

PROMPT_MAP = {
    "submit_job_terms": "extract_terms.md",
    "extract_terms": "extract_terms.md",
    "record_gaps": "find_gaps.md",
    "find_gaps": "find_gaps.md",
    "submit_pruned_profile": "prune_profile.md",
    "prune_profile": "prune_profile.md",
    "compile_typst": "generate_cv.md",
    "generate_cv": "generate_cv.md",
    "fix_typst": "fix_typst.md",
    "refine_cv": "refine_cv.md",
}

_WORKFLOW_CFG = WorkflowConfig.model_validate(
    __import__("yaml").safe_load((CORE_DIR / "workflow.yaml").read_text(encoding="utf-8"))
)
POLICIES = _WORKFLOW_CFG.policies

mcp = MCPServer(
    name="cveck",
    instructions=(
        "Cveck: Autonomous Resume Tailoring and ATS scoring engine.\n"
        "WORKFLOW DIRECTIVE: Before executing any major step, ALWAYS call 'get_tool_instructions' "
        "passing the tool name (e.g., 'submit_job_terms', 'record_gaps', 'submit_pruned_profile', 'compile_typst') to retrieve "
        "the exact technical rules, constraints, and prompt directives.\n"
        "Recommended sequence: 1. submit_job_terms -> 2. record_gaps -> 3. submit_pruned_profile -> "
        "4. compile_typst -> 5. validate_ats -> (refine if needed) -> 6. commit_cv."
    )
)


@mcp.prompt(name="tailor_resume")
def tailor_resume(job_description: str) -> str:
    """Starts tailoring process by injecting candidate profile, style guide, and workflow map."""
    return get_workflow_instructions(job_description)


@mcp.tool()
def start_resume_tailoring(job_description: str) -> str:
    """CALL THIS FIRST upon receiving a job posting to load the factual profile and state machine rules."""
    return get_workflow_instructions(job_description)


@mcp.tool()
def get_tool_instructions(tool_name: str) -> str:
    """Returns the strict instructions, prompt guidelines, and constraints associated with a specific tool or workflow step."""
    normalized_name = tool_name.strip().lower()
    prompt_file = PROMPT_MAP.get(normalized_name)

    if not prompt_file:
        available = list(set(PROMPT_MAP.keys()))
        return (
            f"No specific guidelines found for '{tool_name}'.\n"
            f"Available tool/step names: {available}"
        )

    file_path = PROMPTS_DIR / prompt_file
    if not file_path.exists():
        return f"Instruction file '{prompt_file}' not found in {PROMPTS_DIR}."

    content = file_path.read_text(encoding="utf-8")
    
    if prompt_file == "generate_cv.md":
        style_guide_path = PROMPTS_DIR / "CV_STYLE_GUIDE.md"
        if style_guide_path.exists():
            content += "\n\n---\n" + style_guide_path.read_text(encoding="utf-8")

    return content


@mcp.tool()
def submit_job_terms(
    job_title: str,
    company_name: str,
    job_slug: str,
    job_lang: str,
    terms: List[Dict[str, Any]]
) -> str:
    """Registers technical terms, role, company, and language identified in target job description."""
    parsed_terms = [JobTerm.model_validate(t) for t in terms]
    artifacts = execute_commit_artifacts(
        job_slug=job_slug,
        job_terms=parsed_terms,
        txt_content=""
    )
    req_count = sum(1 for t in parsed_terms if t.required)
    opt_count = len(parsed_terms) - req_count

    return (
        f"✔ Job '{job_title}' @ '{company_name}' registered successfully.\n"
        f"Saved {len(parsed_terms)} terms ({req_count} mandatory, {opt_count} differential) to {artifacts['terms_file']}.\n"
        "Next step: Call 'record_gaps' to log unacquired requirements, or call 'submit_pruned_profile'."
    )


@mcp.tool()
def record_gaps(gaps: List[Dict[str, Any]], job_title: str = "", company_name: str = "") -> str:
    """Records confirmed skill gaps into the study backlog (doc/GAPS.md and doc/gaps.json)."""
    if not gaps:
        return "No gaps provided. Proceed to profile pruning and call 'submit_pruned_profile'."

    parsed_gaps = [
        GapItem(
            term=g.get("term", ""),
            category=g.get("category", "other"),
            required=g.get("required", False),
            job_title=job_title or g.get("job_title", ""),
            company_name=company_name or g.get("company_name", ""),
            date=g.get("date", ""),
            reason=g.get("reason", ""),
            suggestion=g.get("suggestion", "")
        )
        for g in gaps
    ]

    execute_update_gaps(parsed_gaps)
    gap_names = [g.term for g in parsed_gaps]

    return (
        f"✔ {len(parsed_gaps)} gap(s) recorded in backlog doc/GAPS.md: {gap_names}.\n"
        "Compliance reminder: You MUST NOT include these skills in the generated resume.\n"
        "Next step: Call 'submit_pruned_profile' to apply the Relevance Razor to the profile before generating Typst."
    )


@mcp.tool()
def submit_pruned_profile(pruned_profile: str, job_slug: str = "cv-tailored") -> str:
    """Saves the pruned candidate profile to output/profile_pruned-{job_slug}.md after applying the Relevance Razor."""
    if not pruned_profile or not pruned_profile.strip():
        return "Error: Pruned profile content cannot be empty."

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = job_slug or "cv-tailored"
    out_file = OUTPUT_DIR / f"profile_pruned-{slug}.md"
    out_file.write_text(pruned_profile.strip(), encoding="utf-8")

    return (
        f"✔ Pruned profile successfully saved to {out_file}.\n"
        "Next step: Using ONLY the pruned profile above, write the Typst code and call 'compile_typst'."
    )


@mcp.tool()
def compile_typst(typst_code: str, job_slug: str = "cv-tailored", lang: str = "en") -> str:
    """Compiles Typst code locally, sanitizes syntax, and extracts plaintext from vector PDF."""
    res = execute_compile_cv(typst_code=typst_code, job_slug=job_slug, job_lang=lang)

    if not res.success:
        return (
            "❌ TYPST COMPILATION ERROR:\n"
            f"{res.error_message}\n\n"
            "Required action: Fix the Typst code ensuring all matching brackets and quotes are closed, "
            "then call 'compile_typst' again with the corrected version."
        )

    return (
        f"✔ PDF compiled successfully!\n"
        f"- File: {res.pdf_path}\n"
        f"- Extracted text: {len(res.extracted_text)} characters saved.\n"
        "Next step: Call 'validate_ats' to evaluate mathematical keyword adherence."
    )


@mcp.tool()
def validate_ats(job_slug: str = "cv-tailored") -> str:
    """Calculates mathematical ATS score, checking stuffing alerts and mandatory criteria."""
    terms_file = OUTPUT_DIR / f"job_terms-{job_slug}.json"
    txt_file = OUTPUT_DIR / f"resume-{job_slug}.txt"

    if not terms_file.exists():
        return f"Error: File '{terms_file.name}' not found. Call 'submit_job_terms' first."
    if not txt_file.exists():
        return f"Error: File '{txt_file.name}' not found. Call 'compile_typst' successfully first."

    raw_terms = json.loads(terms_file.read_text(encoding="utf-8"))
    job_terms = [JobTerm.model_validate(t) for t in raw_terms]
    resume_text = txt_file.read_text(encoding="utf-8")

    report, _ = execute_validate_ats(
        job_terms=job_terms,
        resume_text=resume_text,
        target_score=POLICIES.target_ats_score,
        stuffing_threshold=POLICIES.stuffing_density_threshold
    )

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
        msg.append("All missing mandatory terms are confirmed real gaps in profile. Resume reached factual limits.")
        msg.append("Action: Call 'commit_cv' to finalize the report.")
    else:
        msg.append("\n↻ RESULT: REFINEMENT NEEDED.")
        msg.append("Action: Rewrite existing bullet points in Typst to incorporate missing terms (backed strictly by the pruned profile) and call 'compile_typst'.")

    return "\n".join(msg)


@mcp.tool()
def commit_cv(job_slug: str = "cv-tailored", lang: str = "en") -> str:
    """Consolidates final artifacts in output/ directory and prints closing summary."""
    pdf_path = OUTPUT_DIR / f"cv-{job_slug}-{lang}.pdf"
    txt_path = OUTPUT_DIR / f"resume-{job_slug}.txt"
    terms_path = OUTPUT_DIR / f"job_terms-{job_slug}.json"
    pruned_path = OUTPUT_DIR / f"profile_pruned-{job_slug}.md"

    if not pdf_path.exists():
        return f"Error: Final PDF '{pdf_path.name}' not found. Make sure to compile the resume first."

    lines = [
        "✦ PROCESS COMPLETED SUCCESSFULLY!",
        f"- Vector PDF: {pdf_path}",
        f"- Plaintext: {txt_path}",
        f"- JSON Terms: {terms_path}",
    ]
    if pruned_path.exists():
        lines.append(f"- Pruned Profile: {pruned_path}")

    lines.append("All artifacts were saved locally. The tailored resume is ready!")
    return "\n".join(lines)


def run_mcp_server():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_mcp_server()