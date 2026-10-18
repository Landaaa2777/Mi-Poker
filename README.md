# mi-poker

Juegos de cartas para el navegador, contra bots: **Poker Hold'em**,
**Blackjack** y **Prisma**, un juego de descarte con las reglas del clásico y
una identidad propia. Se elige a qué jugar en un menú principal.

**Solo para entretenimiento. Sin dinero real.** Las fichas son virtuales y no
tienen ningún valor fuera del juego: no se compran, no se venden y no se
canjean por nada.

## Estado

- Etapa 1 (completa): motor de poker, bots con cuatro niveles de dificultad,
  servidor FastAPI + WebSocket e interfaz web.
- Etapa 2 (completa): pulido visual y sonoro: mesa con colores de casino,
  baraja clásica, animaciones, efectos de sonido y música.
- Etapa 3 (completa): cuentas opcionales, con perfil, estadísticas y saldo de
  fichas virtuales.
- Etapa 4 (completa): plataforma de juegos. Menú principal, el poker de
  siempre, blackjack y Prisma, cada juego como un módulo enchufable.

Todavía no hay minijuegos ni partidas entre personas: son etapas futuras (en el
menú salen como "Próximamente"). Cada partida vive en la memoria del servidor y
se pierde al cerrarlo; las cuentas sí se guardan.

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

Abrir http://localhost:8000. Se abre el menú: una tarjeta por juego, con su
descripción y cuántos jugadores admite. Cada juego tiene su dirección propia
(`/poker`, `/blackjack`, `/prisma`), así que también se puede entrar directo o
guardar el enlace.

Para desarrollar, con recarga automática, en dos terminales:

```powershell
# terminal 1, en backend (con el venv activado)
uvicorn server.app:app --reload
# terminal 2, en frontend
npm run dev
```

y abrir http://localhost:5173.

### El menú y las partidas

Arriba está siempre la misma cabecera: el nombre (que lleva al menú), el botón
**Menú**, la cuenta y los ajustes. Si sales de un juego con una partida en
curso, se pide confirmación; la partida no se pierde: queda en pausa y su
tarjeta del menú ofrece **Continuar partida**. Cada identidad (tu cuenta, o tu
navegador si juegas como invitado) tiene una partida por juego.

## Los juegos

### Poker Hold'em

Texas Hold'em No-Limit contra 1 a 5 bots. Se eligen el número de bots, la
dificultad, las fichas iniciales y las ciegas. Ciegas y botón que rota, side
pots, empates y eliminación como en las reglas oficiales.

### Blackjack

Tú contra el crupier, con 0 a 4 bots en los otros asientos.

- Zapato de 6 mazos. La carta de corte va hacia el 75 %: cuando sale, se
  termina la ronda y se rebaraja.
- El blackjack paga 3 a 2 y el empate devuelve la apuesta. Las apuestas van de
  10 en 10, entre la mínima y la máxima que elijas.
- Puedes pedir, plantarte, doblar (con las dos primeras cartas, también tras
  dividir) y dividir parejas hasta 4 manos; los ases divididos reciben una sola
  carta. Si el crupier enseña un As, se ofrece seguro (paga 2 a 1).
- Opciones: el crupier pide con 17 blando (por defecto se planta) y rendición
  tardía (por defecto no).
- El crupier mira si tiene blackjack cuando enseña un As o un 10. Su carta
  tapada no llega a tu navegador hasta que la destapa.

### Prisma

Las reglas del juego de descarte clásico, con nombre, cartas y vocabulario
propios. El nombre "Prisma" es provisional.

- 108 cartas en cuatro palos, cada uno con su forma y su color (así también se
  distinguen sin ver los colores): **Panal** (hexágono, naranja cobre),
  **Halo** (anillo, turquesa), **Cumbre** (triángulo, violeta) y **Astro**
  (estrella, fucsia).
- En tu turno juegas una carta del mismo color, número o símbolo que la de la
  mesa, o un comodín. Si no puedes (o no quieres), robas una; si te sirve,
  puedes jugarla ya.
