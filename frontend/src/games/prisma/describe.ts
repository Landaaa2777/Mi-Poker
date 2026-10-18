// Textos de Prisma: el registro de la ronda, en español.

import { cardName } from "./cardArt";
import { SUITS } from "./shapes";
import type { Frame } from "./timeline";
import type { GameEvent } from "./types";

const DRAW_REASON: Record<string, string> = {
  carga: " por la Carga +2",
  camaleon4: " por el Camaleón +4",
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

  switch (event.kind) {
    case "deal":
      return mine ? `Recibes ${event.count} cartas` : null;
    case "return":
      return "Un Camaleón +4 no puede abrir la ronda: vuelve al mazo";
    case "start":
      return `— Empieza la ronda con ${cardName(event.card!)} —`;
    case "choose":
      return `${does("elige", "Eliges")} el color ${color}`;
    case "skip":
      return does("pierde el turno", "Pierdes el turno");
    case "reverse":
      return "El juego cambia de sentido";
    case "play": {
      const card = event.card!;
      const chosen = card.color === null ? ` y ${mine ? "eliges" : "elige"} ${color}` : "";
      return `${does("juega", "Juegas")} ${cardName(card)}${chosen}`;
    }
    case "last":
      return `${does("dice", "Dices")} «¡Última!»`;
    case "draw": {
      if (event.count === 0) return does("no puede robar: no quedan cartas", "No puedes robar: no quedan cartas");
      const what = event.count === 1 ? "una carta" : `${event.count} cartas`;
      return `${does("roba", "Robas")} ${what}${DRAW_REASON[event.reason] ?? ""}`;
    }
    case "pass":
      return does("pasa", "Pasas");
    case "caught": {
      const accuser = event.target === me ? "Pillas" : `${name(event.target)} pilla`;
      const target = mine ? "a ti" : `a ${name(event.seat)}`;
      return `¡${accuser} ${target} sin decir «¡Última!»!`;
    }
    case "challenge":
      return event.result === "guilty"
        ? `${does("desafía", "Desafías")} el +4 de ${name(event.target)}: ¡era un farol!`
        : `${does("desafía", "Desafías")} el +4 de ${name(event.target)}, pero era legal`;
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
