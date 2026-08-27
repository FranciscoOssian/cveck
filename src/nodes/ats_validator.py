from src.state import CVState
from src.tools.ats_scorer import calculate_ats_metrics
from src.config import TARGET_ATS_SCORE


def ats_validator_node(state: CVState) -> dict:
    report = calculate_ats_metrics(state.get("job_terms", []), state.get("txt_content", ""))
    is_approved = (not report.hard_fail) and (report.score >= TARGET_ATS_SCORE)

    return {
        "ats_report": report,
        "is_approved": is_approved
    }