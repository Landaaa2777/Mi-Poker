# Música propia (opcional)

El juego funciona sin ningún archivo de audio: los efectos y la música de fondo
se generan por código. Esta carpeta solo sirve para sustituir la música
generada por una pista tuya.

## Cómo usarla

1. Guarda aquí **una** pista con el nombre `music` y una de estas extensiones:
   `music.mp3`, `music.ogg`, `music.wav` o `music.m4a`.
2. Vuelve a compilar (`npm run build`) o, si usas `npm run dev`, recarga la página.

La pista se repite sola. No hace falta que esté preparada para repetirse: cada
vuelta empieza unos segundos antes de que acabe la anterior y las dos se funden.
Si el archivo falta o el navegador no lo sabe leer, suena la música generada y
no aparece ningún error.

## Licencia

Usa solo música que puedas usar de verdad, idealmente **CC0** (dominio público).
Comprueba la licencia en la página de la propia pista antes de descargarla, y
no añadas el archivo al repositorio si su licencia no permite redistribuirlo.
