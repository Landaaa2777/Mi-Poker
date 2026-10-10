import { useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import type { Options, TableConfig } from "../types";
import { Emblem } from "./Emblem";
import { PlayingCard } from "./PlayingCard";

interface Props {
  options: Options;
  initial: TableConfig;
  onStart: (config: TableConfig) => void;
  onCancel?: () => void; // hay una partida en curso a la que se puede volver
}

// Cómo juega cada nivel, en una frase. Los niveles en sí los define el servidor.
const LEVEL_BLURB: Record<string, string> = {
  easy: "Juega casi todas las manos y paga de más. Ideal para empezar.",
  medium: "Elige sus manos y respeta las apuestas grandes.",
  hard: "Calcula sus probabilidades, varía sus apuestas y a veces farolea.",
  expert: "Además observa cómo juegas y se adapta a ti.",
};

const STACK_PRESETS = [500, 1000, 2000, 5000];
const BLIND_PRESETS: [number, number][] = [
  [5, 10],
  [10, 20],
  [25, 50],
  [50, 100],
];

const INPUT =
  "w-full rounded-lg border border-white/15 bg-black/30 px-3 py-2 outline-none focus:border-amber-400";
const CHOICE = "rounded-lg border px-3 py-2 text-sm font-semibold";
const CHOSEN = "border-amber-400 bg-amber-400 text-slate-900";
const NOT_CHOSEN = "border-white/15 bg-white/5 hover:bg-white/10";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-xs font-bold uppercase tracking-[0.16em] text-slate-400">
        {label}
      </div>
      {children}
    </div>
  );
}

