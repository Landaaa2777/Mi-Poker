import { Link } from "react-router";
import type { SalaSummary } from "../salas/salas";
import { RoomsIcon } from "./icons";

/** La tarjeta de las salas con amigos en el menú: crear o entrar en una, o volver a la mía. */
export function RoomsCard({ mine }: { mine: SalaSummary | null }) {
  return (
    <Link
      to={mine ? `/sala/${mine.code}` : "/salas"}
      className="hub-card panel flex h-full flex-col gap-3 p-4 outline-none focus-visible:ring-4 focus-visible:ring-amber-300/70"
    >
      <div className="felt relative flex h-32 items-center justify-center overflow-hidden rounded-xl">
        <RoomsIcon className="h-20 w-20 text-gold drop-shadow-[0_3px_6px_rgb(0_0_0/0.45)]" />
        {mine && (
          <span className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-gold">
            {mine.status === "playing" ? "Partida en juego" : "Estás en una sala"}
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="gold-text font-display text-xl font-black">Salas con amigos</h2>
        <span className="text-xs font-semibold text-amber-100/60">2 a 6 personas</span>
      </div>
      <p className="text-sm text-stone-300">
        Poker, blackjack o Prisma con tus amigos: crea una sala y comparte el código o el enlace.
      </p>
      <div className="mt-auto pt-1">
        <span className={`flex h-10 w-full items-center justify-center text-sm ${mine ? "btn-green" : "btn-gold"}`}>
          {mine ? `Volver a la sala ${mine.code}` : "Crear o unirme"}
        </span>
      </div>
    </Link>
  );
}
