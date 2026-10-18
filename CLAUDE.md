# Proyecto: plataforma de juegos de cartas en el navegador contra bots

Empezó como un juego de poker para navegador y en la etapa 4 se convierte en
una pequeña plataforma de juegos de cartas con un menú principal: poker,
blackjack y un juego de descarte. Inspirado en la idea general de los sitios
de juego social con fichas virtuales, pero con nombre, diseño y textos 100%
originales (no copiar marca, assets ni textos de ningún sitio existente).

## ESTADO ACTUAL
- Etapas 1, 2, 3 y 4 completas. La etapa 4 (plataforma de juegos: menú
  principal, el poker de siempre, blackjack y el juego de descarte "Prisma")
  se aprobó el 2026-10-17 y se trabajó de seguido, sin parar a pedir
  aprobación entre hitos, como pedí; se cerró el 2026-10-17.
- ETAPA 5 EN CURSO (aprobada el 2026-10-17): jugar online con amigos en salas
  privadas, cuentas obligatorias y fichas diarias. Pedí trabajarla de seguido,
  sin parar entre hitos: al cerrar cada hito se corren TODOS los tests y se
  hace su commit.
- El juego de descarte se llama Prisma: lo decidí el 2026-10-17 (probé a
  llamarlo ONE y volví a Prisma).

## Reglas innegociables
- NO se usa dinero real en ninguna parte. Las fichas son virtuales y no
  tienen valor fuera del juego: no se compran, no se venden y no se canjean
  por nada. Se guardan como saldo de la cuenta (decidido el 2026-10-10).
- El aviso "Solo para entretenimiento. Sin dinero real." NO se muestra en la
  interfaz, tampoco en el menú: lo quité el 2026-10-10 y lo confirmé el
  2026-10-17. La regla de arriba no cambia. (En el README sí se mantiene.)
- REGLA DE ORO de la etapa 4: no romper lo que ya funciona. Los tests del
  poker deben pasar en cada hito. Los archivos se mueven en un hito propio,
  con los tests antes y después.

## Fuera del alcance (NO implementar sin que lo pida)
- Cambios en la lógica del motor de poker, sus bots o sus reglas. En la etapa
  4 se mueven de carpeta y cambian sus `import`, nada más.
- Recuperación de contraseña, verificación por correo, entrar con un enlace
  enviado al correo e inicio de sesión con terceros (Google y similares): no
  hay servicio de correo ni despliegue. (El correo de la cuenta es opcional y
  solo sirve para entrar con él en vez de con el nombre de usuario.)
- Minijuegos, bono diario y recompensas diarias: descartados el 2026-10-17
  (no los quiero).
- Salas públicas con desconocidos (emparejamiento al azar), lobby general y
  chat: las salas son privadas, con código o enlace.
- Estadísticas de blackjack y del juego de descarte: el perfil sigue siendo
  del poker.
- Despliegue en un servidor público. Para jugar con amigos de fuera de casa
  se usa un túnel https temporal que abro yo (ver el README).

## Plataforma (etapa 4)
- Menú principal (hub) en `/`, y cada juego en su ruta: `/poker`,
  `/blackjack`, `/prisma`. Navegación con React Router.
- Registro de juegos en el backend (`backend/games/registry.py`): cada juego
  tiene una ficha con id, nombre, descripción, mínimo y máximo de bots,
  esquema de opciones configurables y la función que crea la partida.
  `GET /api/juegos` devuelve la lista y el menú se construye leyéndola.
  Añadir un juego = escribir su módulo, añadir su ficha al registro y su
  página y su ícono al mapa de juegos del frontend (`frontend/src/games/index.ts`),
  sin tocar el menú.
- El menú tiene tarjetas grandes con nombre, una línea de descripción, ícono
  SVG propio dibujado por código y rango de jugadores, y tarjetas
  "Próximamente" deshabilitadas (salas con amigos), que también vienen del
  registro.
- Partidas: en memoria, una por identidad (cuenta o invitado) y por juego.
  `POST /api/partidas` da el id de la partida (largo, al azar y ligado a esa
  identidad) y el WebSocket es `/ws/{juego}/{partida_id}`. El servidor
  rechaza a quien no es su dueño.