/** Pantalla de inicio: presentación del juego y configuración de la partida. */
export function StartScreen({ options, initial, onStart, onCancel }: Props) {
  const [config, setConfig] = useState<TableConfig>(initial);

  function update(changes: Partial<TableConfig>) {
    setConfig((current) => ({ ...current, ...changes }));
  }

  function numberInput(key: "starting_stack" | "small_blind" | "big_blind", label: string) {
    return (
      <input
        type="number"
        min={1}
        max={options.max_stack}
        step={1}
        required
        aria-label={label}
        title={label}
        className={`${INPUT} tabular-nums`}
        value={config[key]}
        onChange={(event) => update({ [key]: Math.floor(Number(event.target.value)) })}
      />
    );
  }

  const problem =
    config.small_blind > config.big_blind
      ? "La ciega pequeña no puede superar a la grande."
      : config.starting_stack < config.big_blind
        ? "Las fichas iniciales deben cubrir al menos la ciega grande."
        : null;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!problem) onStart(config);
  }

  return (
    <main className="felt relative mx-auto w-full max-w-4xl overflow-hidden rounded-[1.75rem] shadow-xl ring-1 ring-black/50">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_50%,rgb(0_0_0/0.4))]" />
      <div className="relative p-5 sm:p-8">
        <header className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Emblem className="h-16 w-16 shrink-0 text-amber-300 sm:h-20 sm:w-20" />
            <div>
              <h1 className="text-4xl font-black tracking-tight sm:text-5xl">
                mi<span className="text-amber-300">-</span>poker
              </h1>
              <p className="mt-1 text-emerald-50/85">Texas Hold&apos;em No-Limit contra bots</p>
            </div>
          </div>
          {/* Adorno: tres cartas en abanico. */}
          <div
            className="relative mr-6 hidden h-28 w-36 shrink-0 sm:block"
            style={{ "--card-w": "62px" } as CSSProperties}
            aria-hidden
          >
            <span className="absolute left-0 top-3 -rotate-[16deg]">
              <PlayingCard card={null} float={0.8} />
            </span>
            <span className="absolute left-9 top-0 -rotate-3">
              <PlayingCard card="As" interactive="tilt" float={1} />
            </span>
            <span className="absolute left-[4.5rem] top-2 rotate-[12deg]">
              <PlayingCard card="Kh" interactive="tilt" float={1} />
            </span>
          </div>
        </header>

        <form
          onSubmit={submit}
          className="mt-6 space-y-5 rounded-2xl bg-[#0b1122]/90 p-5 shadow-lg ring-1 ring-white/10 sm:p-6"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Tu nombre">
              <input
                type="text"
                required
                maxLength={16}
                className={INPUT}
                aria-label="Tu nombre"
                value={config.player_name}
                onChange={(event) => update({ player_name: event.target.value })}
              />
            </Field>
            <Field label="Rivales">
              <div className="grid grid-cols-5 gap-2" role="group" aria-label="Número de bots">
                {Array.from({ length: options.max_bots }, (_, index) => index + 1).map((bots) => (
                  <button
                    key={bots}
                    type="button"
                    aria-pressed={config.bots === bots}
                    className={`${CHOICE} tabular-nums ${config.bots === bots ? CHOSEN : NOT_CHOSEN}`}
                    onClick={() => update({ bots })}
                  >
                    {bots}
                  </button>
                ))}
              </div>
            </Field>
          </div>

          <Field label="Dificultad de los bots">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {options.levels.map((level) => {
                const chosen = config.difficulty === level.id;
                return (
                  <button
                    key={level.id}
                    type="button"
                    aria-pressed={chosen}
                    className={`rounded-xl border p-3 text-left ${chosen ? "border-amber-400 bg-amber-400/15" : NOT_CHOSEN}`}
                    onClick={() => update({ difficulty: level.id })}
                  >
                    <div className={`font-bold ${chosen ? "text-amber-300" : ""}`}>{level.name}</div>
                    <div className="mt-0.5 text-xs leading-snug text-slate-300">
                      {LEVEL_BLURB[level.id] ?? ""}
                    </div>
                  </button>
                );
              })}
            </div>
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Fichas iniciales (virtuales)">
              <div className="mb-2 grid grid-cols-4 gap-2">
                {STACK_PRESETS.map((stack) => (
                  <button
                    key={stack}
                    type="button"
                    className={`${CHOICE} tabular-nums ${config.starting_stack === stack ? CHOSEN : NOT_CHOSEN}`}
                    onClick={() => update({ starting_stack: stack })}
                  >
                    {stack}
                  </button>
                ))}
              </div>
              {numberInput("starting_stack", "Fichas iniciales")}
            </Field>
            <Field label="Ciegas (pequeña / grande)">
              <div className="mb-2 grid grid-cols-4 gap-2">
                {BLIND_PRESETS.map(([small, big]) => {
                  const chosen = config.small_blind === small && config.big_blind === big;
                  return (
                    <button
                      key={big}
                      type="button"
                      className={`${CHOICE} tabular-nums ${chosen ? CHOSEN : NOT_CHOSEN}`}
                      onClick={() => update({ small_blind: small, big_blind: big })}
                    >
                      {small}/{big}
                    </button>
                  );
                })}
              </div>
              <div className="grid grid-cols-2 gap-2">
                {numberInput("small_blind", "Ciega pequeña")}
                {numberInput("big_blind", "Ciega grande")}
              </div>
            </Field>
          </div>

          {problem && <p className="text-sm font-semibold text-amber-300">{problem}</p>}

          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={problem !== null}
              className="h-14 flex-1 rounded-xl bg-amber-400 px-6 text-lg font-black uppercase tracking-wide text-slate-900 shadow-md hover:bg-amber-300 disabled:opacity-40"
            >
              Empezar partida
            </button>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="h-14 rounded-xl bg-slate-700 px-5 font-semibold hover:bg-slate-600"
              >
                Volver a la mesa
              </button>
            )}
          </div>
        </form>

        <p className="mt-4 text-center text-sm text-emerald-50/85">
          <strong>Solo para entretenimiento. Sin dinero real.</strong> Las fichas son virtuales y
          no tienen valor fuera del juego.
        </p>
      </div>
    </main>
  );
}
