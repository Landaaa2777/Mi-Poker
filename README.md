# mi-poker

Texas Hold'em No-Limit para el navegador: un humano contra 1 a 5 bots.

**Solo para entretenimiento. Sin dinero real.** Las fichas son virtuales, viven
solo en memoria durante la partida y no tienen ningún valor fuera del juego.

## Estado

Etapa 1 (completa): motor de poker, bots con cuatro niveles de dificultad,
servidor FastAPI + WebSocket e interfaz web para jugar una partida completa
contra los bots.

Etapa 2 (completa): pulido visual y sonoro. Pantalla de inicio y mesa con
diseño propio y colores de casino, baraja clásica, la mano reproducida paso a
paso con animaciones, efectos de sonido, música de fondo y un panel de ajustes
con los volúmenes y el interruptor de animaciones.

Etapa 3 (cuentas), en curso. Ya hecho: crear una cuenta, entrar y salir. La
cuenta es opcional: sin ella se sigue jugando como invitado. Quedan el perfil
con estadísticas y el saldo de fichas guardado en la cuenta.

Todavía no hay minijuegos ni partidas entre personas: son etapas futuras. Cada
partida vive en la memoria del servidor y se pierde al cerrarlo; las cuentas
sí se guardan.

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

### Cuentas

Arriba a la derecha, **Entrar** abre la ventana para iniciar sesión o crear
una cuenta: solo hacen falta un nombre de usuario (de 3 a 16 letras sin
acento, números, guion o guion bajo) y una contraseña de al menos 8
caracteres. No se pide correo, así que una contraseña olvidada no se puede
recuperar.

Con la sesión iniciada juegas con el nombre de tu cuenta y la sesión dura 30
días en ese navegador, hasta que pulses **Salir**. Cada cuenta tiene su propia
partida, distinta de la que tuvieras como invitado.

Las cuentas se guardan en `backend/data/mi-poker.db` (SQLite), que se crea
solo la primera vez y no se sube a git. Para usar otro archivo, define la
variable `MI_POKER_DB` antes de arrancar el servidor. Borrar ese archivo
borra todas las cuentas.

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
completo: blinds, acciones, mesa, showdown y reparto de botes. Desde `backend`
con el venv activado:

```powershell
python scripts\demo_hand.py
```

## Simulación bot contra bot

Juega miles de manos entre los cuatro niveles y muestra cuántas ciegas grandes
gana cada uno cada 100 manos (bb/100). Tarda alrededor de medio minuto. Desde
`backend` con el venv activado:

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
  accounts/       cuentas en Python puro: contraseñas, usuarios y sesiones (SQLite)
  server/         FastAPI + WebSocket; partidas en memoria, una por jugador,
                  y las rutas de cuentas (`accounts_api.py`)
  data/           la base de datos de cuentas (se crea sola; fuera de git)
  scripts/        demos y simulaciones por consola
  tests/          tests con pytest
frontend/
  src/               React + TypeScript + Tailwind; solo muestra el estado y
                     envía intenciones ("fold", "raise 400")
  src/timeline/      convierte cada estado del servidor en pasos y los
                     reproduce en orden (línea de tiempo y cola)
  src/motion/        animaciones: fichas y cartas que cruzan la mesa, y la base
                     común (curvas, velocidad, de dónde sale cada pieza)
  src/audio/         efectos y música generados con la Web Audio API, y qué
                     sonido corresponde a cada paso
  src/assets/audio/  carpeta para una pista de música propia (opcional)
  src/components/    pantalla de inicio, mesa, fichas, controles, ajustes y cuenta
  src/components/cards/  cómo se pinta cada carta: cara clásica o cara sencilla
  src/assets/cards/  las 52 caras de la baraja clásica (CC0)
  src/guest.ts       identificador de quien juega sin cuenta
  src/account.ts     todo lo de la cuenta: registrarse, entrar y salir
  src/settings.ts    preferencias guardadas en el navegador, también aisladas
  tools/             graba partidas reales para los tests y prepara la baraja
```

El protocolo de mensajes de la mesa está descrito en
`backend/server/protocol.py`, y las rutas de cuentas en
`backend/server/accounts_api.py`.

## Cómo está hecho

### Cartas

Las caras son la baraja clásica inglesa de Adrian Kennard, publicada como CC0
(dominio público) en https://www.me.uk/cards/. Sus figuras están calcadas de
una baraja Goodall & Son del siglo XIX, el diseño del que descienden las
barajas de póker actuales; no llevan el nombre ni los dibujos de ninguna
marca. Los archivos están en `frontend/src/assets/cards/`, con su `LEEME.md`.

Son dibujo propio el dorso (rojo, con rombos y el emblema del juego), el
adorno del as de picas y la cara sencilla de las cartas pequeñas de los
rivales, que lleva solo el valor y el palo para que se lea bien.

Para volver a preparar la baraja desde el original:

```powershell
node frontend\tools\import_cards.mjs <carpeta con los SVG descargados>
```

### Animaciones

Las cartas se mueven al estilo de Balatro, con nuestro propio dibujo: salen del
mazo volando hacia cada jugador, las tuyas se voltean en 3D al llegar, las
comunitarias giran en el aire y aterrizan con un pequeño rebote, y en reposo
flotan apenas. Tus cartas y las de la mesa se inclinan al pasar el ratón; las tuyas,
además, se levantan al pulsarlas (es un adorno: no cambia el juego). Las fichas
van del jugador al bote y del bote al ganador, y las cartas de quien se retira
se deslizan hacia el centro y se desvanecen.

Solo se animan `transform` y `opacity`, y cada movimiento dura menos de medio
segundo. Con las animaciones desactivadas en **Ajustes** (o si el sistema pide
movimiento reducido) no se mueve nada.

### Sonido

El juego no trae ningún archivo de audio: cada efecto y la música se
sintetizan en el momento con la Web Audio API (`frontend/src/audio/`); la
única excepción es la pista opcional que puedes poner tú. Hay dos canales,
efectos y música, cada uno con su volumen, y un interruptor general. Con la
pestaña oculta no suena nada.

### Cuentas y sesión

- **Contraseñas**: nunca se guardan. Se guarda un hash scrypt con una sal
  distinta por cuenta; el coste sigue la recomendación de OWASP.
- **Sesión**: al entrar, el servidor crea un token al azar y lo manda en una
  cookie `HttpOnly` (los scripts de la página no pueden leerla) y
  `SameSite=Lax`. En la base de datos solo queda el hash del token.
- **Quién soy**: lo decide el servidor al abrir la conexión con la mesa. Si la
  cookie es de una sesión válida, juegas con esa cuenta; si no, como invitado.
  El nombre en la mesa lo pone el servidor.
- **Intentos fallidos**: el mensaje es el mismo exista o no el usuario, y tras
  cinco fallos en un minuto hay que esperar para volver a intentarlo.
- **Otras webs**: las peticiones de cuenta y la conexión con la mesa se
  rechazan si vienen de otra página.
- **Cerrar sesión** borra la sesión en el servidor y corta sus conexiones
  abiertas.

Pensado para jugar en local. Antes de publicarlo en internet haría falta, como
mínimo, servirlo por HTTPS y limitar cuántas cuentas se pueden crear.

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

## Créditos

- Caras de las cartas: baraja de Adrian Kennard, CC0 (dominio público),
  https://www.me.uk/cards/. Detalles en `frontend/src/assets/cards/LEEME.md`.
- Todo lo demás (nombre, emblema, dorso, mesa, avatares, textos, efectos de
  sonido y música) es propio de este proyecto.
