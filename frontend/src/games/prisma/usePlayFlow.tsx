// Jugar una carta, con lo que haga falta preguntar antes: el color de un
// comodín o, en Sin tregua, con quién cambias la mano al jugar un 7. Y las
// decisiones que llegan del servidor: el color al empezar la ronda (o tras un
// Eclipse que deja arriba un comodín) y el de la Ruleta que te han echado.
// Lo usan igual la partida contra bots y la mesa de una sala.

import { useState, type ReactNode } from "react";
import { KIND_NAMES } from "./cardArt";
import { ColorPicker } from "./components/ColorPicker";
import { TargetPicker } from "./components/TargetPicker";
import type { Card, ClientMessage, GameState } from "./types";

type Pending = { kind: "color"; card: Card } | { kind: "target"; card: Card };

/** ¿Hay que decir con quién se cambia la mano al jugar esta carta? */
export function needsTarget(state: GameState, card: Card): boolean {
  return state.mode === "sin_tregua" && card.kind === "number" && card.number === 7 && state.hand.length > 1;
}

/** ¿Hay que elegir color al jugar esta carta? (La Ruleta no: lo elige quien la sufre.) */
export function needsColor(card: Card): boolean {
  return card.color === null && card.kind !== "ruleta";
}

export function usePlayFlow(
  state: GameState | null,
  settled: boolean,
  send: (message: ClientMessage) => void,
): { play: (card: Card) => void; dialogs: ReactNode } {
  const [pending, setPending] = useState<Pending | null>(null);
  const legal = state?.legal;
  const mustChoose = settled && legal?.choose_color === true;
  const roulette = settled && legal?.roulette === true;

  function play(card: Card) {
    if (!state) return;
    if (needsColor(card)) setPending({ kind: "color", card });
    else if (needsTarget(state, card)) setPending({ kind: "target", card });
    else send({ type: "play", card: card.id });
  }

  let dialogs: ReactNode = null;
  if (state && pending?.kind === "color") {
    const card = pending.card;
    dialogs = (
      <ColorPicker
        title={`¿Qué color eliges con el ${KIND_NAMES[card.kind as keyof typeof KIND_NAMES]}?`}
        hint={card.kind === "sabueso" ? "El siguiente robará hasta sacar una carta de ese color." : undefined}
        colors={state.colors}
        onPick={(color) => {
          send({ type: "play", card: card.id, color });
          setPending(null);
        }}
        onCancel={() => setPending(null)}
      />
    );
  } else if (state && pending?.kind === "target") {
    const card = pending.card;
    const rivals = state.players.filter((player) => player.seat !== state.human_seat && !player.out);
    dialogs = (
      <TargetPicker
        rivals={rivals}
        onPick={(target) => {
          send({ type: "play", card: card.id, target });
          setPending(null);
        }}
        onCancel={() => setPending(null)}
      />
    );
  } else if (state && roulette) {
    dialogs = (
      <ColorPicker
        title="¡Te han echado una Ruleta! Elige un color"
        hint="Destaparás cartas del mazo hasta que salga ese color, y te las quedas todas."
        colors={state.colors}
        onPick={(color) => send({ type: "roulette", color })}
      />
    );
  } else if (state && mustChoose) {
    const eclipse = state.events.at(-1)?.kind === "eclipse";
    dialogs = (
      <ColorPicker
        title={eclipse ? "El Eclipse deja arriba un comodín: elige el color" : "La ronda empieza con un Camaleón: elige el color"}
        colors={state.colors}
        onPick={(color) => send({ type: "color", color })}
      />
    );
  }
  return { play, dialogs };
}
