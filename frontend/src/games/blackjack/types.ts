// Formas de los mensajes del blackjack (ver backend/games/blackjack/protocol.py).

import type { GameOption } from "../../shared/options";

export type Phase = "betting" | "insurance" | "playing" | "complete";
export type ActionName = "hit" | "stand" | "double" | "split" | "surrender";
export type HandStatus = "playing" | "stood" | "bust" | "blackjack" | "surrendered";
export type HandResult = "win" | "blackjack" | "push" | "lose" | "surrender";

export interface Hand {
  cards: string[];
  bet: number;
  total: number;
  soft: boolean;
  status: HandStatus;
  result: HandResult | null;
  payout: number; // lo que se devuelve al pagar, apuesta incluida
  doubled: boolean;
  from_split: boolean;
}

export interface Seat {
  seat: number;
  name: string;
  stack: number;
  hands: Hand[]; // vacío si no juega esta ronda
  insurance: number;
  insurance_pending: boolean;
  can_bet: boolean;
  is_human: boolean;
  level: string;
}

/** Un suceso de la ronda. `card` es null para la carta tapada del crupier. */
export interface RoundEvent {
  kind:
    | "shuffle"
    | "bet"
    | "card"
    | "dealer_card"
    | "hole_card"
    | "insurance"
    | "peek"
    | "insurance_paid"
    | "action"
    | "split"
    | "reveal"
    | "settle";
  seat: number | null;
  hand: number | null;
  card: string | null;
  amount: number;
  action: string;
  result: string;
}

export interface Rules {
  min_bet: number;
  max_bet: number;
  bet_step: number;
  decks: number;
  dealer_hits_soft_17: boolean;
  surrender: boolean;
  max_hands: number;
  double_after_split: boolean;
}

export interface BlackjackConfig {
  bots: number;
  difficulty: string;
  starting_stack: number;
  min_bet: number;
  max_bet: number;
  dealer_hits_soft_17: boolean;
  surrender: boolean;
  player_name: string;
}

export interface GameState {
  phase: Phase;
  round_number: number;
  rules: Rules;
  dealer: { cards: (string | null)[]; total: number; soft: boolean; hole_hidden: boolean };
  seats: Seat[];
  to_act_seat: number | null;
  to_act_hand: number | null;
  viewer_seat: number;
  legal_actions: ActionName[] | null;
  insurance_offered: boolean;
  shoe: { remaining: number; total: number; cut_reached: boolean };
  events: RoundEvent[];
  config: BlackjackConfig;
  human_seat: number;
  round_in_progress: boolean;
  human_out: boolean;
  balance: number | null; // fichas de mi cuenta, contando las de la mesa; null si soy invitado
}

export interface Options {
  levels: { id: string; name: string }[];
  max_bots: number;
  max_stack: number;
  defaults: BlackjackConfig;
  fields: GameOption[];
}

export type ClientMessage =
  | { type: "new_game"; config: BlackjackConfig }
  | { type: "bet"; amount: number }
  | { type: "action"; action: ActionName }
  | { type: "insurance"; take: boolean }
  | { type: "restart" };
