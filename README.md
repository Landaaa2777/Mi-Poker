# mi-poker

Texas Hold'em No-Limit para el navegador: un humano contra 1 a 5 bots.

**Solo para entretenimiento. Sin dinero real.** Las fichas son virtuales, viven
solo en memoria durante la partida y no tienen ningún valor fuera del juego.

## Estado

Etapa 1 (completa): motor de poker, bots con cuatro niveles de dificultad,
servidor FastAPI + WebSocket e interfaz web para jugar una partida completa
contra los bots.

Etapa 2 (pulido visual y sonoro), en curso. Ya hecho: pantalla de inicio y
mesa con diseño propio (placas con avatar, cartas y fichas dibujadas, marca en
el tapete), la mano reproducida paso a paso, efectos de sonido, música de
fondo y panel de audio. Falta el movimiento: las cartas y las fichas todavía
aparecen en su sitio, sin volar ni girar.

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

### Sonido y ajustes

El audio empieza con tu primera interacción (un clic o una tecla): los
navegadores no dejan sonar nada antes. Arriba a la derecha hay un botón para
silenciarlo todo y un menú **Ajustes** con el volumen de la música y el de los
efectos por separado. Ahí mismo se pueden desactivar las animaciones: cada
jugada se muestra entonces al instante (por defecto se sigue la preferencia de
movimiento reducido del sistema). Todo se guarda en el navegador.

Los efectos y la música se generan por código, sin archivos. Si prefieres tu
propia música, guarda una pista como `frontend/src/assets/audio/music.mp3`
(o `.ogg`, `.wav`, `.m4a`) y vuelve a compilar: sustituye a la generada y se
repite con un fundido. Los detalles están en el `LEEME.md` de esa carpeta.

## Tests

Backend, desde `backend` con el venv activado:

```powershell
pytest
```

Frontend (línea de tiempo, cola, preferencias y sonidos de cada paso), desde
`frontend`:

```powershell
npm test
```

Los tests del frontend usan partidas reales grabadas del servidor. Para
volver a grabarlas, desde la raíz del proyecto:

```powershell
backend\.venv\Scripts\python.exe frontend\tools\record_fixtures.py
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
  src/               React + TypeScript + Tailwind; solo muestra el estado y
                     envía intenciones ("fold", "raise 400")
  src/timeline/      convierte cada estado del servidor en pasos y los
                     reproduce en orden (línea de tiempo y cola)
  src/audio/         efectos y música generados con la Web Audio API, y qué
                     sonido corresponde a cada paso
  src/assets/audio/  carpeta para una pista de música propia (opcional)
  src/components/    pantalla de inicio, mesa, cartas, fichas, controles y ajustes
  src/guest.ts       identificador de invitado, aislado para cambiarlo por login
  src/settings.ts    preferencias guardadas en el navegador, también aisladas
  tools/             graba partidas reales para los tests del frontend
```

El protocolo de mensajes está descrito en `backend/server/protocol.py`.

### Cómo se reproduce una mano

El servidor no envía sucesos sueltos: tras cada cambio envía la mesa completa,
con un registro de la mano que solo crece. El frontend compara ese registro con
el anterior y lo convierte en pasos (ciegas, reparto, jugadas, cartas
comunitarias, showdown) que se muestran de uno en uno. El reparto no viene del
servidor: se deduce del botón y de los jugadores con fichas, en el mismo orden
que usa el motor. Al vaciarse la cola, lo mostrado es exactamente el estado del
servidor, y solo entonces se activan los botones de acción.

El motor es la única autoridad: baraja con el generador seguro del sistema,
reparte, valida cada acción y paga los botes. Bots y cliente solo reciben una
vista (`poker_engine/views.py`) con la información pública y sus propias cartas.
