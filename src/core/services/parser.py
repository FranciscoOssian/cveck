import json
import re
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def repair_truncated_json(json_str: str) -> str:
    """Restaura balanceamento de aspas, chaves e colchetes cortados por limite de tokens."""
    json_str = json_str.strip()
    if not json_str:
        return "{}"

    start_idx = -1
    for i, c in enumerate(json_str):
        if c in ("{", "["):
            start_idx = i
            break
    if start_idx == -1:
        return json_str

    json_str = json_str[start_idx:]
    stack = []
    in_string = False
    escape = False

    for char in json_str:
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char in ("{", "["):
                stack.append(char)
            elif char == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif char == "]" and stack and stack[-1] == "[":
                stack.pop()

    if in_string:
        json_str += '"'

    json_str = json_str.rstrip(",: \t\n\r")
    closing_map = {"{": "}", "[": "]"}
    json_str += "".join(closing_map.get(open_c, "") for open_c in reversed(stack))
    return json_str


def extract_and_parse_json(text: str, target_model: Type[T]) -> T:
    """Extrai blocos JSON limpando tags de pensamento (<think>) com fallback resiliente."""
    if not text or not text.strip():
        return target_model()

    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    candidate = match.group(1).strip() if match else cleaned

    brace_start = candidate.find("{")
    bracket_start = candidate.find("[")
    starts = [pos for pos in (brace_start, bracket_start) if pos != -1]
    if starts:
        candidate = candidate[min(starts):]

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        data = json.loads(repair_truncated_json(candidate))

    if isinstance(data, list):
        list_field = next(
            (name for name, f in target_model.model_fields.items() if getattr(f.annotation, "__origin__", None) is list),
            next(iter(target_model.model_fields))
        )
        return target_model(**{list_field: data})

    return target_model.model_validate(data)