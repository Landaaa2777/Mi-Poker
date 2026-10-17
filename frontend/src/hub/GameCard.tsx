import { Link } from "react-router";
import { GAME_ICONS } from "../games";
import { COMING_SOON_ICONS, GenericGameIcon } from "./icons";
import { playersLabel, type CardState, type GameEntry } from "./hub";

interface Props {
  game: GameEntry;
  state: CardState;
}

const ACTION: Record<Exclude<CardState, "soon">, string> = {
  play: "Jugar",
  continue: "Continuar partida",
};

/** Tarjeta grande de un juego en el menú. Las de "Próximamente" no se pueden pulsar. */
export function GameCard({ game, state }: Props) {
  const Icon = GAME_ICONS[game.id] ?? COMING_SOON_ICONS[game.id] ?? GenericGameIcon;
  const players = playersLabel(game);
  const soon = state === "soon";

  const body = (
    <>
      <div
        className={`relative flex h-32 items-center justify-center overflow-hidden rounded-xl ${
          soon ? "bg-black/35" : "felt"
        }`}
      >
        <Icon
          className={`h-20 w-20 drop-shadow-[0_3px_6px_rgb(0_0_0/0.45)] ${
            soon ? "text-stone-400 grayscale" : "text-gold"
          }`}
        />
        {state === "continue" && (
          <span className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-gold">
            Partida a medias
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className={`font-display text-xl font-black ${soon ? "text-stone-300" : "gold-text"}`}>
          {game.name}
        </h2>
        {players && <span className="text-xs font-semibold text-amber-100/60">{players}</span>}
      </div>
      <p className="text-sm text-stone-300">{game.description}</p>
      <div className="mt-auto pt-1">
        {soon ? (
          <span className="inline-flex h-10 w-full items-center justify-center rounded-button border border-dashed border-amber-400/30 text-sm font-bold uppercase tracking-wider text-amber-100/50">
            Próximamente
          </span>
        ) : (
          <span
            className={`flex h-10 w-full items-center justify-center text-sm ${
              state === "continue" ? "btn-green" : "btn-gold"
            }`}
          >
            {ACTION[state]}
          </span>
        )}
      </div>
    </>
  );

  if (soon) {
    return (
      <div aria-disabled="true" className="panel flex h-full flex-col gap-3 p-4 opacity-70">
        {body}
      </div>
    );
  }
  return (
    <Link
      to={`/${game.id}`}
      className="hub-card panel flex h-full flex-col gap-3 p-4 outline-none focus-visible:ring-4 focus-visible:ring-amber-300/70"
    >
      {body}
    </Link>
  );
}
