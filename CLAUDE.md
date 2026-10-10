# Proyecto: poker Texas Hold'em en el navegador contra bots

Juego de poker para navegador, inspirado en la idea general de los sitios de
poker social con fichas virtuales, pero con nombre, diseño y textos 100%
originales (no copiar marca, assets ni textos de ningún sitio existente).

## ETAPA ACTUAL: ETAPA 1 (solo juego, reglas y bots)
Objetivo: una partida completa de Texas Hold'em No-Limit en el navegador,
un humano contra 1 a 5 bots, con dificultad de bots ajustable.

Dentro del alcance:
- Motor de poker completo y probado.
- Bots con 4 niveles de dificultad.
- Servidor y una interfaz simple pero funcional para jugar y probar.

Fuera del alcance por ahora (NO implementar, solo dejar la estructura lista):
- Cuentas, login, base de datos de usuarios, perfiles y estadísticas.
- Minijuegos, bono diario y economía de fichas.
- Multijugador entre humanos, lobby, chat.
- Despliegue.
- Estética avanzada y animaciones: son la ETAPA 2. En la etapa 1 la interfaz
  debe ser limpia y usable, sin pulido visual.

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

## Stack
- Backend: Python 3.12 + FastAPI + WebSockets.
- Frontend: React + TypeScript + Vite + Tailwind.
- Pruebas: pytest.

## Hitos de la etapa 1 (detenerse al final de cada uno y esperar aprobación)
1. Motor de poker + tests: las 10 categorías de mano, empates por kickers,
   side pots con 3 all-ins distintos y simulaciones de manos completas
   verificando que la suma total de fichas se conserva siempre.
2. Bots + simulación: miles de manos bot contra bot con una tabla de
   resultados por nivel. Experto debe ganar más que Difícil, Difícil más que
   Medio y Medio más que Fácil. Si no es así, ajustar las estrategias.
3. Servidor FastAPI + WebSocket y una interfaz simple para jugar una
   partida completa contra los bots, con panel de configuración.

## Cómo trabajar
- Al cerrar cada hito: ejecutar los tests, indicar cómo correr el proyecto
  y qué debería ver en pantalla.
- Si hay una decisión de diseño con varias opciones, preguntarme.

## Visión futura (solo referencia, NO implementar todavía)
- Etapa 2: estética original (mesa, cartas SVG, fichas, avatares) y animaciones.
- Etapa 3: cuentas y login, perfil, saldo y estadísticas.
- Etapa 4: minijuegos para ganar fichas, bono diario, límite diario.
- Etapa 5: multijugador entre humanos, lobby y chat.
