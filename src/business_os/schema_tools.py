from __future__ import annotations

import re
from datetime import date
from typing import Any


def validate_schema(payload: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    schema_type = schema.get("type")

    if schema_type is not None:
        type_error = _validate_type(payload, schema_type, path)
        if type_error is not None:
            return [type_error]

    if "const" in schema and payload != schema["const"]:
        errors.append(f"{path} muss exakt {schema['const']!r} sein")

    if "enum" in schema and payload not in schema["enum"]:
        errors.append(f"{path} muss einer der Werte {schema['enum']} sein")

    if isinstance(payload, str):
        errors.extend(_validate_string(payload, schema, path))
    elif isinstance(payload, (int, float)) and not isinstance(payload, bool):
        errors.extend(_validate_number(payload, schema, path))
    elif isinstance(payload, list):
        errors.extend(_validate_array(payload, schema, path))
    elif isinstance(payload, dict):
        errors.extend(_validate_object(payload, schema, path))

    return errors


def _validate_type(value: Any, expected: str, path: str) -> str | None:
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
    }
    python_type = type_map.get(expected)
    if python_type is None:
        return None
    if expected == "number" and isinstance(value, bool):
        return f"{path} muss vom Typ {expected} sein"
    if not isinstance(value, python_type):
        return f"{path} muss vom Typ {expected} sein"
    return None


def _validate_string(value: str, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    min_length = schema.get("minLength")
    if min_length is not None and len(value) < min_length:
        errors.append(f"{path} muss mindestens {min_length} Zeichen lang sein")
    max_length = schema.get("maxLength")
    if max_length is not None and len(value) > max_length:
        errors.append(f"{path} darf hoechstens {max_length} Zeichen lang sein")
    pattern = schema.get("pattern")
    if pattern and re.fullmatch(pattern, value) is None:
        errors.append(f"{path} entspricht nicht dem erwarteten Muster")
    if schema.get("format") == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            errors.append(f"{path} muss ein ISO-Datum sein")
    return errors


def _validate_number(value: int | float, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    minimum = schema.get("minimum")
    if minimum is not None and value < minimum:
        errors.append(f"{path} muss groesser oder gleich {minimum} sein")
    exclusive_minimum = schema.get("exclusiveMinimum")
    if exclusive_minimum is not None and value <= exclusive_minimum:
        errors.append(f"{path} muss groesser als {exclusive_minimum} sein")
    return errors


def _validate_array(value: list[Any], schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    min_items = schema.get("minItems")
    if min_items is not None and len(value) < min_items:
        errors.append(f"{path} braucht mindestens {min_items} Eintraege")
    item_schema = schema.get("items")
    if item_schema:
        for index, item in enumerate(value):
            errors.extend(validate_schema(item, item_schema, f"{path}[{index}]"))
    return errors


def _validate_object(value: dict[str, Any], schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    required = schema.get("required", [])
    for key in required:
        if key not in value:
            errors.append(f"{path}.{key} fehlt")
    for key, child_schema in schema.get("properties", {}).items():
        if key in value:
            errors.extend(validate_schema(value[key], child_schema, f"{path}.{key}"))
    return errors
