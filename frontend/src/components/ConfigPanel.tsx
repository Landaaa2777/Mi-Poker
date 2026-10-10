import { useState, type FormEvent } from "react";
import type { Options, TableConfig } from "../types";

interface Props {
  options: Options;
  initial: TableConfig;
  onStart: (config: TableConfig) => void;
  onCancel?: () => void;
}

const FIELD = "w-full rounded border border-slate-600 bg-slate-900 px-3 py-2";

/** Panel de configuración previo a la partida. Todas las fichas son virtuales. */
export function ConfigPanel({ options, initial, onStart, onCancel }: Props) {
  const [config, setConfig] = useState<TableConfig>(initial);

  function update<K extends keyof TableConfig>(key: K, value: TableConfig[K]) {
    setConfig((current) => ({ ...current, [key]: value }));
  }

  function number(key: "starting_stack" | "small_blind" | "big_blind", label: string) {
    return (
      <label className="block">
        <span className="mb-1 block text-sm text-slate-300">{label}</span>
        <input
          type="number"
          min={1}
          max={options.max_stack}
          step={1}
          required
          className={FIELD}
          value={config[key]}
          onChange={(event) => update(key, Math.floor(Number(event.target.value)))}
        />
      </label>
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
    <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-lg bg-slate-800 p-6">
      <h2 className="text-xl font-semibold">Nueva partida</h2>

      <label className="block">
        <span className="mb-1 block text-sm text-slate-300">Tu nombre</span>
        <input
          type="text"
          required
          maxLength={16}
          className={FIELD}
          value={config.player_name}
          onChange={(event) => update("player_name", event.target.value)}
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm text-slate-300">Número de bots: {config.bots}</span>
        <input
          type="range"
          min={1}
          max={options.max_bots}
          className="w-full"
          value={config.bots}
          onChange={(event) => update("bots", Number(event.target.value))}
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm text-slate-300">Dificultad de los bots</span>
        <select
          className={FIELD}
          value={config.difficulty}
          onChange={(event) => update("difficulty", event.target.value)}
        >
          {options.levels.map((level) => (
            <option key={level.id} value={level.id}>
              {level.name}
            </option>
          ))}
        </select>
      </label>

      {number("starting_stack", "Fichas iniciales (virtuales)")}
      <div className="grid grid-cols-2 gap-3">
        {number("small_blind", "Ciega pequeña")}
        {number("big_blind", "Ciega grande")}
      </div>

      {problem && <p className="text-sm text-amber-400">{problem}</p>}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={problem !== null}
          className="flex-1 rounded bg-emerald-600 px-4 py-2 font-semibold hover:bg-emerald-500 disabled:opacity-40"
        >
          Empezar
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded bg-slate-600 px-4 py-2 hover:bg-slate-500"
          >
            Volver a la mesa
          </button>
        )}
      </div>
    </form>
  );
}
