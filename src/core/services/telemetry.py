from typing import Dict, Any

def extract_token_usage(response: Any) -> Dict[str, int]:
    """Extracts input, output, and total tokens from unified LangChain responses."""
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