- **Pausa** salta al siguiente; **Remolino** cambia el sentido (con dos
  jugadores es como una Pausa); **Carga +2** hace robar 2 al siguiente, que
  pierde su turno. **Camaleón** cambia el color; **Camaleón +4** además hace
  robar 4, y solo se puede jugar sin cartas del color de la mesa: si se juega
  de farol, el siguiente puede desafiarlo.
- Al quedarte con una carta pulsa **¡Última!**. Si no lo haces y alguien te
  pilla antes de que juegue el siguiente, robas 2. Tú también puedes pillar a
  un bot despistado con **¡Pillado!**.
- Gana la ronda quien se queda sin cartas. Opciones: jugar a puntos hasta una
  meta, sin desafío del +4, y las opciones de la casa de acumular +2 y +4
  (desactivadas por defecto).

## Cuentas

Arriba a la derecha, **Entrar** abre la ventana para iniciar sesión o crear
una cuenta: solo hacen falta un nombre de usuario (de 3 a 16 letras sin
acento, números, guion o guion bajo) y una contraseña de al menos 8
caracteres. No se pide correo, así que una contraseña olvidada no se puede
recuperar.

Con la sesión iniciada juegas con el nombre de tu cuenta y la sesión dura 30
días en ese navegador, hasta que pulses **Salir**. Al pulsar tu nombre se abre
tu perfil, con las estadísticas del poker: manos jugadas y ganadas, mayor bote,
mejor mano enseñada y partidas ganadas, en total y según el nivel de los rivales.

**Saldo**: cada cuenta tiene un saldo de fichas virtuales, que se ve junto a tu
nombre y empieza en 10.000. Poker y blackjack usan el mismo saldo: para jugar
eliges cuántas fichas llevas a la mesa, y lo que ganas o pierdes en cada mano o
ronda cambia el saldo al terminarla. Las fichas sentadas en una mesa no se
pueden llevar a otra a la vez. Si empiezas otra partida con una mano o ronda a
medias, pierdes lo que llevabas apostado en ella. Con menos de 100 fichas, la
pantalla de inicio te ofrece reponer el saldo a 10.000, gratis. Prisma no usa
fichas, y los invitados juegan con las fichas que elijan.

Las cuentas se guardan en `backend/data/mi-poker.db` (SQLite), que se crea
solo la primera vez y no se sube a git. Para usar otro archivo, define la
variable `MI_POKER_DB` antes de arrancar el servidor. Borrar ese archivo
borra todas las cuentas; para guardar una copia de seguridad basta con
copiarlo con el servidor parado.

## Sonido y ajustes

El audio empieza con tu primera interacción (un clic o una tecla): los
navegadores no dejan sonar nada antes. En la cabecera hay un botón para
silenciarlo todo y un menú **Ajustes** con el volumen de la música y el de los
efectos por separado. Ahí mismo se pueden desactivar las animaciones: cada
jugada se muestra entonces al instante (por defecto se sigue la preferencia de
movimiento reducido del sistema). Todo se guarda en el navegador y vale para
todos los juegos.

Los efectos y la música se generan por código, sin archivos. Si prefieres tu
propia música, guarda una pista como `frontend/src/assets/audio/music.mp3`
(o `.ogg`, `.wav`, `.m4a`) y vuelve a compilar: sustituye a la generada y se
repite con un fundido. Los detalles están en el `LEEME.md` de esa carpeta.

## Tests

Backend, desde `backend` con el venv activado:

```powershell
pytest
```

Cubren los tres motores, sus bots (con simulaciones que comprueban el orden de
los niveles), las partidas por WebSocket, las cuentas, el registro de juegos y
una pasada de seguridad: entrar en partidas ajenas, mensajes rotos o inventados
y cartas ocultas que nunca llegan al navegador. Usan bases de datos temporales:
nunca tocan la de `backend/data`.

Frontend (líneas de tiempo, cola de reproducción, menú, panel de opciones,
textos, sonidos y la parte de cuentas que no necesita navegador), desde
`frontend`:

```powershell
npm test
```

Los tests de las líneas de tiempo usan partidas reales grabadas del servidor.
Para volver a grabarlas, desde la raíz del proyecto:

```powershell
backend\.venv\Scripts\python.exe frontend\tools\record_fixtures.py     # poker
backend\.venv\Scripts\python.exe frontend\tools\record_blackjack.py    # blackjack
backend\.venv\Scripts\python.exe frontend\tools\record_prisma.py       # Prisma
```

