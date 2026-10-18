import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { cardName } from "../cardArt";
import { PrismaCard } from "../PrismaCard";
import type { Card } from "../types";

interface Props {
  cards: Card[];
  playable: number[]; // ids de las que puedo jugar ahora
  drawn: number | null; // la que acabo de robar (se resalta)
  disabled: boolean;
  onPlay: (card: Card) => void;
}

const MAX_GAP = 8; // separación entre cartas cuando caben todas sin solaparse

/**
 * Mi mano, en grande y debajo de la mesa. Si no caben, las cartas se solapan.
 * Las que se pueden jugar se levantan un poco; las demás se apagan. Cada carta
 * es un botón: se juega con un clic, o con el teclado (Tab y Enter).
 */
export function Hand({ cards, playable, drawn, disabled, onPlay }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);

  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const update = () => setWidth(element.clientWidth);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const card = width < 520 ? 62 : 84; // ancho de cada carta
  const space = width - 24;
  const step = cards.length > 1 ? Math.min(card + MAX_GAP, (space - card) / (cards.length - 1)) : 0;

  return (
    <section className="panel px-3 pb-3 pt-6" aria-label="Tus cartas">
      <div
        ref={box}
        data-zone="prisma-hand"
        className="flex justify-center"
        style={{ "--card-w": `${card}px`, minHeight: card * 1.4 + 8 } as CSSProperties}
      >
        {cards.map((item, index) => {
          const canPlay = !disabled && playable.includes(item.id);
          return (
            <button
              key={item.id}
              type="button"
              disabled={!canPlay}
              onClick={() => onPlay(item)}
              className={`hand-card relative rounded-lg outline-none focus-visible:ring-4 focus-visible:ring-amber-300 ${canPlay ? "playable" : "opacity-60 saturate-50"} ${item.id === drawn ? "just-drawn" : ""}`}
              style={{ marginLeft: index === 0 ? 0 : step - card, zIndex: index }}
              aria-label={canPlay ? `Jugar ${cardName(item)}` : `${cardName(item)} (ahora no se puede jugar)`}
            >
              <PrismaCard card={item} enter="deal" />
            </button>
          );
        })}
        {cards.length === 0 && <p className="self-center text-sm text-stone-400">Sin cartas</p>}
      </div>
    </section>
  );
}
