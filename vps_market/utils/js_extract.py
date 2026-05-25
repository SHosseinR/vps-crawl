from __future__ import annotations

import ast
import json
import re
from typing import Any


def extract_balanced(text: str, start: int, opener: str, closer: str) -> str:
    depth = 0
    in_string: str | None = None
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue

        if char in {"'", '"', "`"}:
            in_string = char
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise ValueError("Could not find balanced JavaScript literal")


def extract_var_literal(html: str, marker: str, opener: str = "{", closer: str = "}") -> str:
    marker_index = html.find(marker)
    if marker_index < 0:
        raise ValueError(f"Marker not found: {marker}")
    start = html.find(opener, marker_index)
    if start < 0:
        raise ValueError(f"Literal opener not found after marker: {marker}")
    return extract_balanced(html, start, opener, closer)


def load_json_or_js_literal(literal: str) -> Any:
    cleaned = literal.strip().rstrip(";")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    pythonish = cleaned.replace("\\/", "/")
    pythonish = re.sub(r"\btrue\b", "True", pythonish)
    pythonish = re.sub(r"\bfalse\b", "False", pythonish)
    pythonish = re.sub(r"\bnull\b", "None", pythonish)
    try:
        return ast.literal_eval(pythonish)
    except (SyntaxError, ValueError):
        import chompjs

        return chompjs.parse_js_object(cleaned)
