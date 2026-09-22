from typing import List
from src.core.models.gap import GapItem
from src.core.services.backlog import update_gaps_backlog
from src.core.paths import DOC_DIR


def execute_update_gaps(gaps: List[GapItem]) -> None:
    update_gaps_backlog(
        new_gaps=gaps,
        gaps_json_path=DOC_DIR / "gaps.json",
        gaps_md_path=DOC_DIR / "GAPS.md"
    )