import { cardLabel, isRed } from "../format";

interface Props {
  card?: string | null; // sin carta = boca abajo
  small?: boolean;
}

export function PlayingCard({ card, small }: Props) {
  const size = small ? "h-10 w-7 text-sm" : "h-14 w-10 text-lg";
  if (!card) {
    return (
      <span
        className={`${size} inline-block rounded border border-slate-500 bg-slate-600`}
        aria-label="Carta oculta"
      />
    );
  }
  const color = isRed(card) ? "text-red-600" : "text-slate-900";
  return (
    <span
      className={`${size} ${color} inline-flex items-center justify-center rounded border border-slate-300 bg-white font-bold`}
    >
      {cardLabel(card)}
    </span>
  );
}
