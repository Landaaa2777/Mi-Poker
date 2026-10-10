# Proyecto: poker Texas Hold'em en el navegador contra bots

Juego de poker para navegador, inspirado en la idea general de los sitios de
poker social con fichas virtuales, pero con nombre, diseño y textos 100%
originales (no copiar marca, assets ni textos de ningún sitio existente).

## ETAPA ACTUAL: ETAPA 2 (pulido visual y sonoro)
Objetivo: que la mesa se sienta fluida y agradable, con animaciones, efectos
de sonido y música de fondo relajante.

La ETAPA 1 (motor, bots, servidor e interfaz simple) está completa: una
partida completa de Texas Hold'em No-Limit en el navegador, un humano contra
1 a 5 bots, con dificultad de bots ajustable.

Dentro del alcance:
- Pantalla de inicio y mesa con diseño propio: placas con avatar, cartas y
  fichas dibujadas con CSS/SVG y marca del juego en el tapete.
- Animaciones de reparto, cartas, fichas, fold, turno y ganador.
- Efectos de sonido, música de fondo y panel de controles de audio.

Referencias que he dado (se toma la idea, nunca la marca ni los assets):
- Disposición de la mesa y del panel inferior: como en las mesas de poker
  social (placas oscuras con avatar, bote sobre las cartas comunitarias,
  registro a la izquierda y botones grandes a la derecha).
- Movimiento de las cartas: como en Balatro, pero SIN su estética pixelada.
- Baraja: el diseño clásico de toda la vida, como las cartas Bicycle. Como su
  nombre, su as de picas y su dorso son marca registrada, se usa la baraja
  clásica inglesa de Adrian Kennard, publicada como CC0 (dominio público),
  con figuras calcadas de una baraja Goodall del siglo XIX. Es la única
  excepción que aprobé al "diseño 100% original": ver
  `frontend/src/assets/cards/LEEME.md`. El dorso y el adorno del as de picas
  son propios.
- Colores: los de una web de casino que llame la atención (negro y granate,
  oro, tapete esmeralda con ribete dorado, botones rojo, verde y oro).

Fuera del alcance (NO implementar):
- Cualquier cambio en el motor de poker, los bots, las reglas o el protocolo
  del servidor. En la etapa 2 SOLO cambia el frontend, y los tests del
  backend deben seguir pasando. Únicas excepciones, que aprobé el 2026-10-10:
  se corrigieron tests que fallaban al azar. En `backend/tests/test_server.py`
  daban por hecho que al humano le tocaba jugar antes de que un bot se
  retirase; en `backend/tests/test_bots.py`, el test de adaptación del Experto
  repartía con mazos al azar y ahora usa mazos con semilla fija. El código del
  backend no cambió.
- Cuentas, login, base de datos de usuarios, perfiles y estadísticas.
- Minijuegos, bono diario y economía de fichas.
- Multijugador entre humanos, lobby, chat.
- Despliegue.

## Reglas innegociables
- NO se usa dinero real en ninguna parte. Las fichas son virtuales, viven
  solo en memoria durante la partida y no tienen valor fuera del juego.
- Mostrar de forma visible: "Solo para entretenimiento. Sin dinero real."

## Reglas del juego
- Texas Hold'em No-Limit, de 2 a 6 jugadores (1 humano + 1 a 5 bots).
- Blinds (pequeña y grande), botón de dealer que rota cada mano.
- Fases: preflop, flop, turn, river y showdown.
- Acciones: fold, check, call, raise (con monto) y all-in.
- Raise mínimo según las reglas oficiales. Acciones ilegales se rechazan.
- Side pots correctos cuando hay all-ins de distinto tamaño.
- Empates: el bote se divide; resto indivisible a la posición según reglas.
- Jugadores sin fichas quedan eliminados. Si el humano se queda sin
  fichas, ofrecer "Reiniciar partida" con fichas virtuales gratis.
- Configurable antes de empezar: número de bots, dificultad, fichas
  iniciales y blinds.

## Bots y dificultad
- Todos los bots comparten la misma interfaz: una función `decide` que recibe
  SOLO la vista pública de la mesa más sus propias cartas, y devuelve
  fold, call o raise con monto.
