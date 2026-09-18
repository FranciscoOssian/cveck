from pathlib import Path
import yaml
from langgraph.graph import StateGraph, START, END

from src.adapters.langgraph.state import LangGraphState
from src.core.workflow.schema import WorkflowConfig
from src.adapters.langgraph.nodes import (
    term_extractor_node,
    gap_finder_node,
    gaps_updater_node,
    cv_generator_node,
    typst_compiler_node,
    typst_fixer_node,
    ats_validator_node,
    cv_refiner_node,
    committer_node
)
from src.adapters.langgraph.router import route_after_typst_compiler, route_after_ats

WORKFLOW_YAML_PATH = Path(__file__).resolve().parent.parent.parent / "core" / "workflow.yaml"

NODE_MAPPING = {
    "term_extractor": term_extractor_node,
    "gap_finder": gap_finder_node,
    "gaps_updater": gaps_updater_node,
    "cv_generator": cv_generator_node,
    "typst_compiler": typst_compiler_node,
    "typst_fixer": typst_fixer_node,
    "ats_validator": ats_validator_node,
    "cv_refiner": cv_refiner_node,
    "committer": committer_node,
}


def build_langgraph():
    """Lê workflow.yaml e compila o StateGraph dinamicamente."""
    raw = yaml.safe_load(WORKFLOW_YAML_PATH.read_text(encoding="utf-8"))
    config = WorkflowConfig.model_validate(raw)

    workflow = StateGraph(LangGraphState)

    # 1. Registra nós descritos no YAML
    for step in config.steps:
        if step.id in NODE_MAPPING:
            workflow.add_node(step.id, NODE_MAPPING[step.id])

    # 2. Conecta Entrypoint
    workflow.add_edge(START, config.entrypoint)

    # 3. Conecta Transições
    for step in config.steps:
        for trans in step.transitions:
            if trans.type == "direct":
                workflow.add_edge(step.id, trans.target)

            elif trans.type == "conditional":
                if trans.condition == "check_compilation":
                    workflow.add_conditional_edges(
                        step.id,
                        lambda s, p=config.policies: route_after_typst_compiler(s, p),
                        trans.target  # {"syntax_error": "typst_fixer", "max_step_error": "committer", "success": "ats_validator"}
                    )
                elif trans.condition == "check_ats_result":
                    workflow.add_conditional_edges(
                        step.id,
                        lambda s, p=config.policies: route_after_ats(s, p),
                        trans.target  # {"approved": "committer", "max_retries": "committer", ...}
                    )

            elif trans.type == "end":
                workflow.add_edge(step.id, END)

    return workflow.compile()


app = build_langgraph()