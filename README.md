# mi-poker

Texas Hold'em No-Limit para el navegador: un humano contra 1 a 5 bots.

**Solo para entretenimiento. Sin dinero real.** Las fichas son virtuales, viven
solo en memoria durante la partida y no tienen ningún valor fuera del juego.

## Estado

Etapa 1, hito 1 de 3: motor de poker y tests. Todavía no hay bots, servidor ni
interfaz web.

## Requisitos

- Python 3.12 o superior.

## Instalación

Desde la carpeta `backend`, en PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Tests

```powershell
pytest
```

## Demo por consola

Juega una mano entre cuatro jugadores que actúan al azar e imprime el registro
completo: blinds, acciones, mesa, showdown y reparto de botes.

```powershell
python scripts\demo_hand.py
```

## Estructura

```
backend/
  poker_engine/   motor del juego en Python puro (sin dependencias web)
  scripts/        demos por consola
  tests/          tests con pytest
```

El motor es la única autoridad: baraja con el generador seguro del sistema,
reparte, valida cada acción y paga los botes. Bots y cliente solo reciben una
vista (`poker_engine/views.py`) con la información pública y sus propias cartas.
