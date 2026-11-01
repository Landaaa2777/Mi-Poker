// Línea de tiempo de Prisma: convierte el registro de la ronda (`events`) en
// pasos que se reproducen de uno en uno: el reparto, cada carta que va al
// descarte, cada robo y los avisos (saltos, cambios de sentido, "¡Última!"…).
//
// Cada paso trae la mesa tal como debe dibujarse (`frame`), calculada rehaciendo
// la ronda con el registro. El último paso es siempre la mesa exacta del servidor.
//
// En Doble cara, además, se sigue paso a paso la otra cara que se ve de las
// manos ajenas y de la carta de encima del mazo; en Sin tregua, quién queda
// fuera, las cartas apartadas y la cuenta de las cargas acumuladas.

import type { Timeline } from "../../shared/timeline/playback";
import { KIND_NAMES, cardName } from "./cardArt";
import { SUITS, type PrismaColor } from "./shapes";
import type { Card, Face, GameEvent, GameState, Mode, Side } from "./types";

export interface PlayerFrame {
  seat: number;
  name: string;
  isHuman: boolean; // soy yo
  person?: boolean; // en una sala: lo juega una persona
  level: string;
  count: number;
  score: number;
  saidLast: boolean;
  vulnerable: boolean;
  out: boolean; // Sin tregua: eliminado de la ronda
  backs: Face[]; // Doble cara: la otra cara de sus cartas, la que veo (nunca de las mías)
  action: string | null; // lo último que le ha pasado, para enseñarlo junto a su asiento
}

/** Cartas que se enseñan a todos un momento: las que destapa la Ruleta o las que barre el Barrido. */
export interface Shown {
  kind: "reveal" | "sweep";
  seat: number;
  cards: Card[];
}