- Volver al menú con una partida en curso pide confirmación. La partida
  queda en pausa en el servidor y el menú ofrece "Continuar" (decidido el
  2026-10-17). En el futuro online, salir de una partida con otras personas
  será abandonarla, con sus consecuencias.
- Saldo compartido (decidido el 2026-10-17): con cuenta, poker y blackjack
  usan el mismo saldo. Las fichas sentadas en una mesa no se pueden llevar a
  otra a la vez. Los invitados juegan con fichas gratis en cada mesa. El
  juego de descarte no usa fichas.
- Todo con el estilo de casino del poker. Colores, tipografías y espaciados
  centralizados en tokens (`frontend/src/shared/styles/tokens.css`). Responsive,
  usable con teclado y respetando `prefers-reduced-motion`.
- Bots de todos los juegos: misma idea que en el poker. Reciben SOLO la
  información pública más la suya propia, y "piensan" entre 0.8 y 2.5
  segundos.

### Estructura
- Backend:
  - `core/`: piezas compartidas en Python puro (carta y mazo estándar de 52,
    barajado seguro, ritmo e identidad de los bots, esquema de opciones y
    ficha del registro).
  - `games/<juego>/`: `engine/` (Python puro, sin FastAPI), `bots/`,
    `session.py` (la partida en el servidor), `protocol.py` (mensajes),
    `info.py` (su ficha) y `tests/`.
  - `server/`: FastAPI. Partidas genéricas, WebSocket por partida, API de
    juegos y de cuentas.
- Frontend:
  - `src/hub/`: el menú.
  - `src/shared/`: lo común (cabecera, cuenta, ajustes, sonido, movimiento,
    baraja clásica, panel de opciones, tokens).
  - `src/games/<juego>/`: la interfaz de cada juego.

## Reglas del poker
- Texas Hold'em No-Limit, de 2 a 6 jugadores (1 humano + 1 a 5 bots).
- Blinds (pequeña y grande), botón de dealer que rota cada mano.
- Fases: preflop, flop, turn, river y showdown.
- Acciones: fold, check, call, raise (con monto) y all-in.
- Raise mínimo según las reglas oficiales. Acciones ilegales se rechazan.
- Side pots correctos cuando hay all-ins de distinto tamaño.
- Empates: el bote se divide; resto indivisible a la posición según reglas.
- Jugadores sin fichas quedan eliminados. Si el humano se queda sin fichas,
  ofrecer "Reiniciar partida" (con fichas de su saldo).
- Configurable antes de empezar: número de bots, dificultad, fichas
  iniciales y blinds.

### Bots del poker
- Todos comparten la misma interfaz: una función `decide` que recibe SOLO la
  vista pública de la mesa más sus propias cartas, y devuelve fold, call o
  raise con monto.
- Nunca ven cartas ajenas ni el mazo. Cambiar de dificultad es cambiar la
  estrategia, nunca dar o quitar información.
- Niveles:
  - Fácil: pasivo y suelto, juega demasiadas manos, llama mucho, casi no
    hace farol y comete errores obvios.
  - Medio: decide según la fuerza de la mano inicial, usa pot odds básicos y
    respeta las apuestas grandes.
  - Difícil: estima su equity con simulación Monte Carlo (unos pocos miles
    de simulaciones), usa pot odds, varía el tamaño de sus apuestas, hace
    faroles ocasionales y considera la posición.
  - Experto: como Difícil, con rangos más ajustados, agresión selectiva,
    faroles con frecuencia calculada y algo de aleatoriedad.
- En bot contra bot: Experto gana más que Difícil, Difícil más que Medio y
  Medio más que Fácil (`backend/scripts/simulate.py`).