## Por consola

Desde `backend` con el venv activado:

```powershell
python scripts\demo_hand.py            # una mano de poker al azar, con todo su registro
python scripts\simulate.py             # poker: bb/100 de cada nivel (medio minuto)
python scripts\simulate_blackjack.py   # blackjack: lo que gana o pierde cada nivel
python scripts\simulate_prisma.py      # Prisma: partidas ganadas por cada nivel
```

En todos el orden esperado es Experto > Difícil > Medio > Fácil (en el
blackjack, Difícil y Experto quedan casi iguales: los dos siguen la estrategia
básica y ninguno cuenta cartas).

## Bots

En todos los juegos los bots reciben solo lo que vería cualquier jugador (más
sus propias cartas) y "piensan" entre 0,8 y 2,5 segundos. Cambiar de nivel
cambia la estrategia, nunca la información.

| Nivel | Poker | Blackjack | Prisma |
|---|---|---|---|
| Fácil | Suelto y pasivo: juega casi todo y paga de más. | Decisiones a corazonadas. | Carta legal al azar; a menudo olvida «¡Última!». |
| Medio | Manos por su fuerza inicial y pot odds básicos. | Media estrategia básica. | Suelta primero lo que más vale; color: el que más tiene. |
| Difícil | Equity por Monte Carlo, posición y faroles ocasionales. | Estrategia básica completa. | Recuerda qué colores te faltan; guarda comodines y ataques. |
| Experto | Como Difícil, y se adapta a lo que haces. | Estrategia básica con ajustes por su mano. | Como Difícil, cierra mejor la mano y nunca se despista. |

## Estructura

```
backend/
  core/                piezas comunes en Python puro: baraja estándar, barajado
                       seguro, bots, opciones y la ficha de un juego
  games/
    registry.py        EL REGISTRO: la lista de juegos que ve el menú
    poker/             engine/ (motor), bots/, session.py (la partida en el
    blackjack/         servidor), protocol.py (mensajes), info.py (su ficha)
    prisma/            y tests/, igual en cada juego
  accounts/            cuentas en Python puro: contraseñas, sesiones,
                       estadísticas y saldo (SQLite)
  server/              FastAPI: partidas en memoria (partidas.py), WebSocket por
                       partida, API de juegos (games_api.py) y de cuentas
  data/                la base de datos de cuentas (se crea sola; fuera de git)
  scripts/             demos y simulaciones por consola
  tests/               tests de la plataforma (registro, partidas, seguridad…)
frontend/
  src/hub/             el menú principal, construido con GET /api/juegos
  src/shared/          lo común: cabecera, cuenta, ajustes, sonido, movimiento,
                       baraja clásica, panel de opciones, cola de reproducción,
                       conexión con las partidas y tokens de diseño
                       (styles/tokens.css: colores, tipografías y espacios)
  src/games/index.ts   el mapa de juegos: id → página e ícono
  src/games/poker/     la mesa de poker
  src/games/blackjack/ la mesa de blackjack
  src/games/prisma/    la mesa de Prisma y sus cartas en SVG
  src/assets/          la baraja clásica (CC0) y la carpeta de música opcional
  tools/               graba partidas reales para los tests y prepara la baraja
```

Cada juego describe sus mensajes en su `protocol.py`; las rutas de partidas
están en `backend/server/games_api.py` y las de cuentas en
`backend/server/accounts_api.py`.

### Añadir un juego

1. Escribir su carpeta en `backend/games/<juego>/`: motor en Python puro,
   bots, partida (`session.py`), mensajes (`protocol.py`) y tests.
2. Escribir su ficha en `info.py` y añadirla al registro
   (`backend/games/registry.py`). El menú la mostrará solo.
3. Escribir su página en `frontend/src/games/<juego>/` y añadir una línea
   (página e ícono) en `frontend/src/games/index.ts`.

El menú no se toca: se construye leyendo el registro.

## Cómo está hecho

### Partidas y seguridad

El servidor es la única autoridad: baraja con el generador seguro del sistema,
reparte, valida cada intención y paga. El navegador solo muestra el estado y
envía intenciones ("pedir carta", "jugar la carta 17").

