// Formas de los mensajes de Prisma (ver backend/games/prisma/protocol.py).

import type { GameOption } from "../../shared/options";
import type { PrismaColor } from "./shapes";
import type { TurnTimer } from "../../shared/room";

export type Kind = "number" | "pausa" | "remolino" | "carga" | "camaleon" | "camaleon4";
export type Phase = "choose_color" | "playing" | "challenge" | "round_over";

export interface Card {
  id: number; // único en el mazo: distingue las dos copias de cada carta
  kind: Kind;
  color: PrismaColor | null; // null en los comodines
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
    | "round_over";
  seat: number | null;
  card: Card | null; // carta jugada o volteada
  cards: Card[]; // robadas o repartidas: solo si son mías
  count: number;
  color: PrismaColor | null;
  target: number | null;
  result: string;
  reason: string;
}

export interface PrismaConfig {
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
  | { type: "play"; card: number; color?: PrismaColor; declare?: boolean }
  | { type: "color"; color: PrismaColor }
  | {
      type: "draw" | "pass" | "challenge" | "accept" | "last" | "catch" | "next_round" | "restart";
    };
