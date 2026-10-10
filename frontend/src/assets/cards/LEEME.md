# Baraja

Las 52 caras de esta carpeta son la baraja clásica inglesa de **Adrian Kennard**
(RevK), publicada como **CC0 1.0 (dominio público)** en https://www.me.uk/cards/.
Sus figuras (jotas, reinas y reyes) están calcadas de una baraja Goodall & Son
del siglo XIX, el diseño del que descienden las barajas de póker actuales.

No llevan el nombre ni los dibujos de ninguna marca.

## Qué se cambió respecto al original

Lo hace `frontend/tools/import_cards.mjs`, que también explica cómo volver a
descargarlas:

- El fondo ocupa toda la carta, sin borde ni esquinas: eso lo dibuja el juego.
- Los colores rojo, azul y dorado son algo más profundos.
- El as de picas lleva un adorno propio: laurel, el emblema del juego y una
  cinta con su nombre.

El dorso de las cartas y la cara sencilla de las cartas pequeñas no vienen de
esta baraja: son dibujo propio del juego.
