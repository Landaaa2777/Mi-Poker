import type { OptionValues, GameOption } from "../options";
import { CARD_CHOSEN, CHOICE, CHOSEN, Field, INPUT, NOT_CHOSEN } from "./form";

interface Props {
  fields: GameOption[]; // las opciones del juego, tal como las describe el servidor
  values: OptionValues;
  onChange: (changes: OptionValues) => void;
  /** Límites más estrictos que los del servidor, por ejemplo las fichas que tiene la cuenta. */
  maxFor?: Partial<Record<string, number>>;
  /** Etiquetas que cambian según la cuenta ("Fichas para la mesa (tienes 9.000)"). */
  labelFor?: Partial<Record<string, string>>;
}

/**
 * Panel de opciones de cualquier juego, construido con el esquema que da el
 * servidor. Cada tipo de opción tiene su forma de elegirse:
 * - número con pocos valores (como los bots): una fila de botones;
 * - número con valores típicos: botones rápidos y una casilla para escribir;
 * - elección con descripciones: tarjetas; sin descripciones, botones;
 * - sí/no: un interruptor.
 */
export function ConfigPanel({ fields, values, onChange, maxFor = {}, labelFor = {} }: Props) {
  // Las elecciones con descripción ocupan todo el ancho; el resto va de dos en dos.
  const wide = (field: GameOption) =>
    field.type === "choice" && field.choices.some((choice) => choice.description);

  return (
    <div className="grid gap-5 sm:grid-cols-2">
      {fields.map((field) => (
        <div key={field.key} className={wide(field) ? "sm:col-span-2" : ""}>
          <Field label={labelFor[field.key] ?? field.label}>
            <OptionInput
              field={field}
              value={values[field.key] ?? field.default}
              max={maxFor[field.key]}
              onChange={(value) => onChange({ [field.key]: value })}
            />
          </Field>
        </div>
      ))}
    </div>
  );
}

interface InputProps {
  field: GameOption;
  value: number | string | boolean;
  max?: number;
  onChange: (value: number | string | boolean) => void;
}

function OptionInput({ field, value, max, onChange }: InputProps) {
  if (field.type === "toggle") {
    const on = value === true;
    return (
      <button
        type="button"
        role="switch"
        aria-checked={on}
        className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left ${on ? CARD_CHOSEN : NOT_CHOSEN}`}
        onClick={() => onChange(!on)}
      >
        <span
          className={`relative h-6 w-11 shrink-0 rounded-full ${on ? "bg-amber-400" : "bg-white/15"}`}
          aria-hidden
        >
          <span
            className={`switch-knob absolute top-0.5 h-5 w-5 rounded-full bg-white shadow ${on ? "translate-x-5" : "translate-x-0.5"}`}
          />
        </span>
        <span>
          <span className={`block text-sm font-bold ${on ? "text-amber-300" : ""}`}>
            {on ? "Sí" : "No"}
          </span>
          {field.help && <span className="block text-xs leading-snug text-stone-300">{field.help}</span>}
        </span>
      </button>
    );
  }

  if (field.type === "choice") {
    const described = field.choices.some((choice) => choice.description);
    if (described) {
      return (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4" role="group" aria-label={field.label}>
          {field.choices.map((choice) => {
            const chosen = value === choice.value;
            return (
              <button
                key={choice.value}
                type="button"
                aria-pressed={chosen}
                className={`rounded-xl border p-3 text-left ${chosen ? CARD_CHOSEN : NOT_CHOSEN}`}
                onClick={() => onChange(choice.value)}
              >
                <div className={`font-bold ${chosen ? "text-amber-300" : ""}`}>{choice.label}</div>
                {choice.description && (
                  <div className="mt-0.5 text-xs leading-snug text-stone-300">{choice.description}</div>
                )}
              </button>
            );
          })}
        </div>
      );
    }
    return (
      <div className="flex flex-wrap gap-2" role="group" aria-label={field.label}>
        {field.choices.map((choice) => (
          <button
            key={choice.value}
            type="button"
            aria-pressed={value === choice.value}
            className={`${CHOICE} ${value === choice.value ? CHOSEN : NOT_CHOSEN}`}
            onClick={() => onChange(choice.value)}
          >
            {choice.label}
          </button>
        ))}
      </div>
    );
  }

  // Número.
  const low = field.min ?? 0;
  const high = Math.min(field.max ?? Infinity, max ?? Infinity);
  const few = field.step === 1 && field.max !== null && field.max - low <= 5;
  if (few) {
    const count = field.max! - low + 1;
    return (
      <div
        className="grid gap-2"
        style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
        role="group"
        aria-label={field.label}
      >
        {Array.from({ length: count }, (_, index) => low + index).map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={value === option}
            className={`${CHOICE} tabular-nums ${value === option ? CHOSEN : NOT_CHOSEN}`}
            onClick={() => onChange(option)}
          >
            {option}
          </button>
        ))}
      </div>
    );
  }
  return (
    <>
      {field.presets && (
        <div className="mb-2 grid grid-cols-4 gap-2">
          {field.presets.map((preset) => (
            <button
              key={preset}
              type="button"
              disabled={preset > high}
              aria-pressed={value === preset}
              className={`${CHOICE} tabular-nums disabled:opacity-35 ${value === preset ? CHOSEN : NOT_CHOSEN}`}
              onClick={() => onChange(preset)}
            >
              {preset}
            </button>
          ))}
        </div>
      )}
      <input
        type="number"
        min={low}
        max={Number.isFinite(high) ? high : undefined}
        step={field.step}
        required
        aria-label={field.label}
        className={`${INPUT} tabular-nums`}
        value={String(value)}
        onChange={(event) => onChange(Math.floor(Number(event.target.value)))}
      />
    </>
  );
}
