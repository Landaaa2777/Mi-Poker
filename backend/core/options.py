"""Del modelo de opciones de un juego al esquema que pinta el panel de opciones.

Cada juego escribe sus opciones una sola vez, como un modelo de pydantic con
título y límites en cada campo. El servidor valida con ese modelo lo que manda
el cliente, y este módulo lo traduce a una lista sencilla para el menú:

    {"key": "bots", "type": "number", "label": "Bots", "default": 3, "min": 1, "max": 5, "step": 1}
    {"key": "difficulty", "type": "choice", "label": "Dificultad", "default": "medium",
     "choices": [{"value": "easy", "label": "Fácil", "description": "..."}, ...]}
    {"key": "dealer_hits_soft_17", "type": "toggle", "label": "...", "default": false}
"""

from __future__ import annotations

from typing import Any


def describe_options(model: Any) -> list[dict[str, Any]]:
    """Las opciones de un modelo, en el orden en que están escritas.

    `model` es una clase de pydantic: aquí solo se usa su `model_json_schema()`,
    así que este módulo no depende de ninguna librería.
    """
    schema = model.model_json_schema()
    described = []
    for key, field in schema.get("properties", {}).items():
        if field.get("hidden"):
            continue  # no se elige en el panel (por ejemplo, el nombre en la mesa)
        option: dict[str, Any] = {
            "key": key,
            "label": field.get("title", key),
            "default": field.get("default"),
        }
        if field.get("description"):
            option["help"] = field["description"]
        if field.get("type") == "boolean":
            option["type"] = "toggle"
        elif "enum" in field:
            option["type"] = "choice"
            option["choices"] = field.get("choices") or [
                {"value": value, "label": str(value)} for value in field["enum"]
            ]
        elif field.get("type") == "integer":
            option["type"] = "number"
            option["min"] = field.get("minimum")
            option["max"] = field.get("maximum")
            option["step"] = field.get("multipleOf", 1)
            if field.get("presets"):
                option["presets"] = field["presets"]
        else:
            continue  # texto libre u otros tipos: no van en el panel
        described.append(option)
    return described
