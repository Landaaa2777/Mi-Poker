import type { TableView } from "../settings";

interface Props {
  view: TableView;
  onChange: (view: TableView) => void;
  className?: string;
}

const OPTIONS: { view: TableView; label: string; title: string }[] = [
  { view: "2d", label: "2D", title: "Mesa plana, vista desde arriba" },
  { view: "3d", label: "3D", title: "Mesa en perspectiva, con cartas y fichas en relieve" },
];

/** Interruptor de dos botones para elegir cómo se ven las mesas: 2D o 3D. */
export function ViewSwitch({ view, onChange, className = "" }: Props) {
  return (
    <div role="group" aria-label="Vista de la mesa" className={`flex rounded-button ${className}`}>
      {OPTIONS.map((option, index) => (
        <button
          key={option.view}
          type="button"
          aria-pressed={view === option.view}
          title={option.title}
          onClick={() => onChange(option.view)}
          className={`h-9 min-w-11 px-2.5 text-sm font-black tracking-wide ${view === option.view ? "btn-gold" : "btn-dark"} ${index === 0 ? "rounded-r-none" : "rounded-l-none"}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
