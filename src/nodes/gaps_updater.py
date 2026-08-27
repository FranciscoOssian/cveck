from src.state import CVState
from src.tools.file_manager import update_gaps_backlog

def gaps_updater_node(state: CVState) -> dict:
    gaps = state.get("detected_gaps", [])
    update_gaps_backlog(gaps)
    return {}