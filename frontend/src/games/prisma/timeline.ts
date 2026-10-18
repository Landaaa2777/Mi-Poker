// Línea de tiempo de Prisma: convierte el registro de la ronda (`events`) en
// pasos que se reproducen de uno en uno: el reparto, cada carta que va al
// descarte, cada robo y los avisos (saltos, cambios de sentido, "¡Última!"…).
//
// Cada paso trae la mesa tal como debe dibujarse (`frame`), calculada rehaciendo
// la ronda con el registro. El último paso es siempre la mesa exacta del servidor.

import type { Timeline } from "../../shared/timeline/playback";
import type { PrismaColor } from "./shapes";
import type { Card, GameEvent, GameState } from "./types";

export interface PlayerFrame {
  seat: number;
  name: string;
  isHuman: boolean;
  level: string;
  count: number;
  score: number;
  saidLast: boolean;
  vulnerable: boolean;
  action: string | null; // lo último que le ha pasado, para enseñarlo junto a su asiento
}

export interface Frame {
  round: number;
  players: PlayerFrame[];
  hand: Card[]; // mis cartas
  top: Card | null;
  color: PrismaColor | null;
  direction: 1 | -1;
  turn: number | null; // a quién se resalta
  drawCount: number;
  discardCount: number;
  lastPlayer: number | null; // quién soltó la carta de arriba (null = salió del mazo)
  note: string | null;
  events: GameEvent[];
}

export type Step =
  | { kind: "round"; frame: Frame } // ronda nueva: mesa limpia
  | { kind: "deal"; seat: number; frame: Frame } // el reparto de un jugador
  | { kind: "play"; seat: number | null; frame: Frame } // una carta al descarte (null = la inicial)
  | { kind: "draw"; seat: number; frame: Frame } // cartas del mazo a un jugador
  | { kind: "event"; event: GameEvent; frame: Frame } // salto, sentido, aviso, pillada, desafío…
  | { kind: "sync"; frame: Frame }; // la mesa exacta del servidor

const DECK_SIZE = 108;

// --- La mesa del servidor, tal cual ---

export function frameFromState(state: GameState): Frame {
  return {
    round: state.round_number,
    players: state.players.map((player) => ({
      seat: player.seat,
      name: player.name,
      isHuman: player.is_human,
      level: player.level,
      count: player.count,
      score: player.score,
      saidLast: player.said_last,
      vulnerable: player.vulnerable,
      action: null,
    })),
    hand: state.hand,
    top: state.top,
    color: state.color,
    direction: state.direction,
    turn: state.phase === "round_over" ? null : state.turn,
    drawCount: state.draw_count,
    discardCount: state.discard_count,
    lastPlayer: lastPlayer(state.events),
    note: null,
    events: state.events,
  };
}

function lastPlayer(events: GameEvent[]): number | null {
  for (let index = events.length - 1; index >= 0; index--) {
    const event = events[index];
    if (event.kind === "play") return event.seat;
    if (event.kind === "start") return null;
  }
  return null;
}

// --- Rehacer la ronda con el registro ---