- Cada bot tiene nombre y personalidad originales (por ejemplo "tight
  agresivo" o "suelto pasivo") que modifican levemente sus decisiones.

## Blackjack (etapa 4)
- 1 humano contra el crupier, con 0 a 4 asientos de bots opcionales.
- Zapato de 6 mazos con barajado seguro. La carta de corte va hacia el 75%:
  cuando sale, se termina la ronda y se rebaraja antes de la siguiente.
- Apuestas mínima y máxima configurables, de 10 en 10, para que el 3 a 2, el
  seguro y la rendición den siempre fichas enteras.
- Blackjack natural paga 3 a 2. Empate (push) devuelve la apuesta.
- El crupier se planta en 17 blando por defecto (opción: pide en 17 blando).
- Acciones:
  - Pedir carta y plantarse. Con 21, la mano se planta sola.
  - Doblar con las dos primeras cartas, también después de dividir.
  - Dividir pares del mismo valor, hasta 4 manos. Los ases divididos reciben
    una sola carta y no se vuelven a dividir; As y figura después de dividir
    cuenta 21, no blackjack.
  - Seguro cuando el crupier enseña un As: cuesta la mitad de la apuesta y
    paga 2 a 1 si el crupier tiene blackjack.
  - Rendición tardía: opcional, desactivada por defecto.
- El crupier mira si tiene blackjack cuando enseña un As o un 10.
- La carta oculta del crupier NUNCA se envía al cliente hasta que se revela.
  El zapato, nunca.
- Bots (nadie cuenta cartas):
  - Fácil: decisiones erráticas.
  - Medio: una versión incompleta de la estrategia básica.
  - Difícil: la estrategia básica correcta para las reglas de la mesa.
  - Experto: como Difícil, más ajustes según las cartas de su propia mano.
  - Apuestan cantidades fijas y se levantan cuando se quedan sin fichas.
- Con cuenta: las fichas se llevan a la mesa desde el saldo, cada ronda
  cambia el saldo al terminar y dejar una ronda a medias cuesta lo apostado.
- Tests: valor de manos con ases blandos y duros, división de ases, doblar,
  seguro, pagos de cada resultado, rebarajado del zapato y simulaciones
  largas en las que el total de fichas (jugadores más la banca) se conserva.

## Juego de descarte "Prisma" (etapa 4)
Es el UNO clásico original, con sus mismas reglas, pero sin su nombre, su
logo ni su vocabulario: ninguna palabra, logo, eslogan ni asset del juego
clásico. Su nombre es Prisma (decidido el 2026-10-17).

### Identidad propia
- Cuatro palos con nombre, forma y color propios. Cada forma es distinta, lo
  que ayuda con el daltonismo, y se evita la paleta clásica rojo, amarillo,
  verde y azul:
  - Panal: hexágono, naranja cobre.
  - Halo: anillo, turquesa.
  - Cumbre: triángulo, violeta.
  - Astro: estrella de cuatro puntas, fucsia.
- Acciones:
  - Pausa (salto).
  - Remolino (cambio de sentido).
  - Carga +2 (el siguiente roba 2).
  - Camaleón (comodín de color).
  - Camaleón +4 (comodín que hace robar 4).
  - El botón para avisar de la última carta se llama "¡Última!".
- Cartas dibujadas por código en SVG, con diseño propio (tipografía,
  esquinas, símbolos y reverso): sin óvalos centrales ni composiciones que
  imiten las cartas conocidas.

### Reglas (las del clásico)
- **Mazo de 108 cartas.** Por palo: un 0, dos de cada número del 1 al 9 y dos
  de cada acción (Pausa, Remolino, Carga +2). Además, 4 Camaleón y
  4 Camaleón +4.
- **Reparto:** de 2 a 6 jugadores (1 humano + 1 a 5 bots), 7 cartas a cada
  uno. Empieza el jugador a la izquierda del que reparte, y el que reparte
  rota en cada ronda.
- **Carta inicial:**
  - Si es un Camaleón +4, se devuelve al mazo y se saca otra.
  - Si es de acción, se aplica al primero: Camaleón, el primero elige color;
    Pausa, se salta al primero; Remolino, empieza el que reparte y el
    sentido se invierte; Carga +2, el primero roba 2 y pierde el turno.
- **Turno:**
  - Se juega una carta del mismo color, del mismo número o del mismo símbolo,
    o un comodín.
  - En lugar de jugar se puede robar una carta, aunque se tenga jugada, como
    en el clásico. Si la robada se puede jugar, se puede soltar en ese mismo
    turno; si no, pasa el turno.
- **Efectos de las acciones:**
  - Pausa salta al siguiente.
  - Remolino invierte el sentido; con 2 jugadores actúa como Pausa.
  - Carga +2: el siguiente roba 2 y pierde el turno.
  - Camaleón: quien lo juega elige el color.
  - Camaleón +4: quien lo juega elige el color y el siguiente roba 4 y
    pierde el turno. Solo se puede jugar sin cartas del color actual.
- **Desafío del +4:** es una opción y viene activada, como en el clásico.
  - Activada, el +4 se puede jugar de farol y el siguiente puede desafiarlo.
    Si era ilegal, quien lo jugó roba 4 y el desafiante juega normal; si era
    legal, el desafiante roba 6 y pierde el turno.
  - Solo se muestra el resultado del desafío, nunca la mano.
  - Desactivada, el servidor no deja jugar el +4 si tienes el color actual.
- **"¡Última!":**
  - Al quedarte con una carta hay que pulsar "¡Última!". Vale pulsarlo al
    jugar la penúltima o justo después, hasta que actúe el siguiente jugador.
  - Si no lo haces y un rival te pilla antes de eso, robas 2.
  - El humano tiene un botón para pillar a los bots; los bots pillan con más
    probabilidad cuanto más nivel tienen.
- **Mazo agotado:** si se acaba el mazo de robo, se rebaraja el descarte
  dejando la carta de arriba.
- **Final de la ronda:** gana quien se queda sin cartas. Si su última carta
  hace robar, el siguiente roba igualmente.
- **Puntuación** (opcional, desactivada por defecto): el ganador suma las
  cartas que les quedan a los demás (números, su valor; acciones, 20;
  comodines, 50) hasta una meta configurable (500 por defecto).
- **Opciones de la casa**, desactivadas por defecto: acumular +2 sobre +2 y
  +4 sobre +4.

### Bots
Solo ven el descarte, el tamaño de las manos de todos y el historial de
jugadas.
- Fácil: juega una carta legal al azar y a menudo olvida decir "¡Última!".
- Medio: suelta primero las cartas de más valor, elige como color el que más
  tiene en la mano y casi siempre dice "¡Última!".
- Difícil: recuerda qué colores no tenían los rivales (quien robó en un color
  probablemente no lo tiene), guarda los comodines para el final y usa las
  cartas de ataque contra el rival con menos cartas.
- Experto: como Difícil, con mejor gestión de la mano final, sin olvidar
  nunca "¡Última!" y con algo de aleatoriedad.

### Tests
- Composición exacta del mazo.
- Jugadas legales e ilegales y el +4 restringido.
- Remolino con 2 jugadores.
- Rebarajado.
- Castigo por no decir "¡Última!".
- Puntuación.
- Simulación de miles de partidas bot contra bot: Experto gana más que
  Difícil, Difícil más que Medio y Medio más que Fácil, y siempre hay 108
  cartas en juego.

## Reglas técnicas
- El SERVIDOR es la única autoridad: baraja, reparte, valida y paga. El
  cliente solo muestra el estado y envía intenciones ("fold", "raise 400").
- Los bots viven en el servidor y juegan como un jugador más.
- Nunca enviar al cliente cartas ocultas: las de otros jugadores (hasta el
  showdown en el poker), la carta tapada del crupier, los mazos ni el zapato.
- Barajar con `secrets` o `random.SystemRandom` (nunca `random` normal). Solo
  los tests y las simulaciones pueden pasar un mazo preparado o un generador
  con semilla, para que el resultado se repita.
- Los motores de los juegos son Python puro, separados de FastAPI, para
  poder probarlos solo con pytest. Igual la lógica de cuentas.
- El servidor envía el estado completo tras cada cambio, con un registro de
  la mano o la ronda (`events`) que solo crece.
- Desde la etapa 5 hace falta cuenta para jugar a todo. El identificador de
  invitado (`frontend/src/shared/guest.ts`) queda solo para desarrollo y tests:
  el servidor real exige cuenta (`create_app(require_account=True)`, lo que
  viene por defecto).
- Todo lo de la cuenta en el frontend va aislado en
  `frontend/src/shared/account.ts`; las preferencias, en
  `frontend/src/shared/settings.ts`.

## Stack
- Backend: Python 3.12 o superior, FastAPI y WebSockets. Cuentas en SQLite
  (módulo `sqlite3` de Python, sin dependencias nuevas).
- Frontend: React + TypeScript + Vite + Tailwind + React Router.
- Pruebas: pytest (backend) y Vitest (lógica pura del frontend: línea de
  tiempo, cola, preferencias, sonidos, cuenta y menú).

## Diseño visual
Referencias que di (se toma la idea, nunca la marca ni los assets):
- Disposición de la mesa de poker y del panel inferior: como en las mesas de
  poker social (placas oscuras con avatar, bote sobre las cartas
  comunitarias, registro a la izquierda y botones grandes a la derecha).
- Las cartas de cada jugador, también las de los bots, van ENCIMA de su
  placa, enteras y sobre el nombre. Nunca metidas por detrás de la placa ni
  tapadas por ella (corregido el 2026-10-10).
- Baraja de poker y blackjack: el diseño clásico de toda la vida, como las
  cartas Bicycle. Como su nombre, su as de picas y su dorso son marca
  registrada, se usa la baraja clásica inglesa de Adrian Kennard, publicada
  como CC0 (dominio público), con figuras calcadas de una baraja Goodall del
  siglo XIX. Es la única excepción que aprobé al "diseño 100% original": ver
  `frontend/src/assets/cards/LEEME.md`. El dorso y el adorno del as de picas
  son propios.
- Probé unas figuras dibujadas a mano que se movían y NO me gustaron: no
  volver a ellas. Las figuras de las cartas NO se animan.
- Colores: los de una web de casino que llame la atención (negro y granate,
  oro, tapete esmeralda con ribete dorado, botones rojo, verde y oro en tonos
  tenues: los vivos me resultaban demasiado brillantes).

## Animaciones
- Las cartas se mueven con el estilo de Balatro, pero SIN su estética
  pixelada: salen del mazo con fluidez, flotan suavemente mientras están
  quietas, se inclinan al pasar el ratón, hacen un efecto al seleccionarlas
  (se levantan con un rebote) y entran en la mesa con giro y rebote.
  Seleccionar una carta es un adorno; no cambia el juego.
- Reparto: las cartas salen del mazo (junto al dealer) y vuelan una a una
  hacia cada jugador en orden de reparto, con un pequeño retardo entre
  cartas. El reparto del poker me gusta como está: NO cambiarlo.
- Mis cartas se voltean con un giro 3D al llegar; las de los bots quedan boca
  abajo y solo se voltean en el showdown.
- Flop, turn y river: las cartas comunitarias aparecen de una en una con
  deslizamiento y giro.
- Fichas: van directas del jugador al bote al apostar, y del bote al ganador
  al terminar la mano. La apuesta de la ronda sigue visible como cifra junto
  a cada jugador.
- Fold: las cartas del jugador se deslizan hacia el centro y se desvanecen.
- Resaltar de forma suave al jugador en turno y al ganador de la mano. Los
  resaltes son halos ya dibujados a los que solo se les anima la opacidad.
- Solo se animan `transform` y `opacity` (60 fps), con curvas suaves y
  duraciones de 200 a 500 ms por movimiento. Única excepción, continua, lenta
  y muy leve: la flotación en reposo, al mínimo.
- Sin librerías de animación: API de animaciones del navegador y CSS.
- Respetar `prefers-reduced-motion` y ofrecer una opción para desactivar las
  animaciones.

### Línea de tiempo (cómo se reproduce una mano)
- El cliente compara el registro de la mano (`events`) con el anterior y lo
  convierte en pasos que se reproducen de uno en uno, en orden, sin pisarse.
- El reparto del poker no es un evento del servidor: se deduce en el cliente
  con el botón y los jugadores con fichas, en el mismo orden que usa el motor.
- Al vaciarse la cola, lo mostrado es exactamente el estado del servidor, y
  solo entonces se activan los botones de acción.
- Si la cola se atrasa, se acelera. Con la pestaña oculta, al reconectar o
  con las animaciones desactivadas, se salta al estado final sin animar.

## Sonido
- Efectos para: repartir carta, voltear carta, check, apostar o igualar
  fichas, subir, fold, all-in, ganar el bote, y un aviso suave cuando es mi
  turno. Cortos, discretos y sincronizados con su animación.
- Música de fondo ambiental, tranquila (tipo lo-fi o ambient suave), en bucle
  sin cortes perceptibles y a volumen bajo por defecto. Empieza solo después
  de la primera interacción del usuario.
- Panel pequeño con volumen de música y de efectos por separado, y un botón
  de silenciar todo. Preferencias (animaciones, volúmenes, silencio) en
  localStorage.
- Nada con derechos de autor. Efectos y música se generan por código con la
  Web Audio API: la aplicación funciona sin ningún archivo de audio.
- Opcional: si existe `frontend/src/assets/audio/music.mp3` (o `.ogg`), se usa
  esa pista en lugar de la música generada, con fundido en el punto de bucle.
  Debe ser CC0 de verdad y la descargo yo; si falta, no hay ningún error.

## Cuentas y sesión
- Hace falta cuenta para jugar a todo, contra bots y con amigos (decidido el
  2026-10-17; antes era opcional). Crearla tiene que ser lo más fácil posible:
  nombre de usuario y contraseña, y nada más.
- Se entra con el nombre de usuario o con el correo, y la contraseña. El correo
  es opcional al crear la cuenta, no se verifica y nadie más lo ve.
- El nombre de usuario es el nombre en la mesa de todos los juegos.
- Las contraseñas se guardan solo como hash con sal (scrypt), nunca en claro.
  No se escriben en registros ni se devuelven al cliente.
- La sesión es un token aleatorio en una cookie HttpOnly. En la base de datos
  se guarda solo el hash del token.
- Un inicio de sesión fallido no dice si el usuario existe (también tarda lo
  mismo exista o no), y los intentos repetidos se frenan.
- Base de datos SQLite en `backend/data/mi-poker.db`, fuera de git.
- Con sesión iniciada, el nombre en la mesa es el de la cuenta: lo pone el
  servidor, no el cliente.

## Saldo (decidido el 2026-10-10; compartido entre juegos desde la etapa 4)
- Cada cuenta empieza con 10.000 fichas. Para jugar se lleva a la mesa una
  parte, como mucho lo que no esté ya sentado en otra mesa, y lo ganado o
  perdido en cada mano o ronda cambia el saldo al terminarla. El saldo
  incluye las fichas que el jugador tiene en las mesas.
- Fichas diarias (decidido el 2026-10-17; sustituye a la recarga gratis):
  cada vez que entras, si no tienes ya unas pendientes, ganas 10.000 fichas
  que llegan 24 horas después (llegan aunque no estés conectado). Si un día no
  entras, al siguiente no llega nada. Si pierdes todas tus fichas, toca
  esperar a la próxima entrega. Las fichas se suman al saldo.
- Dejar una mano o ronda a medias (empezar otra partida de ese juego antes de
  que termine) cuesta lo ya apostado en ella, como si el jugador se retirase.
- El saldo lo lleva el servidor. El cliente solo lo muestra, y al ritmo de la
  mesa: no cambia en pantalla antes de que se vea cómo acabó la mano.

## Perfil y estadísticas (solo poker)
- Las apunta el servidor al terminar cada mano; el cliente no las envía.
  Quedan guardadas antes de que el jugador vea el resultado.
- Solo cuentan las manos terminadas; una mano dejada a medias no cuenta.
- Se llevan aparte por nivel de los rivales; el perfil muestra el total y el
  desglose.
- Qué se guarda: manos jugadas; manos ganadas (cobrar algo de algún bote); lo
  máximo cobrado en una mano; la mejor mano enseñada en un showdown; partidas
  jugadas (cuenta al terminar su primera mano) y partidas ganadas (dejar sin
  fichas a todos los rivales).
- Si falla el guardado, la mano sigue: nunca se rompe una partida por las
  estadísticas.

## Cómo trabajar
- Cada etapa se divide en hitos. Por defecto, detenerse al final de cada hito
  y esperar mi aprobación (en la etapa 4 pedí no parar: ver arriba).
- Al cerrar cada hito: ejecutar TODOS los tests (backend y frontend), indicar
  cómo correr el proyecto y qué debería verse en pantalla.
- Soy principiante-intermedio en Python: comentar el código en español y, al
  cerrar cada hito, explicarme lo hecho con un ejemplo corto.
- Un commit por hito.
- El último hito de cada etapa es un repaso final y la puesta al día del
  README.
- Si hay una decisión de diseño con varias opciones, preguntarme (salvo en la
  etapa 4, donde decidí dejar que se elija la opción recomendada y se anote
  aquí).

## Etapa 5: online con amigos (salas privadas)
Decisiones del 2026-10-17:
- Salas privadas en los tres juegos. Quien crea la sala (el anfitrión) elige
  el juego y sus opciones y recibe un código corto (por ejemplo `K7P2QX`) y un
  enlace (`/sala/K7P2QX`). Los demás entran con el código o abriendo el
  enlace. Al encontrarse la sala hay una animación ("Buscando la sala…" y
  "¡Partida encontrada!").
- Sala de espera en tiempo real: quién está, el anfitrión, el código y el
  enlace para copiar. El anfitrión empieza la partida cuando hay al menos dos
  personas; puede rellenar los asientos libres con bots.
- Poker y blackjack se juegan con el saldo de cada cuenta: lo que se gana o se
  pierde cambia el saldo, también entre personas. Prisma no usa fichas.
- Cada uno recibe solo su vista: nunca las cartas de los demás.
- Tiempo por decisión: 30 segundos. Si se acaba, el servidor juega por ti lo
  más prudente (poker: pasar o retirarse; blackjack: plantarse, sin seguro, y
  sin apuesta no juegas la ronda; Prisma: robar y pasar).
- Desconectarse no es salir: el asiento se guarda y se puede volver con el
  mismo enlace. Salir de la sala con la partida empezada es abandonarla, con
  sus consecuencias: en el poker se pierde lo apostado en la mano (te
  retiras) y en el blackjack la ronda se juega sola (te plantas); en Prisma
  un bot ocupa tu sitio. No se puede volver a esa partida.
- Conexión: el servidor puede escuchar en la red de casa (misma WiFi) y, para
  amigos de fuera, se usa un túnel https temporal. El enlace de la sala usa
  siempre la dirección por la que se ha entrado.
- Los códigos son difíciles de adivinar y los intentos de entrar con códigos
  que no existen se frenan.

### Hitos de la etapa 5
1. Cuentas obligatorias y más fáciles (completado): sin cuenta no se juega
   (cualquier dirección enseña la pantalla de entrada); crear cuenta con
   usuario y contraseña (correo opcional, sin repetir la contraseña y con
   botón para verla); entrar con usuario o correo.
2. Fichas diarias (completado): 10.000 fichas 24 h después de entrar, si no
   hay unas pendientes; fuera la recarga gratis; el menú, el perfil y la
   pantalla de inicio de cada mesa dicen cuándo llegan las próximas. Mirar el
   saldo cuenta como entrar (`AccountStore.wallet`).
3. Salas en el servidor: crear, unirse por código o enlace, sala de espera en
   tiempo real, anfitrión, salir y volver.
4. Partidas con varias personas en los tres juegos: una vista por persona,
   tiempo por decisión, desconexiones y abandonos, saldo de cada cuenta.
5. Interfaz: crear sala y unirse, animación de "¡Partida encontrada!", sala de
   espera y las mesas de los tres juegos con varias personas.
6. Red local, túnel y repaso: pasada de seguridad, pruebas con dos
   navegadores, README y este archivo al día.

## Hitos de la etapa 4
0. Plan (completado el 2026-10-17).
1. Refactor modular y registro de juegos (completado): el poker se mueve a
   `games/poker/`, aparecen `core/`, las partidas genéricas, el WebSocket
   `/ws/{juego}/{partida_id}` y `GET /api/juegos`. El poker sigue igual y sus
   320 tests pasan con los mismos nombres.
2. Menú principal conectado al registro, con el poker accesible desde él
   (completado): cabecera común con botón Menú, cuenta y ajustes para toda la
   plataforma, confirmación al salir de una partida, "Continuar partida" en
   el menú, tokens de diseño y el servidor devuelve la web en /poker y demás
   rutas.
3. Blackjack: motor y tests, luego bots, luego interfaz (completado). Motor
   con zapato y carta de corte, seguro, doblar, dividir y rendición; bots con
   la estrategia básica en tablas (orden de niveles comprobado jugando las
   mismas rondas); mesa de media luna con el crupier, el zapato y las reglas
   impresas en el tapete. La cola de reproducción paso a paso y el panel de
   opciones construido con el esquema del servidor pasan a ser comunes.
4. Prisma: motor y tests, luego bots con simulación, luego interfaz y arte
   SVG original (completado). Motor con las reglas del clásico; bots con
   memoria de colores (Medio suelta primero las cartas que más valen, también
   los comodines); en miles de partidas a cuatro Experto > Difícil > Medio >
   Fácil; mesa con mazo, descarte, color en juego y sentido, mi mano en
   grande, selector de color, desafío, "¡Última!" y "¡Pillado!".
5. Revisión de conjunto (completado): pasada de seguridad en los tres juegos
   (partidas ajenas, otras webs, mensajes rotos o inventados, el mazo nunca
   viaja), títulos de pestaña, registro y escalado de mesa comunes, todo
   comprobado en Chrome en ordenador y en móvil, y README al día. El poker
   conserva su pantalla de inicio (con las ciegas por parejas), hecha con las
   mismas piezas comunes que el panel de opciones de los demás juegos.

### Decisiones tomadas durante la etapa 4
- Blackjack: el humano se sienta en medio de la mesa; los bots deciden el
  seguro en el momento en que se ofrece (sin pausa), y su orden de niveles se
  mide jugando todos las mismas rondas.
- Prisma: como en el clásico, se puede robar aunque se tenga jugada; el
  desafío del +4 solo enseña el resultado, nunca la mano; con "acumular +4"
  activado no hay desafío. El nivel Medio suelta primero las cartas de más
  valor, comodines incluidos (así se separa de Difícil, que los guarda).
- Los bots de Prisma, mientras "piensan", dejan al humano decir "¡Última!" o
  pillar a quien no lo dijo; justo antes de jugar, los demás bots pueden
  pillar al despistado, cada uno con la probabilidad de su nivel.

## Historial de etapas
### Etapa 1: motor, bots, servidor e interfaz simple (completa)
1. Motor de poker + tests: las 10 categorías de mano, empates por kickers,
   side pots con 3 all-ins distintos y simulaciones de manos completas
   verificando que la suma total de fichas se conserva siempre.
2. Bots + simulación: miles de manos bot contra bot con una tabla de
   resultados por nivel.
3. Servidor FastAPI + WebSocket y una interfaz simple para jugar una partida
   completa contra los bots, con panel de configuración.

### Etapa 2: pulido visual y sonoro (completa el 2026-10-10)
Solo cambió el frontend. Única excepción en el backend, aprobada el
2026-10-10: se corrigieron tests que fallaban al azar.
1. Mesa, línea de tiempo y audio (el audio se adelantó a petición mía).
2. Animaciones al estilo Balatro, fichas, fold, resaltes y movimiento
   reducido.
3. Baraja clásica y colores de casino.
4. Cierre: repaso y README. Se corrigió un fallo de audio: un volumen
   cambiado en silencio no se aplicaba hasta el siguiente sonido.

### Etapa 3: cuentas y login (completa el 2026-10-10)
1. Cuentas y login: registro, inicio y cierre de sesión; partida de invitado
   y de cuenta independientes.
2. Perfil y estadísticas, en total y por nivel de los rivales.
3. Saldo: fichas guardadas en la cuenta, llevadas a la mesa y actualizadas
   con cada mano; recarga gratis.
4. Cierre: repaso y README. Se igualó lo que tarda el primer intento de
   inicio de sesión, exista o no la cuenta.

## Visión futura (solo referencia, NO implementar todavía)
- Publicar la plataforma en un servidor (HTTPS, límites de cuentas) para
  jugar con gente de todo el mundo sin túnel.
- Los minijuegos y las recompensas diarias quedan descartados (2026-10-17).
