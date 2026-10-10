# mi-poker

Texas Hold'em No-Limit para el navegador: un humano contra 1 a 5 bots.

**Solo para entretenimiento. Sin dinero real.** Las fichas son virtuales, viven
solo en memoria durante la partida y no tienen ningún valor fuera del juego.

## Estado

Etapa 1, hito 2 de 3: motor de poker y bots con cuatro niveles de dificultad,
con sus tests y una simulación bot contra bot. Todavía no hay servidor ni
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

## Simulación bot contra bot

Juega miles de manos entre los cuatro niveles y muestra cuántas ciegas grandes
gana cada uno cada 100 manos (bb/100). Tarda alrededor de medio minuto.

```powershell
python scripts\simulate.py
python scripts\simulate.py --duels          # añade los duelos mano a mano
python scripts\simulate.py --hands 200000   # más manos, resultado más estable
```

El orden esperado es Experto > Difícil > Medio > Fácil.

## Bots

Todos comparten la misma interfaz: `decide(vista)` recibe solo la mesa pública y
sus propias cartas, y devuelve fold, call o raise con monto. Cambiar de nivel
cambia la estrategia, nunca la información.

| Nivel | Cómo juega |
|---|---|
| Fácil | Suelto y pasivo: juega casi todo, paga de más, apuesta poco y casi no farolea. |
| Medio | Elige manos por su fuerza inicial, usa pot odds básicos y respeta las apuestas grandes. |
| Difícil | Equity por Monte Carlo, pot odds, posición, tamaños de apuesta variables y faroles ocasionales. |
| Experto | Como Difícil, pero observa lo que cada rival hace en público y se adapta: rangos, valor y faroles calculados. |

Cada bot tiene además un nombre y una personalidad (`bots/personalities.py`) que
ajustan levemente sus decisiones.

## Estructura

```
backend/
  poker_engine/   motor del juego en Python puro (sin dependencias web)
  bots/           estrategias por nivel; solo usan la vista pública del motor
  scripts/        demos y simulaciones por consola
  tests/          tests con pytest
```

El motor es la única autoridad: baraja con el generador seguro del sistema,
reparte, valida cada acción y paga los botes. Bots y cliente solo reciben una
vista (`poker_engine/views.py`) con la información pública y sus propias cartas.
