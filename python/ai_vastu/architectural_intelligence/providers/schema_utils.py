from __future__ import annotations

from typing import Any

_ALLOWED_SCHEMA_KEYS = {
    "$id",
    "$defs",
    "$ref",
    "$anchor",
    "type",
    "format",
    "title",
    "description",
    "enum",
    "items",
    "prefixItems",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "anyOf",
    "oneOf",
    "properties",
    "additionalProperties",
    "required",
}


def sanitize_gemini_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [sanitize_gemini_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    result: dict[str, Any] = {}
    if "const" in value:
        result["enum"] = [value["const"]]

    for key, item in value.items():
        if key == "const" or key not in _ALLOWED_SCHEMA_KEYS:
            continue
        if (key == "properties" and isinstance(item, dict)) or (
            key == "$defs" and isinstance(item, dict)
        ):
            result[key] = {
                str(name): sanitize_gemini_schema(schema) for name, schema in item.items()
            }
        else:
            result[key] = sanitize_gemini_schema(item)
    return result
