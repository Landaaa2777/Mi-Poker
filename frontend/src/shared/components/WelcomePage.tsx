import { useDocumentTitle } from "../useDocumentTitle";
import { Emblem } from "./Emblem";
import { SignInPanel } from "./SignInPanel";

const PERKS = [
  "Poker Texas Hold'em, blackjack y Prisma, el juego de descarte.",
  "Empiezas con 10.000 fichas virtuales.",
  "Tu nombre de usuario es tu nombre en todas las mesas.",
];

/** Lo que se ve sin sesión, en cualquier dirección: hace falta una cuenta para jugar. */
export function WelcomePage({ onSignedIn }: { onSignedIn: () => void }) {
  useDocumentTitle("mi-poker · Entra para jugar");
  return (
    <div className="grid items-start gap-gutter lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <section className="felt rim relative overflow-hidden rounded-[1.6rem] px-5 py-6 sm:px-8 sm:py-8">
        <div className="flex items-center gap-4 sm:gap-6">
          <Emblem className="h-16 w-16 shrink-0 text-amber-300 drop-shadow-[0_4px_10px_rgb(0_0_0/0.5)] sm:h-20 sm:w-20" />
          <div>
            <h1 className="gold-text font-display text-3xl font-black tracking-tight sm:text-4xl">
              Siéntate a la mesa
            </h1>
            <p className="mt-1 text-sm text-emerald-50/85 sm:text-base">
              Juegos de cartas con fichas virtuales.
            </p>
          </div>
        </div>
        <ul className="mt-6 space-y-2.5 text-sm text-emerald-50/90 sm:text-base">
          {PERKS.map((perk) => (
            <li key={perk} className="flex gap-3">
              <span aria-hidden className="mt-[0.45em] h-2 w-2 shrink-0 rotate-45 bg-amber-300" />
              {perk}
            </li>
          ))}
        </ul>
      </section>
      <SignInPanel onSignedIn={onSignedIn} />
    </div>
  );
}