- Los bots nunca ven cartas ajenas ni el mazo. Cambiar de dificultad es
  cambiar la estrategia, nunca dar o quitar información.
- Niveles:
  - Fácil: pasivo y suelto, juega demasiadas manos, llama mucho, casi no
    hace farol y comete errores obvios.
  - Medio: decide según la fuerza de la mano inicial, usa pot odds básicos
    y respeta las apuestas grandes.
  - Difícil: estima su equity con simulación Monte Carlo (unos pocos miles
    de simulaciones), usa pot odds, varía el tamaño de sus apuestas, hace
    faroles ocasionales y considera la posición.
  - Experto: como Difícil, con rangos más ajustados, agresión selectiva,
    faroles con frecuencia calculada y algo de aleatoriedad.
- Cada bot tiene nombre y personalidad originales (por ejemplo "tight
  agresivo" o "suelto pasivo") que modifican levemente sus decisiones.
- Los bots "piensan" con un retraso aleatorio de 0.8 a 2.5 segundos.

## Reglas técnicas
- El SERVIDOR es la única autoridad: baraja, reparte, valida y paga. El
  cliente solo muestra el estado y envía intenciones ("fold", "raise 400").
- Los bots viven en el servidor y juegan como un jugador más.
- Nunca enviar al cliente las cartas de otros jugadores hasta el showdown,
  ni el mazo.
- Barajar con `secrets` o `random.SystemRandom` (nunca `random` normal).
- El motor de poker es Python puro, separado de FastAPI, para poder
  probarlo solo con pytest.
- Identificador de invitado guardado en el navegador, aislado en un módulo,
  para poder sustituirlo por login en etapas futuras.

## Reglas de la etapa 2

### Animaciones
- Las cartas se mueven con el estilo de Balatro: salen del mazo con fluidez,
  flotan suavemente mientras están quietas, se inclinan al pasar el ratón,
  hacen un efecto al seleccionarlas (se levantan con un rebote) y entran en la
  mesa con giro y rebote. Solo el movimiento: las cartas siguen siendo las
  nuestras, sin píxeles. Seleccionar una carta es un adorno; no cambia el juego.
- Reparto: las cartas salen del mazo (junto al dealer) y vuelan una a una
  hacia cada jugador en orden de reparto, con un pequeño retardo entre cartas.
- Mis cartas se voltean con un giro 3D al llegar; las de los bots quedan boca
  abajo y solo se voltean en el showdown.
- Flop, turn y river: las cartas comunitarias aparecen de una en una con
  deslizamiento y giro.
- Fichas: se deslizan del jugador al bote al apostar, y del bote al ganador
  al terminar la mano.
- Fold: las cartas del jugador se deslizan hacia el centro y se desvanecen.
- Resaltar de forma suave al jugador en turno y al ganador de la mano.
- Solo se animan `transform` y `opacity` (60 fps), con curvas de aceleración
  suaves y duraciones cortas: entre 200 y 500 ms por movimiento. La única
  excepción es continua, lenta y muy leve: la flotación en reposo, al mínimo.
  Las figuras de las cartas NO se animan.
- Los eventos del servidor pasan por una cola de animación: se reproducen en
  orden y no se pisan aunque lleguen varios seguidos. Los botones de acción se
  habilitan cuando termina la animación pendiente.
- Respetar `prefers-reduced-motion` y ofrecer una opción para desactivar las
  animaciones.

### Efectos de sonido
- Sonidos para: repartir carta, voltear carta, check, apostar o igualar
  fichas, subir, fold, all-in, ganar el bote, y un aviso suave cuando es mi
  turno.
- Cortos, discretos y sincronizados con su animación.

### Música de fondo
- Ambiental, tranquila y relajante (tipo lo-fi o ambient suave), en bucle sin
  cortes perceptibles y a volumen bajo por defecto.
- Empieza solo después de la primera interacción del usuario (política de
  reproducción automática de los navegadores).

### Controles de audio
- Un panel pequeño con volumen de música y volumen de efectos por separado, y
  un botón de silenciar todo. Las preferencias se guardan en localStorage.

### Origen del audio
- Nada con derechos de autor.
- Efectos y música se generan por código con la Web Audio API: la aplicación
  funciona sin ningún archivo de audio.
- Opcional: si existe `frontend/src/assets/audio/music.mp3` (o `.ogg`), se usa
  esa pista en lugar de la música generada, con fundido en el punto de bucle.
  Debe ser CC0 de verdad y la descargo yo; si falta, no hay ningún error.

### Decisiones de diseño aprobadas
- El servidor envía el estado completo tras cada cambio. El cliente compara
  el registro de la mano (`events`) con el anterior y lo convierte en pasos
  (línea de tiempo) que se reproducen de uno en uno. Al vaciarse la cola, lo
  mostrado es exactamente el estado del servidor, y solo entonces se activan
  los botones. El servidor sigue siendo la única autoridad.
- El reparto no es un evento del servidor: se deduce en el cliente con el
  botón y los jugadores con fichas, en el mismo orden que usa el motor.
- Animaciones sin librerías: API de animaciones del navegador y CSS. Los
  resaltes son halos ya dibujados a los que solo se les anima la opacidad.
- Las fichas van directas al bote; la apuesta de la ronda sigue visible como
  cifra junto a cada jugador.
- Si la cola se atrasa, se acelera. Con la pestaña oculta, al reconectar o
  con las animaciones desactivadas, se salta al estado final sin animar.
- Preferencias (animaciones, volúmenes, silencio) en localStorage, en un
  módulo aislado.

## Stack
- Backend: Python 3.12 + FastAPI + WebSockets.
- Frontend: React + TypeScript + Vite + Tailwind.
- Pruebas: pytest (backend) y Vitest (lógica pura del frontend: línea de
  tiempo, cola y preferencias).

## Hitos de la etapa 2 (detenerse al final de cada uno y esperar aprobación)
1. Mesa, línea de tiempo y audio (completado). Pantalla de inicio y mesa
   nuevas, cola de pasos con los botones bloqueados hasta el final,
   interruptor de animaciones, efectos de sonido sincronizados con cada paso,
   música de fondo tras la primera interacción, panel de audio con
   preferencias guardadas y tests con partidas grabadas del servidor real. El
   audio estaba previsto para más tarde y se adelantó a petición mía.
2. Animaciones (completado): cartas con el movimiento de Balatro (reparto
   desde el mazo, flotación, inclinación, selección, entrada en la mesa con
   giro), fichas al bote y al ganador, fold, resaltes y movimiento reducido.
   El reparto me gusta como está: NO cambiarlo.
3. Baraja clásica y colores de casino: caras de la baraja clásica inglesa
   (dominio público), sin animar; as de picas adornado y dorso propios;
   flotación de las cartas en reposo al mínimo; y toda la interfaz con la
   paleta de casino. Probé antes unas figuras dibujadas por mí que se movían
   y NO me gustaron: no volver a ellas.
4. Cierre: repaso final y README.

## Hitos de la etapa 1 (completada)
1. Motor de poker + tests: las 10 categorías de mano, empates por kickers,
   side pots con 3 all-ins distintos y simulaciones de manos completas
   verificando que la suma total de fichas se conserva siempre.
2. Bots + simulación: miles de manos bot contra bot con una tabla de
   resultados por nivel. Experto debe ganar más que Difícil, Difícil más que
   Medio y Medio más que Fácil. Si no es así, ajustar las estrategias.
3. Servidor FastAPI + WebSocket y una interfaz simple para jugar una
   partida completa contra los bots, con panel de configuración.

## Cómo trabajar
- Al cerrar cada hito: ejecutar los tests (backend y frontend), indicar cómo
  correr el proyecto y qué debería ver en pantalla, y esperar a que lo pruebe
  en el navegador.
- Un commit por hito, después de que lo apruebe.
- Si hay una decisión de diseño con varias opciones, preguntarme.

## Visión futura (solo referencia, NO implementar todavía)
- Etapa 3: cuentas y login, perfil, saldo y estadísticas.
- Etapa 4: minijuegos para ganar fichas, bono diario, límite diario.
- Etapa 5: multijugador entre humanos, lobby y chat.
