from typing import Dict, Any


def extract_token_usage(response) -> Dict[str, int]:
    """Extracts input, output, and total tokens with unified LangChain support and fallbacks."""
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        in_tok = response.usage_metadata.get("input_tokens", 0)
        out_tok = response.usage_metadata.get("output_tokens", 0)
        total_tok = response.usage_metadata.get("total_tokens", in_tok + out_tok)
        return {"input_tokens": in_tok, "output_tokens": out_tok, "total_tokens": total_tok}

    meta = getattr(response, "response_metadata", {})
    usage = meta.get("token_usage") or meta.get("usage") or {}
    in_tok = usage.get("prompt_tokens", usage.get("input_tokens", 0))
    out_tok = usage.get("completion_tokens", usage.get("output_tokens", 0))
    total_tok = usage.get("total_tokens", in_tok + out_tok)

    return {"input_tokens": in_tok, "output_tokens": out_tok, "total_tokens": total_tok}


def accumulate_tokens(current_usage: Dict[str, Any], node_name: str, node_tokens: Dict[str, int]) -> Dict[str, Any]:
    """Accumulates consumed tokens globally and tracks by node (including retry loops)."""
    usage = current_usage.copy() if current_usage else {
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "by_node": {}
    }

    usage["input_tokens"] += node_tokens.get("input_tokens", 0)
    usage["output_tokens"] += node_tokens.get("output_tokens", 0)
    usage["total_tokens"] += node_tokens.get("total_tokens", 0)

    if node_name not in usage["by_node"]:
        usage["by_node"][node_name] = node_tokens.copy()
    else:
        usage["by_node"][node_name]["input_tokens"] += node_tokens.get("input_tokens", 0)
        usage["by_node"][node_name]["output_tokens"] += node_tokens.get("output_tokens", 0)
        usage["by_node"][node_name]["total_tokens"] += node_tokens.get("total_tokens", 0)

    return usage