- Para jugar, el navegador pide su partida por HTTP (`POST /api/partidas`) y se
  conecta a `/ws/{juego}/{partida_id}`. El id es largo, al azar y va ligado a
  su dueño: con el id de otro no se entra.
- Los mensajes se validan con modelos estrictos: un campo de más, un tipo
  equivocado o una acción inventada se rechazan sin tocar la partida.
- Nunca viajan las cartas ocultas: las de los rivales (hasta el showdown en el
  poker), la carta tapada del crupier, los mazos ni el zapato. Bots y
  navegador reciben la misma clase de vista, con solo lo público y lo suyo.
- Las peticiones y las conexiones desde otras webs se rechazan.

Pensado para jugar en local. Antes de publicarlo en internet haría falta, como
mínimo, servirlo por HTTPS y limitar cuántas cuentas se pueden crear.

### Cuentas y sesión

- **Contraseñas**: nunca se guardan. Se guarda un hash scrypt con una sal
  distinta por cuenta; el coste sigue la recomendación de OWASP.
- **Sesión**: al entrar, el servidor crea un token al azar y lo manda en una
  cookie `HttpOnly` y `SameSite=Lax`. En la base de datos solo queda el hash
  del token.
- **Quién soy**: lo decide el servidor al abrir la conexión con una partida. El
  nombre en la mesa lo pone el servidor.
- **Intentos fallidos**: el mensaje es el mismo exista o no el usuario, y tras
  cinco fallos en un minuto hay que esperar para volver a intentarlo.
- **Cerrar sesión** borra la sesión en el servidor y corta sus conexiones.
- **Saldo y estadísticas**: los apunta el servidor al terminar cada mano o
  ronda, antes de enviar el resultado; en pantalla el saldo no cambia hasta que
  la mesa ha terminado de mostrar cómo acabó.

### Cómo se reproduce una jugada

El servidor no envía sucesos sueltos: tras cada cambio envía la mesa completa,
con un registro de la mano o ronda que solo crece. Cada juego compara ese
registro con el anterior y lo convierte en pasos (repartir una carta, jugar,
robar, destapar…), que una cola común (`frontend/src/shared/timeline/`)
reproduce de uno en uno. Al vaciarse la cola, lo mostrado es exactamente el
estado del servidor, y solo entonces se activan los botones de acción.

### Cartas

- **Poker y blackjack**: la baraja clásica inglesa de Adrian Kennard, publicada
  como CC0 (dominio público) en https://www.me.uk/cards/, con figuras calcadas
  de una baraja Goodall & Son del siglo XIX. No lleva el nombre ni los dibujos
  de ninguna marca. Son dibujo propio el dorso, el adorno del as de picas y la
  cara sencilla de las cartas pequeñas. Para volver a preparar la baraja:
  `node frontend\tools\import_cards.mjs <carpeta con los SVG descargados>`.
- **Prisma**: cartas dibujadas por código en SVG (`frontend/src/games/prisma/`),
  de diseño propio: marco claro, campo del color del palo con una banda
  diagonal, la forma del palo de fondo, números rectos y símbolos propios para
  cada acción. El reverso es un prisma que abre la luz en los cuatro colores.

### Animaciones

Las cartas se mueven al estilo de Balatro, con nuestro propio dibujo: salen
volando del mazo (o del zapato), las tuyas se voltean en 3D al llegar y, en
reposo, flotan apenas. Solo se animan `transform` y `opacity`, y cada movimiento
dura menos de medio segundo. Con las animaciones desactivadas en **Ajustes**
(o si el sistema pide movimiento reducido) no se mueve nada.

### Sonido

El juego no trae ningún archivo de audio: cada efecto y la música se sintetizan
en el momento con la Web Audio API (`frontend/src/shared/audio/`); la única
excepción es la pista opcional que puedes poner tú. Con la pestaña oculta no
suena nada.

## Créditos

- Caras de la baraja clásica: Adrian Kennard, CC0 (dominio público),
  https://www.me.uk/cards/. Detalles en `frontend/src/assets/cards/LEEME.md`.
- Todo lo demás (nombre, emblemas, íconos, cartas de Prisma, dorsos, mesas,
  avatares, textos, efectos de sonido y música) es propio de este proyecto.
