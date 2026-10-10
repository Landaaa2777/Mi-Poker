// Prepara la baraja clásica para el juego.
//
// Las caras de las cartas son de Adrian Kennard (https://www.me.uk/cards/),
// publicadas como CC0 (dominio público); sus figuras están calcadas de una
// baraja Goodall & Son del siglo XIX, el diseño clásico inglés. Este script
// toma los SVG tal como salen de su generador y los deja listos:
//
//   1. Descargar el zip "SVG for web use" con estas opciones:
//      https://www.me.uk/cards/makeadeck.cgi?zip=1&size=poker&ace=Large&back=Diamond&pip=1&value=0&super=1&modern=on&ace1=&ace2=&qr=
//      (índice mediano, para que el valor se lea bien en cartas pequeñas, y
//      figuras mirando hacia donde miran en las barajas actuales).
//   2. Descomprimirlo en una carpeta.
//   3. node tools/import_cards.mjs <esa carpeta>
//
// Cambios que hace: quita el borde y las esquinas del fondo (los pone la
// propia carta en pantalla), ajusta los tres colores y adorna el as de picas.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const source = process.argv[2];
if (!source) {
  console.error("Uso: node tools/import_cards.mjs <carpeta con los SVG descargados>");
  process.exit(1);
}
const target = join(dirname(fileURLToPath(import.meta.url)), "..", "src", "assets", "cards");

// Paleta de la baraja: los colores clásicos, algo más profundos.
const RED = "#d5121e";
const BLUE = "#2440c4";
const GOLD = "#f6c12b";
const BLACK = "#16151a";

const RANKS = "A23456789TJQK";
const SUITS = "SHDC";

function recolor(svg) {
  return svg
    .replaceAll('"red"', `"${RED}"`)
    .replaceAll('"#44F"', `"${BLUE}"`)
    .replaceAll('"#FC4"', `"${GOLD}"`)
    .replaceAll('"black"', `"${BLACK}"`);
}

/** El fondo pasa a ocupar toda la carta, sin borde ni esquinas: eso lo dibuja el juego. */
function flattenBackground(svg) {
  const background =
    '<rect width="239" height="335" x="-119.5" y="-167.5" rx="12" ry="12" fill="white" stroke="black"></rect>';
  if (!svg.includes(background)) throw new Error("No encuentro el fondo de la carta");
  return svg.replace(background, '<rect width="240" height="336" x="-120" y="-168" fill="white"></rect>');
}

/** As de picas adornado: pica mediana, laurel, emblema del juego y cinta con el nombre. */
function ornateAce(svg) {
  // La pica central es el primer uso del palo y el único grande.
  const bigSpade = svg.match(/<use xlink:href="#SSA" height="([0-9.]+)"[^>]*><\/use>/);
  if (!bigSpade || Number(bigSpade[1]) < 100) throw new Error("No encuentro la pica grande del as");

  const leaves = [116, 131, 146, 161, 176, 191, 206]
    .map((degrees) => {
      const angle = (degrees * Math.PI) / 180;
      const x = (74 * Math.cos(angle)).toFixed(1);
      const y = (-6 + 74 * Math.sin(angle)).toFixed(1);
      return `<ellipse cx="${x}" cy="${y}" rx="11.6" ry="4.6" transform="rotate(${degrees + 60} ${x} ${y})"></ellipse>`;
    })
    .join("");
  const branch = `<path d="M-32 61Q-78 40 -66 -38" fill="none" stroke="black" stroke-width="2"></path>${leaves}`;
  const ornament = [
    `<g fill="black">${branch}<g transform="scale(-1 1)">${branch}</g></g>`,
    '<use xlink:href="#SSA" height="150" width="150" x="-75" y="-92"></use>',
    '<circle cx="0" cy="-12" r="20" fill="none" stroke="white" stroke-width="2.4"></circle>',
    '<circle cx="0" cy="-12" r="14.2" fill="none" stroke="white" stroke-width="5.2" stroke-dasharray="5.7 5.45"></circle>',
    '<circle cx="0" cy="-12" r="4.6" fill="white"></circle>',
    '<path d="M-56 84l-11 11.5 11 10zM56 84l11 11.5-11 10z" fill="#3b3b44"></path>',
    '<path d="M-56 80Q0 63 56 80L56 102Q0 85 -56 102Z" fill="black"></path>',
    '<text x="0" y="91.5" text-anchor="middle" font-size="15" font-weight="700" letter-spacing="2.8" fill="white" font-family="Georgia, \'Times New Roman\', serif">MI-POKER</text>',
  ].join("");
  return svg.replace(bigSpade[0], ornament);
}

mkdirSync(target, { recursive: true });
let count = 0;
for (const suit of SUITS) {
  for (const rank of RANKS) {
    const name = `${rank}${suit}.svg`;
    let svg = readFileSync(join(source, name), "utf8");
    if (/<script|<image|<foreignObject|href="(?!#)/i.test(svg)) {
      throw new Error(`${name} trae contenido que no debería tener una carta`);
    }
    svg = flattenBackground(svg);
    if (name === "AS.svg") svg = ornateAce(svg);
    writeFileSync(join(target, name), recolor(svg));
    count += 1;
  }
}
console.log(`${count} cartas preparadas en ${target}`);
