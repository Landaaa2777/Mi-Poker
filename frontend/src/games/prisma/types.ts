// Formas de los mensajes de Prisma (ver backend/games/prisma/protocol.py).

import type { GameOption } from "../../shared/options";
import type { PrismaColor } from "./shapes";
import type { TurnTimer } from "../../shared/room";

export type Kind =
  // Clásico
  | "number"
  | "pausa"
  | "remolino"
  | "carga"
  | "camaleon"
  | "camaleon4"
  // Doble cara
  | "carga1"
  | "carga5"
  | "eclipse"
  | "pausa_total"
  | "camaleon2"
  | "sabueso"
  // Sin tregua (además de Pausa total)
  | "carga4"
  | "barrido"
  | "camaleon_remolino4"
  | "camaleon6"
  | "camaleon10"
  | "ruleta";
export type Phase = "choose_color" | "playing" | "challenge" | "roulette" | "round_over";
export type Mode = "clasico" | "doble_cara" | "sin_tregua";
export type Side = "luz" | "sombra";

export interface Card {
  id: number; // único en el mazo: distingue las dos copias de cada carta
  kind: Kind;
  color: PrismaColor | null; // null en los comodines
  number: number | null;
}

/**
 * Doble cara: la otra cara de una carta, la que ven los demás. No lleva el id de
 * la carta, sino un alias de la ronda (`key`) para seguirla en la mano.
 */
export interface Face {
  key?: number;
  kind: Kind;
  color: PrismaColor | null;
  number: number | null;
}

export interface PlayerInfo {
  seat: number;
  name: string;
  count: number; // cuántas cartas tiene
  score: number;
  said_last: boolean;
  vulnerable: boolean; // se quedó con una carta sin decir "¡Última!"
  is_human: boolean; // soy yo
  level: string;
  backs: Face[]; // Doble cara: la otra cara de sus cartas (nunca de las mías)
  out: boolean; // Sin tregua: eliminado de la ronda por desborde
  person?: boolean; // en una sala: lo juega una persona (yo u otra)
  gone?: boolean; // en una sala: esa persona se fue y ahora juega un bot en su sitio
}

export interface Legal {
  play: number[]; // ids de las cartas que puedo jugar
  draw: boolean;
  pass: boolean;
  choose_color: boolean;
  challenge: boolean;
  declare: boolean;
  catch: boolean;
  roulette: boolean; // Sin tregua: me han echado una Ruleta y elijo el color
}

export interface GameEvent {
  kind:
    | "deal"
    | "return"
    | "start"
    | "choose"
    | "skip"
    | "reverse"
    | "play"
    | "last"
    | "draw"
    | "pass"
    | "caught"
    | "challenge"
    | "reshuffle"
    | "blocked"
    | "round_over"
    // Doble cara
    | "eclipse"
    // Sin tregua
    | "skip_all"
    | "stack"
    | "sweep"
    | "reveal"
    | "swap"
    | "rotate"
    | "eliminated";
  seat: number | null;
  card: Card | null; // carta jugada o volteada
  // Robadas o repartidas: solo si son mías (las de la Ruleta y el Barrido, de
  // todos). Tras un Eclipse, un 7 o un 0: cómo me queda la mano.
  cards: Card[];
  count: number;
  color: PrismaColor | null;
  target: number | null;
  result: string;
  reason: string;
  // Doble cara: las caras que entran en las manos de los demás (o, tras un
  // Eclipse, todas), la carta que sale de la mano de otro y la cara de encima
  // del mazo. Tras un Eclipse, un 7 o un 0, cuántas cartas tiene cada uno.
  backs?: Record<string, Face[]>;
  key?: number | null;
  deck_back?: Face | null;
  counts?: number[];
}

export interface PrismaConfig {
  mode: Mode;
  bots: number;
  difficulty: string;
  challenge: boolean;
  scoring: boolean;
  target: number;
  stack_draw2: boolean;
  stack_draw4: boolean;
  player_name: string;
}

export interface GameState {
  mode: Mode;
  side: Side; // Doble cara: la cara que está en juego
  colors: PrismaColor[]; // los colores en juego (los de luz o los de sombra)
  deck_back: Face | null; // Doble cara: la cara que se ve encima del mazo
  pending_min: number; // Sin tregua: la carga mínima para responder a una acumulada
  aside_count: number; // Sin tregua: cartas apartadas de los eliminados
  phase: Phase;
  round_number: number;
  direction: 1 | -1;
  turn: number;
  dealer: number;
  color: PrismaColor | null;
  top: Card;
  discard_count: number;
  draw_count: number;
  pending_draw: number;
  players: PlayerInfo[];
  viewer_seat: number;
  hand: Card[];
  drawn: number | null; // la carta que acabo de robar y aún puedo jugar
  legal: Legal;
  winner: number | null;
  game_over: boolean;
  rules: {
    mode: Mode;
    challenge: boolean;
    stack_draw2: boolean;
    stack_draw4: boolean;
    scoring: boolean;
    target: number;
    hand_size: number;
  };
  events: GameEvent[];
  config: PrismaConfig;
  human_seat: number;
  // Solo en las salas:
  timer?: TurnTimer | null; // la cuenta atrás de la decisión en curso
  next_round_in?: number | null; // segundos hasta la ronda siguiente (jugando a puntos)
}

export interface Options {
  levels: { id: string; name: string }[];
  max_bots: number;
  defaults: PrismaConfig;
  fields: GameOption[];
}

export type ClientMessage =
  | { type: "new_game"; config: PrismaConfig }
  | { type: "play"; card: number; color?: PrismaColor; declare?: boolean; target?: number }
  | { type: "color"; color: PrismaColor }
  | { type: "roulette"; color: PrismaColor }
  | {
      type: "draw" | "pass" | "challenge" | "accept" | "last" | "catch" | "next_round" | "restart";
    };
