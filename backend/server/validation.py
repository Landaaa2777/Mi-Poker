"""Mensajes mal formados, explicados en una frase para el cliente."""

from __future__ import annotations

from pydantic import ValidationError

# Ningún mensaje del juego se acerca a esto: lo más largo es un cambio de opciones.
MAX_MESSAGE = 4096
TOO_LONG = "Mensaje inválido: demasiado largo"


def explain(error: ValidationError) -> str:
    """Primer problema de un mensaje mal formado, en una frase."""
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"] if not str(part).startswith("function"))
    reason = first["msg"].removeprefix("Value error, ")
    return f"Mensaje inválido ({field}): {reason}" if field else f"Mensaje inválido: {reason}"
