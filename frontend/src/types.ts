// Formas de los mensajes del servidor (ver backend/server/protocol.py).

export type ActionName = "fold" | "check" | "call" | "raise" | "all_in";
export type SeatStatus = "active" | "folded" | "all_in" | "out";

export interface Seat {
  seat: number;
  name: string;
  stack: number;
  bet: number;
  contributed: number;
  status: SeatStatus;
  hole_cards: string[] | null; // null = ocultas
  is_human: boolean;
  style: string;
  level: string;
}

export interface HandEvent {
  kind: "small_blind" | "big_blind" | "action" | "board" | "refund" | "show" | "win";
  seat: number | null;
  amount: number;
  action: string;
  cards: string[];
  all_in: boolean;
}

export interface LegalActions {
  can_check: boolean;
  call_amount: number;
  can_raise: boolean;
  min_raise_to: number;
  max_raise_to: number;
}

export interface PotAward {
  amount: number;
  eligible: number[];
  winners: number[];
  payouts: Record<string, number>;
}

export interface HandResult {
  showdown: boolean;
  board: string[];
  awards: PotAward[];
  payouts: Record<string, number>;
  shown_hands: Record<string, string[]>;
  hand_names: Record<string, string>;
}

export interface TableConfig {
  bots: number;
  difficulty: string;
  starting_stack: number;
  small_blind: number;
  big_blind: number;
  player_name: string;
}

export interface GameState {
  hand_number: number;
  phase: string | null;
  button_seat: number | null;
  small_blind: number;
  big_blind: number;
  board: string[];
  pot: number;
  current_bet: number;
  to_act_seat: number | null;
  seats: Seat[];
  events: HandEvent[];
  result: HandResult | null;
  viewer_seat: number;
  hole_cards: string[];
  legal_actions: LegalActions | null;
  notice: string;
  config: TableConfig;
  hand_in_progress: boolean;
  human_out: boolean;
  game_over: boolean;
  winner_seat: number | null;
}

export interface Options {
  notice: string;
  levels: { id: string; name: string }[];
  max_bots: number;
  max_stack: number;
  defaults: TableConfig;
}

export type ServerMessage =
  | { type: "hello"; options: Options; state: GameState | null }
  | { type: "state"; state: GameState | null }
  | { type: "error"; message: string };

export type ClientMessage =
  | { type: "new_game"; config: TableConfig }
  | { type: "action"; action: ActionName; amount?: number }
  | { type: "next_hand" }
  | { type: "restart" };
