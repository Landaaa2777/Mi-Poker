# mi-poker

Texas Hold'em No-Limit para el navegador: un humano contra 1 a 5 bots.

**Solo para entretenimiento. Sin dinero real.** Las fichas son virtuales, viven
solo en memoria durante la partida y no tienen ningún valor fuera del juego.

## Estado

Etapa 1, hito 3 de 3: motor de poker, bots con cuatro niveles de dificultad,
servidor FastAPI + WebSocket e interfaz web simple para jugar una partida
completa contra los bots.

## Requisitos

- Python 3.12 o superior.
- Node.js LTS (para la interfaz web).

## Instalación

Desde la carpeta `backend`, en PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Y la interfaz, desde la carpeta `frontend`:

```powershell
npm install
```

## Jugar

Forma simple: compilar la interfaz una vez y dejar que el servidor la sirva.

```powershell
cd frontend
npm run build
cd ..\backend
.\.venv\Scripts\Activate.ps1
uvicorn server.app:app
```

Abrir http://localhost:8000. Se elige el número de bots, la dificultad, las
fichas iniciales y las blinds, y se juega con los botones de la mesa.

Para desarrollar, con recarga automática, en dos terminales:

```powershell
# terminal 1, en backend (con el venv activado)
uvicorn server.app:app --reload
# terminal 2, en frontend
npm run dev
```

y abrir http://localhost:5173.

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
  server/         FastAPI + WebSocket; partidas en memoria, una por invitado
  scripts/        demos y simulaciones por consola
  tests/          tests con pytest
frontend/
  src/            React + TypeScript + Tailwind; solo muestra el estado y
                  envía intenciones ("fold", "raise 400")
  src/guest.ts    identificador de invitado, aislado para cambiarlo por login
```

El protocolo de mensajes está descrito en `backend/server/protocol.py`.

El motor es la única autoridad: baraja con el generador seguro del sistema,
reparte, valida cada acción y paga los botes. Bots y cliente solo reciben una
vista (`poker_engine/views.py`) con la información pública y sus propias cartas.
