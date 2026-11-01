// Textos de Prisma: el registro de la ronda, en español.

import type { LogLine } from "../../shared/components/EventLog";
import { KIND_NAMES, cardName } from "./cardArt";
import { SUITS } from "./shapes";
import type { Frame } from "./timeline";
import type { GameEvent, Mode } from "./types";

export const MODE_NAMES: Record<Mode, string> = {
  clasico: "Clásico",
  doble_cara: "Doble cara",
  sin_tregua: "Sin tregua",
};

const DRAW_REASON: Record<string, string> = {
  carga: " por la Carga +2",
  carga1: " por la Carga +1",
  carga5: " por la Carga +5",
  camaleon4: " por el Camaleón +4",
  camaleon2: " por el Camaleón +2",
  sabueso: " hasta dar con el color, por el Camaleón Sabueso",
  acumuladas: " (las acumuladas)",
  pillado: " de castigo",
  desafio: " por el desafío",
  final: " por la última carta",
};

/**
 * Una línea del registro: el suceso número `index` de `frame.events`. `me` es
 * mi asiento: lo mío se cuenta en segunda persona. Algunos sucesos no llevan
 * línea (null).
 */
export function describeEvent(index: number, frame: Frame, me: number): string | null {
  const event: GameEvent = frame.events[index];
  const mine = event.seat === me;
  const name = (seat: number | null) => (seat === null ? "" : frame.players[seat]?.name ?? "");
  const does = (theirs: string, yours: string) => (mine ? yours : `${name(event.seat)} ${theirs}`);
  const color = event.color ? SUITS[event.color].name : "";
  // El comodín al que se refiere un desafío: el último que se jugó.
  const challenged = () => {
    for (let at = index - 1; at >= 0; at--) {
      const card = frame.events[at].card;
      if (frame.events[at].kind === "play" && card && card.color === null) return KIND_NAMES[card.kind as keyof typeof KIND_NAMES];
    }
    return "comodín";
  };

  switch (event.kind) {
    case "deal":
      return mine ? `Recibes ${event.count} cartas` : null;
    case "return":
      return `${event.card ? cardName(event.card) : "Esa carta"} no puede abrir la ronda: vuelve al mazo`;
    case "start":
      return `— Empieza la ronda con ${cardName(event.card!)} —`;
    case "choose":
      return `${does("elige", "Eliges")} el color ${color}`;
    case "skip":
      return does("pierde el turno", "Pierdes el turno");
    case "skip_all":
      return mine ? "Todos los demás pierden el turno: vuelves a jugar" : `Todos pierden el turno: vuelve a jugar ${name(event.seat)}`;
    case "reverse":
      return "El juego cambia de sentido";
    case "play": {
      const card = event.card!;
      // La Ruleta no lleva color: lo elige quien la sufre.
      const chosen = card.color === null && card.kind !== "ruleta" ? ` y ${mine ? "eliges" : "elige"} ${color}` : "";
      return `${does("juega", "Juegas")} ${cardName(card)}${chosen}`;
    }
    case "sweep":
      return `${does("barre", "Barres")} ${event.count === 1 ? "otra carta" : `${event.count} cartas más`} de ${color}: ${event.cards.map(cardName).join(", ")}`;
    case "stack":
      return `La cuenta sube: +${event.count} acumuladas`;
    case "eclipse":
      return event.result === "sombra"
        ? "— ¡Eclipse! Todo da la vuelta: se juega por la sombra —"
        : "— ¡Eclipse! Todo da la vuelta: vuelve la luz —";
    case "swap": {
      const other = event.target === me ? "contigo" : `con ${name(event.target)}`;
      return mine ? `Cambias tu mano con ${name(event.target)}` : `${name(event.seat)} cambia su mano ${other}`;
    }
    case "rotate":
      return "Todos pasan su mano al siguiente";
    case "reveal": {
      const what = event.count === 1 ? "una carta" : `${event.count} cartas`;
      return `${does("elige", "Eliges")} ${color} y ${mine ? "destapas" : "destapa"} ${what}: ${event.cards.map(cardName).join(", ")}`;
    }
    case "eliminated":
      return mine
        ? `Llegas a ${event.count} cartas: quedas fuera de la ronda`
        : `${name(event.seat)} llega a ${event.count} cartas: queda fuera de la ronda`;
    case "last":
      return `${does("dice", "Dices")} «¡Última!»`;
    case "draw": {
      if (event.count === 0) return does("no puede robar: no quedan cartas", "No puedes robar: no quedan cartas");
      const what = event.count === 1 ? "una carta" : `${event.count} cartas`;
      // Sin tregua: en tu turno se roba hasta sacar una que sirva.
      const until = frame.mode === "sin_tregua" && event.reason === "turno" && event.count > 1 ? " hasta sacar una que sirve" : "";
      return `${does("roba", "Robas")} ${what}${until}${DRAW_REASON[event.reason] ?? ""}`;
    }
    case "pass":
      return does("pasa", "Pasas");
    case "caught": {
      const accuser = event.target === me ? "Pillas" : `${name(event.target)} pilla`;
      const target = mine ? "a ti" : `a ${name(event.seat)}`;
      return `¡${accuser} ${target} sin decir «¡Última!»!`;
    }
    case "challenge": {
      const whose = event.target === me ? "tu" : `el`;
      const owner = event.target === me ? "" : ` de ${name(event.target)}`;
      return event.result === "guilty"
        ? `${does("desafía", "Desafías")} ${whose} ${challenged()}${owner}: ¡era un farol!`
        : `${does("desafía", "Desafías")} ${whose} ${challenged()}${owner}, pero era legal`;
    }
    case "reshuffle":
      return "— Se acabó el mazo: se rebaraja el descarte —";
    case "blocked":
      return "— Nadie puede jugar ni robar: gana quien tiene menos cartas —";
    case "round_over":
      return mine
        ? `¡Ganas la ronda!${event.count ? ` (${event.count} puntos)` : ""}`
        : `${name(event.seat)} gana la ronda${event.count ? ` (${event.count} puntos)` : ""}`;
  }
}


const HIGHLIGHT = new Set(["round_over", "caught", "challenge", "blocked", "eliminated", "eclipse"]);
const NOTE = new Set(["start", "reshuffle", "reverse", "return", "rotate", "stack"]);

/** Las líneas del registro de la ronda que se ve ahora en la mesa. */
export function logLines(frame: Frame, me: number): LogLine[] {
  const lines: LogLine[] = [];
  frame.events.forEach((event, index) => {
    const text = describeEvent(index, frame, me);
    if (text === null) return;
    const tone = HIGHLIGHT.has(event.kind)
      ? "highlight"
      : NOTE.has(event.kind)
        ? "note"
        : event.seat === me
          ? "mine"
          : "others";
    lines.push({ text, tone });
  });
  return lines;
}
