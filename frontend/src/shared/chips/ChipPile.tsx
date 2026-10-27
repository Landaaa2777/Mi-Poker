import { useLayoutEffect, useRef, type CSSProperties } from "react";
import { EASE, animate, motion } from "../motion";
import { stacks, type Denomination } from "./chips";

// Pilas de fichas dibujadas con CSS: cada ficha es un cilindro (canto con sus
// marcas y cara de arriba con su anillo), y las fichas se apilan una encima de
// otra. Cómo de inclinada se ve la cara de arriba depende de la vista: en 2D
// casi de lado; en 3D, como se ve la mesa (ver --chip-ratio en base.css).

const SPREAD = 0.8; // separación entre pilas, en diámetros de ficha

interface Props {
  chips: readonly Denomination[];
  pile: string; // nombre de la pila, para que las animaciones la encuentren
  size?: number; // diámetro de cada ficha, en px
  tallest?: number; // fichas como mucho por pila
  still?: boolean; // decorado: sus fichas nunca caen (la bandeja del crupier)
}

/** Una ficha. Al aparecer en mitad de una jugada, cae sobre su pila cuando le llega su turno. */
function Chip({ value, level, still }: { value: Denomination; level: number; still: boolean }) {
  const chip = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const landing = motion.chipLanding;
    if (still || !motion.enabled || landing === null || !chip.current) return;
    animate(
      chip.current,
      [
        { transform: "translateY(-16px) scale(1.04)", opacity: 0 },
        { transform: "translateY(-16px) scale(1.04)", opacity: 1, offset: 0.15 },
        { transform: "translateY(1.5px) scale(1, 0.96)", opacity: 1, offset: 0.7 },
        { transform: "translateY(0px) scale(1)", opacity: 1 },
      ],
      { duration: 240, delay: landing + level * 22, fill: "backwards", easing: EASE.out },
    );
    // Solo al aparecer.
  }, []);
  return <span ref={chip} className="chip" data-v={value} style={{ "--i": level } as CSSProperties} />;
}

/** Las fichas de una apuesta o del bote, en pilas por valor. */
export function ChipPile({ chips, pile, size = 24, tallest = 8, still = false }: Props) {
  const columns = stacks(chips, tallest);
  const highest = Math.max(1, ...columns.map((column) => column.count));
  return (
    <span
      className="chip-pile"
      data-pile={pile}
      style={
        {
          "--chip-d": `${size}px`,
          width: size * (1 + SPREAD * Math.max(0, columns.length - 1)),
          height: `calc(var(--chip-d) * var(--chip-ratio) + ${highest} * var(--chip-t))`,
        } as CSSProperties
      }
      aria-hidden
    >
      {columns.map((column, index) => (
        <span
          key={`${column.value}-${column.first}`}
          className="chip-stack"
          style={{ left: index * size * SPREAD, zIndex: index % 2 === 0 ? 1 : 2 }}
        >
          <span className="chip-shadow" />
          {Array.from({ length: column.count }, (_, level) => (
            <Chip key={column.first + level} value={column.value} level={level} still={still} />
          ))}
        </span>
      ))}
    </span>
  );
}