export interface Frame {
  mode: Mode;
  side: Side; // la cara en juego (siempre "luz" fuera de Doble cara)
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
  deckBack: Face | null; // Doble cara: la cara que se ve encima del mazo
  asideCount: number; // Sin tregua: cartas apartadas de los eliminados
  pending: number; // cartas acumuladas por las cargas, a la espera de quien las robe
  handFrom: number | null; // de quién me acaba de llegar la mano (un 7 o un 0)
  shown: Shown | null; // cartas destapadas o barridas en este paso
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

export const DECK_SIZES: Record<Mode, number> = { clasico: 108, doble_cara: 112, sin_tregua: 168 };

// Los sucesos que cambian el mazo traen, en Doble cara, la cara que queda encima.
const DECK_EVENTS = new Set(["deal", "return", "start", "draw", "reveal", "reshuffle", "eclipse"]);
// Los comodines que se pueden desafiar.
const RESTRICTED = new Set(["camaleon4", "camaleon2", "sabueso"]);

// --- La mesa del servidor, tal cual ---

export function frameFromState(state: GameState): Frame {
  return {
    mode: state.mode ?? "clasico",
    side: state.side ?? "luz",
    round: state.round_number,
    players: state.players.map((player) => ({
      seat: player.seat,
      name: player.name,
      isHuman: player.is_human,
      person: player.person,
      level: player.level,
      count: player.count,
      score: player.score,
      saidLast: player.said_last,
      vulnerable: player.vulnerable,
      out: player.out ?? false,
      backs: player.backs ?? [],
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
    deckBack: state.deck_back ?? null,
    asideCount: state.aside_count ?? 0,
    pending: state.pending_draw,
    handFrom: null,
    shown: null,
    note: null,
    events: state.events,
  };
}

function lastPlayer(events: GameEvent[]): number | null {
  for (let index = events.length - 1; index >= 0; index--) {
    const event = events[index];
    if (event.kind === "play") return event.seat;
    if (event.kind === "start" || event.kind === "eclipse") return null;
  }
  return null;
}

// --- Rehacer la ronda con el registro ---

/** El siguiente asiento que sigue en la ronda, yendo en el sentido `step` (1 o -1). */
function neighbour(players: PlayerFrame[], seat: number, step: number): number {
  const count = players.length;
  let next = seat;
  for (let index = 0; index < count; index++) {
    next = (next + step + count) % count;
    if (!players[next].out) return next;
  }
  return seat;
}

/** La mesa tras los `count` primeros sucesos de la ronda de `state`. */
export function frameAt(state: GameState, count: number): Frame {
  const me = state.human_seat;
  const mode: Mode = state.mode ?? "clasico";
  const players: PlayerFrame[] = state.players.map((player) => ({
    seat: player.seat,
    name: player.name,
    isHuman: player.is_human,
    person: player.person,
    level: player.level,
    count: 0,
    score: player.score,
    saidLast: false,
    vulnerable: false,
    out: false,
    backs: [],
    action: null,
  }));
  const frame: Frame = {
    mode,
    side: "luz",
    round: state.round_number,
    players,
    hand: [],
    top: null,
    color: null,
    direction: 1,
    turn: null,
    drawCount: DECK_SIZES[mode],
    discardCount: 0,
    lastPlayer: null,
    deckBack: null,
    asideCount: 0,
    pending: 0,
    handFrom: null,
    shown: null,
    note: null,
    events: state.events.slice(0, count),
  };
  const name = (seat: number | null) => (seat === null ? "" : players[seat].name);
  let wild: Card | null = null; // el último comodín que se puede desafiar

  // Tras un Eclipse, un 7 o un 0: cómo quedan las manos. Si cambian de dueño
  // (`moved`), quien se queda así con una carta está a salvo: no la jugó él.
  function handsMoved(event: GameEvent, moved: boolean) {
    frame.hand = [...event.cards];
    (event.counts ?? []).forEach((cards, seat) => {
      players[seat].count = cards;
      if (moved) {
        players[seat].saidLast = cards === 1;
        players[seat].vulnerable = false;
      }
    });
    for (const player of players) {
      player.backs = player.seat === me ? [] : [...(event.backs?.[String(player.seat)] ?? [])];
    }
  }

  for (const event of frame.events) {
    const player = event.seat === null ? null : players[event.seat];
    frame.note = null;
    frame.handFrom = null;
    frame.shown = null;
    if (mode === "doble_cara" && DECK_EVENTS.has(event.kind)) frame.deckBack = event.deck_back ?? null;
    switch (event.kind) {
      case "deal":
        player!.count += event.count;
        frame.drawCount -= event.count;
        if (event.seat === me) frame.hand = [...event.cards];
        else player!.backs = [...(event.backs?.[String(event.seat)] ?? [])];
        break;
      case "return":
        frame.note = `${event.card ? cardName(event.card) : "Esa carta"} no puede abrir: vuelve al mazo`;
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
      case "skip_all":
        frame.note = "¡Pausa total! Todos pierden el turno";
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
        else if (event.key !== null && event.key !== undefined) player!.backs = player!.backs.filter((face) => face.key !== event.key);
        frame.top = event.card;
        frame.color = event.color;
        frame.discardCount += 1;
        frame.lastPlayer = event.seat;
        frame.turn = event.seat;
        if (event.card && RESTRICTED.has(event.card.kind)) wild = event.card;
        break;
      case "sweep": {
        // El Barrido se lleva también las demás cartas de su color (debajo del descarte).
        const swept = new Set(event.cards.map((card) => card.id));
        player!.count -= event.count;
        if (event.seat === me) frame.hand = frame.hand.filter((card) => !swept.has(card.id));
        frame.discardCount += event.count;
        frame.shown = { kind: "sweep", seat: event.seat!, cards: event.cards };
        frame.note = `¡Barrido! ${event.count} ${event.count === 1 ? "carta más" : "cartas más"} al descarte`;
        break;
      }
      case "stack":
        frame.pending = event.count;
        frame.note = `¡Se acumula! Ya son +${event.count}`;
        break;
      case "last":
        player!.saidLast = true;
        player!.action = "¡Última!";
        break;
      case "draw":
      case "reveal":
        player!.count += event.count;
        frame.drawCount -= event.count;
        if (player!.count > 1) player!.saidLast = false;
        if (event.seat === me) frame.hand = [...frame.hand, ...event.cards];
        else player!.backs = [...player!.backs, ...(event.backs?.[String(event.seat)] ?? [])];
        if (event.reason === "acumuladas" || event.reason === "final") frame.pending = 0;
        player!.action = event.count > 0 ? `Roba ${event.count}` : "No quedan cartas";
        frame.turn = event.seat;
        if (event.kind === "reveal") {
          frame.shown = { kind: "reveal", seat: event.seat!, cards: event.cards };
          frame.color = event.color;
          frame.note = `Ruleta: ${event.count} ${event.count === 1 ? "carta" : "cartas"} hasta sacar ${event.color ? colorName(event.color) : "el color"}`;
        }
        break;
      case "pass":
        player!.action = "Pasa";
        break;
      case "caught":
        player!.action = "¡Pillado!";
        frame.note = `${name(event.target)} pilla a ${name(event.seat)} sin decir «¡Última!»`;
        break;
      case "challenge": {
        const what = wild ? KIND_NAMES[wild.kind as keyof typeof KIND_NAMES] : "comodín";
        frame.note =
          event.result === "guilty"
            ? `${name(event.seat)} desafía y acierta: era un farol`
            : `${name(event.seat)} desafía y falla: el ${what} era legal`;
        break;
      }
      case "eclipse":
        // Todo da la vuelta: el descarte (la de abajo queda arriba), el mazo y las manos.
        frame.side = event.result === "sombra" ? "sombra" : "luz";
        frame.top = event.card;
        frame.color = event.card && event.card.color !== null ? event.card.color : null;
        frame.lastPlayer = null;
        handsMoved(event, false);
        frame.note = frame.side === "sombra" ? "¡Eclipse! Todo da la vuelta: llega la sombra" : "¡Eclipse! Todo da la vuelta: vuelve la luz";
        break;
      case "swap":
        handsMoved(event, true);
        player!.action = "Cambia de mano";
        if (event.seat === me) frame.handFrom = event.target;
        else if (event.target === me) frame.handFrom = event.seat;
        frame.note = `${name(event.seat)} cambia su mano con ${name(event.target)}`;
        break;
      case "rotate":
        // Cada uno pasa su mano al siguiente: la mía viene del anterior.
        frame.handFrom = neighbour(players, me, -frame.direction);
        handsMoved(event, true);
        frame.note = "¡Todos pasan su mano al siguiente!";
        break;
      case "eliminated":
        player!.count = 0;
        player!.out = true;
        player!.backs = [];
        if (event.seat === me) frame.hand = []; // mis cartas se apartan
        player!.saidLast = false;
        player!.vulnerable = false;
        player!.action = "¡Desbordado!";
        frame.asideCount += event.count;
        frame.note = `${name(event.seat)} llega a ${event.count} cartas: queda fuera de la ronda`;
        break;
      case "reshuffle":
        frame.drawCount += event.count;
        frame.discardCount = 1;
        frame.asideCount = 0;
        frame.note = "Se acabó el mazo: se rebaraja el descarte";
        break;
      case "blocked":
        frame.note = "Ronda trancada: gana quien tiene menos cartas";
        break;
      case "round_over":
        frame.turn = null;
        break;
    }
  }
  return frame;
}

function colorName(color: PrismaColor): string {
  return SUITS[color].name;
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
    else if ((event.kind === "draw" || event.kind === "reveal") && event.count > 0)
      steps.push({ kind: "draw", seat: event.seat!, frame });
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
      return step.frame.shown ? 850 : 380; // la Ruleta enseña lo que destapa
    case "event":
      switch (step.event.kind) {
        case "caught":
        case "challenge":
        case "eliminated":
          return 900;
        case "eclipse":
        case "swap":
        case "rotate":
        case "sweep":
          return 700;
        case "skip_all":
        case "stack":
          return 650;
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
