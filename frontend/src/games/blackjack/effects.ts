// Lo que acompaña a cada paso de la ronda: el movimiento de las cartas y de
// las fichas, y su sonido.

import { audio } from "../../shared/audio/engine";
import type { EffectName } from "../../shared/audio/effects";
import { total, type Denomination } from "../../shared/chips/chips";
import { flyChips, slidePile } from "../../shared/chips/flight";
import { motion } from "../../shared/motion";
import type { PlaybackListener } from "../../shared/timeline/playback";
import { seatChips } from "./chips";
import type { Frame, Step } from "./timeline";

const CHIP_SIZE = 28; // las fichas que vuelan

function find(selector: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(selector);
}

/** Las fichas de `after` que no estaban en `before` (las de arriba de la pila). */
function added(before: readonly Denomination[], after: readonly Denomination[]): Denomination[] {
  return after.slice(before.length);
}

/**
 * Las fichas que se mueven entre lo dibujado (`before`) y el paso que va a
 * dibujarse: apuestas a su círculo, pagos desde la bandeja del crupier, lo
 * perdido a la bandeja y, al empezar otra ronda, lo que queda a cada jugador.
 * Devuelve cuándo llegan a su pila (ms), o null si no se mueve nada.
 */
export function moveChips(before: Frame, step: Step): number | null {
  const rack = find('[data-pile="rack"]');
  let landing: number | null = null;
  const land = (ms: number) => (landing = Math.max(landing ?? 0, ms));

  step.frame.seats.forEach((seat, index) => {
    const previous = before.seats[index];
    if (!previous || previous.seat !== seat.seat) return;
    const plaque = find(`[data-seat="${seat.seat}"] [data-anchor="chips"]`);
    if (!plaque || !rack) return;
    const was = seatChips(before, previous);
    const now = seatChips(step.frame, seat);

    was.hands.forEach((chips, hand) => {
      if (step.kind !== "round") return;
      // Ronda nueva: lo que quedaba en la mesa (apuestas que no se perdieron y pagos) vuelve al jugador.
      for (const kind of ["bet", "win"]) {
        const pile = find(`[data-pile="bj-${kind}-${seat.seat}-${hand}-chips"]`);
        if (pile && (kind === "bet" ? chips.bet : chips.win).length > 0) slidePile(pile, plaque);
      }
    });

    now.hands.forEach((chips, hand) => {
      const old = was.hands[hand] ?? { bet: [], win: [] };
      const spot = find(`[data-pile="bj-bet-${seat.seat}-${hand}"]`);
      const winSpot = find(`[data-pile="bj-win-${seat.seat}-${hand}"]`);
      if (!spot || !winSpot) return;
      if (total(chips.bet) > total(old.bet)) {
        // Apuesta, doble o división: sus fichas van de su placa al círculo.
        land(flyChips(plaque, spot, added(old.bet, chips.bet), CHIP_SIZE));
      } else if (total(chips.bet) < total(old.bet)) {
        // Pierde (o se rinde): el crupier se lleva lo apostado a su bandeja.
        const pile = find(`[data-pile="bj-bet-${seat.seat}-${hand}-chips"]`);
        if (chips.bet.length === 0 && pile) slidePile(pile, rack);
        else flyChips(spot, rack, old.bet.slice(chips.bet.length), CHIP_SIZE);
      }
      // Gana: el crupier paga desde su bandeja, al lado de la apuesta.
      if (total(chips.win) > total(old.win)) land(flyChips(rack, winSpot, added(old.win, chips.win), CHIP_SIZE));
    });

    const insurance = find(`[data-pile="bj-ins-${seat.seat}"]`);
    if (!insurance) return;
    if (total(now.insurance) > total(was.insurance)) {
      land(flyChips(plaque, insurance, now.insurance, CHIP_SIZE));
    } else if (total(now.insurance) < total(was.insurance)) {
      const pile = find(`[data-pile="bj-ins-${seat.seat}-chips"]`);
      const paid = step.kind === "event" && step.event.kind === "insurance_paid";
      // Si el crupier tenía blackjack, el seguro cobra 2 a 1 y vuelve con su premio; si no, se pierde.
      if (pile) slidePile(pile, paid ? plaque : rack);
      if (paid) flyChips(rack, plaque, was.insurance.concat(was.insurance), CHIP_SIZE);
    }
  });
  return landing;
}

/** El sonido de un paso, si tiene. `me` es mi asiento. */
export function soundFor(step: Step, me: number): EffectName | null {
  switch (step.kind) {
    case "card":
      return "deal";
    case "reveal":
      return "flip";
    case "event": {
      const { kind, action, seat, result } = step.event;
      if (kind === "bet" || kind === "insurance" || kind === "split") return "chips";
      if (kind === "action") {
        if (action === "stand") return "check";
        if (action === "double") return "chips";
        if (action === "surrender") return "fold";
        return null; // pedir suena con la carta que llega
      }
      if (kind === "settle" && seat === me && (result === "win" || result === "blackjack")) return "win";
      if (kind === "shuffle") return "select";
      return null;
    }
    default:
      return null;
  }
}

/** Animaciones y sonido de la mesa de blackjack, enganchados a la cola de reproducción. */
export function tableEffects(me: () => number): PlaybackListener<Step> {
  let shown: Frame | null = null; // lo último que se ha dibujado, para ver qué cambia en cada paso
  return {
    onStep(step, speed) {
      // Las cartas leen esto al aparecer: vuelan desde el zapato, y al destapar se voltean.
      motion.entering = step.kind === "card" ? "deal" : null;
      motion.revealing = step.kind === "reveal";
      motion.speed = speed;
      // Y las fichas que llegan a una pila caen cuando llegan las que vuelan.
      motion.chipLanding = motion.enabled && shown ? (moveChips(shown, step) ?? 0) : 0;
      shown = step.frame;
      const sound = soundFor(step, me());
      if (sound) audio.play(sound);
    },
    onJump() {
      motion.entering = null;
      motion.revealing = false;
      motion.speed = 1;
      motion.chipLanding = null;
      shown = null;
      document.querySelector('[data-zone="fx"]')?.replaceChildren();
    },
  };
}
