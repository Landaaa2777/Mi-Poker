// Opciones configurables de un juego, tal como las describe el servidor (ver
// backend/core/options.py). Con ellas se pinta el panel de opciones.

export type GameOption =
  | {
      key: string;
      type: "number";
      label: string;
      default: number;
      min: number | null;
      max: number | null;
      step: number;
      presets?: number[];
      help?: string;
    }
  | {
      key: string;
      type: "choice";
      label: string;
      default: string;
      choices: { value: string; label: string; description?: string }[];
      help?: string;
    }
  | { key: string; type: "toggle"; label: string; default: boolean; help?: string };

export type OptionValues = Record<string, number | string | boolean>;

/** Los valores por defecto de todas las opciones. */
export function defaultValues(fields: GameOption[]): OptionValues {
  return Object.fromEntries(fields.map((field) => [field.key, field.default]));
}

/**
 * El primer problema de un número fuera de sus límites, en una frase; o null.
 * `max` puede ser más estricto que el del servidor (por ejemplo, el saldo).
 */
export function numberProblem(field: GameOption, value: number, max?: number): string | null {
  if (field.type !== "number") return null;
  const top = Math.min(field.max ?? Infinity, max ?? Infinity);
  if (!Number.isFinite(value)) return `${field.label}: escribe un número.`;
  if (field.min !== null && value < field.min) return `${field.label}: como poco ${field.min}.`;
  if (value > top) return `${field.label}: como mucho ${top}.`;
  if (field.step > 1 && value % field.step !== 0) {
    return `${field.label}: va de ${field.step} en ${field.step}.`;
  }
  return null;
}