/** La mesa tras los `count` primeros sucesos de la ronda de `state`. */
export function frameAt(state: GameState, count: number): Frame {
  const me = state.human_seat;
  const players: PlayerFrame[] = state.players.map((player) => ({
    seat: player.seat,
    name: player.name,
    isHuman: player.is_human,
    level: player.level,
    count: 0,
    score: player.score,
    saidLast: false,
    vulnerable: false,
    action: null,
  }));
  const frame: Frame = {
    round: state.round_number,
    players,
    hand: [],
    top: null,
    color: null,
    direction: 1,
    turn: null,
    drawCount: DECK_SIZE,
    discardCount: 0,
    lastPlayer: null,
    note: null,
    events: state.events.slice(0, count),
  };
  const name = (seat: number | null) => (seat === null ? "" : players[seat].name);

  for (const event of frame.events) {
    const player = event.seat === null ? null : players[event.seat];
    frame.note = null;
    switch (event.kind) {
      case "deal":
        player!.count += event.count;
        frame.drawCount -= event.count;
        if (event.seat === me) frame.hand = [...event.cards];
        break;
      case "return":
        frame.note = "Un Camaleón +4 no puede abrir: vuelve al mazo";
        break;
      case "start":
        frame.top = event.card;
        frame.color = event.color;
        frame.drawCount -= 1;
        frame.discardCount = 1;
        frame.lastPlayer = null;
        break;
      case "choose":
        frame.color = event.color;
        break;
      case "skip":
        player!.action = "Pierde el turno";
        break;
      case "reverse":
        frame.direction = frame.direction === 1 ? -1 : 1;
        frame.note = "¡Cambia el sentido!";
        break;
      case "play":
        player!.count -= 1;
        player!.action = null;
        if (player!.count !== 1) player!.saidLast = false;
        if (event.seat === me) frame.hand = frame.hand.filter((card) => card.id !== event.card!.id);
        frame.top = event.card;
        frame.color = event.color;
        frame.discardCount += 1;
        frame.lastPlayer = event.seat;
        frame.turn = event.seat;
        break;
      case "last":
        player!.saidLast = true;
        player!.action = "¡Última!";
        break;
      case "draw":
        player!.count += event.count;
        frame.drawCount -= event.count;
        if (player!.count > 1) player!.saidLast = false;
        if (event.seat === me) frame.hand = [...frame.hand, ...event.cards];
        player!.action = event.count > 0 ? `Roba ${event.count}` : "No quedan cartas";
        frame.turn = event.seat;
        break;
      case "pass":
        player!.action = "Pasa";
        break;
      case "caught":
        player!.action = "¡Pillado!";
        frame.note = `${name(event.target)} pilla a ${name(event.seat)} sin decir «¡Última!»`;
        break;
      case "challenge":
        frame.note =
          event.result === "guilty"
            ? `${name(event.seat)} desafía y acierta: era un farol`
            : `${name(event.seat)} desafía y falla: el +4 era legal`;
        break;
      case "reshuffle":
        frame.drawCount += event.count;
        frame.discardCount = 1;
        frame.note = "Se acabó el mazo: se rebaraja el descarte";
        break;
      case "round_over":
        frame.turn = null;
        break;
    }
  }
  return frame;
}

// --- Pasos ---

/** ¿Sigue `next` la misma ronda que `previous`, con el registro solo crecido? */
export function continuesRound(previous: GameState | null, next: GameState): boolean {
  if (previous === null || previous.round_number !== next.round_number) return false;
  if (next.events.length < previous.events.length) return false;
  return previous.events.every(
    (event, index) => JSON.stringify(event) === JSON.stringify(next.events[index]),
  );
}

export function buildSteps(previous: GameState | null, next: GameState): Step[] {
  const steps: Step[] = [];
  let from = 0;
  if (continuesRound(previous, next)) {
    from = previous!.events.length;
  } else {
    steps.push({ kind: "round", frame: frameAt(next, 0) });
  }
  for (let index = from; index < next.events.length; index++) {
    const event = next.events[index];
    const frame = frameAt(next, index + 1);
    if (event.kind === "deal") steps.push({ kind: "deal", seat: event.seat!, frame });
    else if (event.kind === "play") steps.push({ kind: "play", seat: event.seat, frame });
    else if (event.kind === "start") steps.push({ kind: "play", seat: null, frame });
    else if (event.kind === "draw" && event.count > 0) steps.push({ kind: "draw", seat: event.seat!, frame });
    else steps.push({ kind: "event", event, frame });
  }
  steps.push({ kind: "sync", frame: frameFromState(next) });
  return steps;
}

/** Milisegundos que se muestra cada paso. Cada animación dura entre 200 y 500 ms. */
export function stepDelay(step: Step, next: Step | undefined): number {
  switch (step.kind) {
    case "round":
      return 200;
    case "deal":
      return next?.kind === "deal" ? 260 : 520;
    case "play":
      return 460;
    case "draw":
      return 380;
    case "event":
      switch (step.event.kind) {
        case "caught":
        case "challenge":
          return 900;
        case "round_over":
          return 600;
        case "reverse":
        case "reshuffle":
        case "return":
          return 650;
        case "last":
          return 520;
        case "pass":
          return 260;
        default:
          return 420;
      }
    case "sync":
      return 0;
  }
}

export const PRISMA_TIMELINE: Timeline<GameState, Frame, Step> = {
  buildSteps,
  frameFromState,
  stepDelay,
  startsRound: (step) => step.kind === "round",
};
