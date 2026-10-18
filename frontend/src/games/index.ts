// Mapa de juegos del frontend: el id de cada juego (el mismo que en el registro
// del servidor) con su página y su ícono. Añadir un juego es añadir aquí su
// página y su ícono, y su ficha en `backend/games/registry.py`: el menú no se
// toca.
//
// Las páginas se cargan solo al entrar en ellas (`lazy`), para que el menú
// abra rápido.

import { lazy, type ComponentType, type JSX, type LazyExoticComponent } from "react";
import { BlackjackIcon } from "./blackjack/icon";
import { PokerIcon } from "./poker/icon";
import { PrismaIcon } from "./prisma/icon";

export type GameIcon = (props: { className?: string }) => JSX.Element;

/** Página de cada juego que ya se puede jugar. */
export const GAME_PAGES: Record<string, LazyExoticComponent<ComponentType>> = {
  poker: lazy(() => import("./poker/PokerPage")),
  blackjack: lazy(() => import("./blackjack/BlackjackPage")),
};

/** Ícono de cada juego en el menú (también de los que aún son "Próximamente"). */
export const GAME_ICONS: Record<string, GameIcon> = {
  poker: PokerIcon,
  blackjack: BlackjackIcon,
  prisma: PrismaIcon,
};

/** ¿Tiene la web una página para este juego? */
export function hasPage(gameId: string): boolean {
  return Object.hasOwn(GAME_PAGES, gameId);
}
