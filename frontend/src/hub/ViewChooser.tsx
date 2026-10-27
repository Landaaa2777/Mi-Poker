import type { TableView } from "../shared/settings";

// La primera vez, el menú pregunta cómo se quieren ver las mesas. Cada opción
// lleva un dibujo pequeño de la mesa: plana, vista desde arriba, o en perspectiva.

function FlatTable() {
  return (
    <svg viewBox="0 0 160 96" className="h-full w-full" aria-hidden>
      <rect x="10" y="12" width="140" height="72" rx="36" fill="#17804c" stroke="#f5c542" strokeWidth="3" />
      <ellipse cx="80" cy="48" rx="50" ry="22" fill="none" stroke="rgb(255 241 191 / 0.25)" strokeWidth="1.5" />
      {[52, 66, 80, 94, 108].map((x) => (
        <rect key={x} x={x - 5} y="40" width="10" height="15" rx="1.5" fill="#fdfbf5" />
      ))}
      <circle cx="80" cy="25" r="5" fill="#9b2a35" stroke="#fff1f2" strokeWidth="1.2" strokeDasharray="2 2" />
    </svg>
  );
}

function PerspectiveTable() {
  return (
    <svg viewBox="0 0 160 96" className="h-full w-full" aria-hidden>
      {/* Canto de la mesa y tapete en perspectiva: más estrecho al fondo. */}
      <path d="M8 66 Q8 88 40 88 H120 Q152 88 152 66 L136 26 Q132 14 112 14 H48 Q28 14 24 26 Z" fill="#3a1d0e" />
      <path d="M8 62 Q8 82 40 82 H120 Q152 82 152 62 L136 24 Q132 12 112 12 H48 Q28 12 24 24 Z" fill="#17804c" stroke="#f5c542" strokeWidth="3" />
      {/* Cartas tumbadas en el tapete, cada una con su sombra. */}
      {[50, 65, 80, 95, 110].map((x, index) => (
        <g key={x}>
          <path d={`M${x - 5} ${52} l2 -12 h8 l2 12 z`} fill="rgb(0 0 0 / 0.3)" transform="translate(1.5 2)" />
          <path d={`M${x - 5} ${52} l2 -12 h8 l2 12 z`} fill="#fdfbf5" transform={`rotate(${(index - 2) * 2} ${x} 46)`} />
        </g>
      ))}
      {/* Una pila de fichas con volumen. */}
      {[0, 1, 2, 3].map((level) => (
        <g key={level} transform={`translate(0 ${-level * 3})`}>
          <path d="M72 32 v3 a8 3.5 0 0 0 16 0 v-3 z" fill="#6b1420" />
          <ellipse cx="80" cy="32" rx="8" ry="3.5" fill="#9b2a35" stroke="#fff1f2" strokeWidth="0.8" strokeDasharray="1.6 1.6" />
        </g>
      ))}
    </svg>
  );
}

const OPTIONS: { view: TableView; title: string; text: string; Picture: () => React.JSX.Element }[] = [
  {
    view: "2d",
    title: "2D",
    text: "La mesa plana, vista desde arriba, como siempre.",
    Picture: FlatTable,
  },
  {
    view: "3d",
    title: "3D",
    text: "La mesa en perspectiva, con cartas y fichas en relieve que se mueven como las de verdad.",
    Picture: PerspectiveTable,
  },
];

/** Pregunta del menú: ¿mesas en 2D o en 3D? Se puede cambiar después en Ajustes o en la mesa. */
export function ViewChooser({ onChoose }: { onChoose: (view: TableView) => void }) {
  return (
    <section className="panel p-4 sm:p-5" aria-labelledby="view-chooser-title">
      <h2 id="view-chooser-title" className="gold-text font-display text-xl font-black">
        ¿Cómo quieres ver las mesas?
      </h2>
      <p className="mt-1 text-sm text-stone-300">
        Puedes cambiarlo cuando quieras en Ajustes o con el botón 2D/3D de la mesa.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {OPTIONS.map(({ view, title, text, Picture }) => (
          <button
            key={view}
            type="button"
            onClick={() => onChoose(view)}
            className="hub-card flex items-center gap-4 rounded-tile border border-amber-400/30 bg-black/30 p-3 text-left outline-none hover:border-amber-300/70 focus-visible:ring-4 focus-visible:ring-amber-300"
          >
            <span className="block h-20 w-32 shrink-0">
              <Picture />
            </span>
            <span>
              <span className="gold-text font-display text-2xl font-black">{title}</span>
              <span className="mt-0.5 block text-sm text-stone-300">{text}</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
