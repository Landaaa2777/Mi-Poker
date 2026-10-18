import { useEffect, useState } from "react";
import { formatChips } from "../../../shared/format";
import { ACTION_LABEL, handProfit } from "../describe";
import type { ActionName, GameState } from "../types";

// Fichas para apostar: cada una suma su valor a la apuesta. Van de 10 en 10.
const CHIPS = [
  { value: 10, color: "#9b2a35" },
  { value: 50, color: "#2c7a50" },
  { value: 100, color: "#1c1c22" },
  { value: 500, color: "#6d3fb3" },
];

// Cada jugada con su color de botón: pedir en verde, plantarse en rojo.
const ACTION_STYLE: Record<ActionName, string> = {
  hit: "btn-green",
  stand: "btn-red",
  double: "btn-gold",
  split: "btn-gold",
  surrender: "btn-dark",
};
const ACTION_ORDER: ActionName[] = ["hit", "stand", "double", "split", "surrender"];

function ChipButton({ value, color, disabled, onClick }: { value: number; color: string; disabled: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-label={`Añadir ${value} a la apuesta`}
      className="chip-button relative flex h-14 w-14 items-center justify-center rounded-full text-sm font-black text-white shadow-lg disabled:opacity-35"
      style={{ background: color }}
    >
      <span className="absolute inset-1 rounded-full border-[3px] border-dashed border-white/70" />
      <span className="relative">{value}</span>
    </button>
  );
}

interface BetProps {
  state: GameState;
  lastBet: number;
  disabled: boolean;
  onBet: (amount: number) => void;
}

/** Apostar: fichas que suman, borrar y repartir. Empieza con la última apuesta. */
export function BetControls({ state, lastBet, disabled, onBet }: BetProps) {
  const { min_bet: low, max_bet: high, bet_step: step } = state.rules;
  const stack = state.seats[state.human_seat].stack;
  const top = Math.min(high, stack - (stack % step));
  const [bet, setBet] = useState(() => Math.min(Math.max(lastBet, low), top));
  useEffect(() => setBet((current) => Math.min(current, top)), [top]);
  const valid = bet >= low && bet <= top && bet % step === 0;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-bold uppercase tracking-[0.16em] text-amber-200/75">Tu apuesta</div>
          <div className="text-3xl font-black tabular-nums text-amber-200">{formatChips(bet)}</div>
          <div className="text-xs text-stone-400">
            Entre {formatChips(low)} y {formatChips(high)}, de {step} en {step}
          </div>
        </div>
        <div className="flex gap-2">
          {CHIPS.filter((chip) => chip.value <= high).map((chip) => (
            <ChipButton
              key={chip.value}
              value={chip.value}
              color={chip.color}
              disabled={disabled || bet + chip.value > top}
              onClick={() => setBet((current) => Math.min(current + chip.value, top))}
            />
          ))}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-gold h-12 flex-1 px-5 text-base uppercase tracking-wide"
          disabled={disabled || !valid}
          onClick={() => onBet(bet)}
        >
          Repartir
        </button>
        <button type="button" className="btn-dark h-12 px-4 text-sm" disabled={disabled} onClick={() => setBet(low)}>
          Mínima
        </button>
        <button
          type="button"
          className="btn-dark h-12 px-4 text-sm"
          disabled={disabled}
          onClick={() => setBet((current) => Math.min(current * 2, top))}
        >
          ×2
        </button>
      </div>
    </div>
  );
}

interface ActionProps {
  legal: ActionName[];
  disabled: boolean;
  onAction: (action: ActionName) => void;
}

/** Las jugadas que se pueden hacer ahora con la mano en juego. */
export function ActionControls({ legal, disabled, onAction }: ActionProps) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {ACTION_ORDER.filter((action) => legal.includes(action)).map((action) => (
        <button
          key={action}
          type="button"
          className={`${ACTION_STYLE[action]} h-14 px-4 text-base uppercase tracking-wide ${action === "hit" || action === "stand" ? "sm:col-span-1" : ""}`}
          disabled={disabled}
          onClick={() => onAction(action)}
        >
          {ACTION_LABEL[action]}
        </button>
      ))}
    </div>
  );
}

interface InsuranceProps {
  cost: number;
  disabled: boolean;
  onDecide: (take: boolean) => void;
}

/** El crupier enseña un As: ¿seguro? */
export function InsurancePrompt({ cost, disabled, onDecide }: InsuranceProps) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-amber-100">
        El crupier enseña un As. ¿Te aseguras por <strong>{formatChips(cost)}</strong> fichas? Si
        tiene blackjack, el seguro paga 2 a 1.
      </p>
      <div className="flex gap-2">
        <button type="button" className="btn-gold h-12 flex-1 px-4" disabled={disabled} onClick={() => onDecide(true)}>
          Asegurarme
        </button>
        <button type="button" className="btn-dark h-12 flex-1 px-4" disabled={disabled} onClick={() => onDecide(false)}>
          Sin seguro
        </button>
      </div>
    </div>
  );
}

/** Cómo me ha ido en la ronda que acaba de terminar, en una línea. */
export function RoundSummary({ state }: { state: GameState }) {
  const hands = state.seats[state.human_seat].hands;
  if (hands.length === 0 || hands.some((hand) => hand.result === null)) return null;
  const profit = hands.reduce((sum, hand) => sum + handProfit(hand), 0);
  const text =
    profit > 0 ? `Ganas ${formatChips(profit)} fichas` : profit < 0 ? `Pierdes ${formatChips(-profit)} fichas` : "Recuperas tu apuesta";
  return (
    <p
      className={`pop-in rounded-lg px-3 py-2 text-center text-sm font-bold ${profit > 0 ? "bg-emerald-900/60 text-emerald-100" : profit < 0 ? "bg-black/40 text-rose-200" : "bg-white/10 text-stone-100"}`}
    >
      {text}
    </p>
  );
}
