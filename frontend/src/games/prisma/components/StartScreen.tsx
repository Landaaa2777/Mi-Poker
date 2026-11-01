import { useState, type CSSProperties, type FormEvent } from "react";
import { ConfigPanel } from "../../../shared/components/ConfigPanel";
import { Field, INPUT } from "../../../shared/components/form";
import type { OptionValues } from "../../../shared/options";
import { CardFaceArt } from "../cardArt";
import { PrismaIcon } from "../icon";
import type { Card, Mode, Options, PrismaConfig } from "../types";

// Cartas de muestra para la cabecera, según el modo.
const SAMPLES: Record<Mode, { card: Card; dark?: boolean }[]> = {
  clasico: [
    { card: { id: 0, kind: "number", color: "halo", number: 7 } },
    { card: { id: 1, kind: "remolino", color: "cumbre", number: null } },
    { card: { id: 2, kind: "camaleon4", color: null, number: null } },
  ],
  doble_cara: [
    { card: { id: 0, kind: "number", color: "astro", number: 4 } },
    { card: { id: 1, kind: "eclipse", color: "jade", number: null } },
    { card: { id: 2, kind: "sabueso", color: null, number: null }, dark: true },
  ],
  sin_tregua: [
    { card: { id: 0, kind: "barrido", color: "panal", number: null } },
    { card: { id: 1, kind: "ruleta", color: null, number: null } },
    { card: { id: 2, kind: "camaleon10", color: null, number: null } },
  ],
};

// Cómo se juega cada modo, en pocas líneas.
const HOW_TO: Record<Mode, string[]> = {
  clasico: [
    "Juega una carta del mismo color, número o símbolo que la de la mesa, o un Camaleón.",
    "Si no puedes (o no quieres), roba una; si te sirve, puedes jugarla ya.",
    "Pausa salta al siguiente; Remolino cambia el sentido; Carga +2 hace robar 2.",
    "Camaleón cambia el color; Camaleón +4 además hace robar 4 al siguiente.",
    "Al quedarte con una carta, pulsa «¡Última!» o te pueden pillar: robarías 2.",
  ],
  doble_cara: [
    "Cada carta tiene dos caras: la de luz y la de sombra, con sus propios palos. Se empieza por la luz.",
    "De tu mano ves la cara en juego; de las de los demás, la otra (y ellos la otra de las tuyas).",
    "El Eclipse le da la vuelta a todo: el descarte, el mazo y todas las manos.",
    "Luz: Carga +1, Pausa, Remolino, Camaleón y Camaleón +2. Sombra: Carga +5, Pausa total (todos pierden el turno), Remolino, Camaleón y Camaleón Sabueso (robar hasta sacar el color elegido).",
    "Al quedarte con una carta, pulsa «¡Última!» o te pueden pillar.",
  ],
  sin_tregua: [
    "168 cartas y ninguna piedad. Las cargas se acumulan: responde a un +2, +4, +6 o +10 con otra igual o mayor, o te lo comes todo.",
    "Si robas en tu turno, robas hasta sacar una carta que puedas jugar.",
    "El 7 cambia tu mano por la de quien elijas; el 0 hace que todos pasen su mano al siguiente.",
    "Barrido suelta todas tus cartas de su color. Pausa total deja sin turno a todos. Camaleón Ruleta: el siguiente elige color y destapa hasta que sale.",
    "Quien llega a 25 cartas queda fuera de la ronda. Gana quien se vacía la mano o el último que quede.",
  ],
};
// Meta habitual de cada modo, si se juega a puntos.
const USUAL_TARGET: Record<Mode, number> = { clasico: 500, doble_cara: 500, sin_tregua: 1000 };

interface Props {
  options: Options;
  initial: PrismaConfig;
  accountName?: string; // con cuenta, el nombre en la mesa es el de la cuenta
  onStart: (config: PrismaConfig) => void;
  onCancel?: () => void;
}

/** Pantalla de inicio de Prisma: presentación y opciones de la partida. */
export function StartScreen({ options, initial, accountName, onStart, onCancel }: Props) {
  const [config, setConfig] = useState<PrismaConfig>(initial);
  const mode: Mode = config.mode ?? "clasico";

  function change(changes: Partial<PrismaConfig>) {
    setConfig((current) => {
      const next = { ...current, ...changes };
      // Al cambiar de modo, si la meta era la habitual, pasa a la habitual del nuevo.
      if (changes.mode && changes.mode !== current.mode && current.target === USUAL_TARGET[current.mode ?? "clasico"]) {
        next.target = USUAL_TARGET[changes.mode];
      }
      return next;
    });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    onStart(accountName ? { ...config, player_name: accountName } : config);
  }

  return (
    <div className="felt rim relative mx-auto w-full max-w-4xl overflow-hidden rounded-[1.75rem]">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_50%,rgb(0_0_0/0.4))]" />
      <div className="relative p-5 sm:p-8">
        <header className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <PrismaIcon className="h-16 w-16 shrink-0 sm:h-20 sm:w-20" />
            <div>
              <h1 className="gold-text font-display text-4xl font-black tracking-tight sm:text-5xl">Prisma</h1>
              <p className="mt-1 text-emerald-50/85">Suelta todas tus cartas antes que nadie</p>
            </div>
          </div>
          <div className="relative mr-2 hidden h-36 w-52 shrink-0 sm:block" aria-hidden>
            {SAMPLES[mode].map(({ card, dark }, index) => (
              <span
                key={`${mode}${card.id}`}
                className="pop-in absolute top-2 block overflow-hidden rounded-lg shadow-lg"
                style={{ left: index * 44, transform: `rotate(${(index - 1) * 11}deg)`, width: 84, height: 118 } as CSSProperties}
              >
                <CardFaceArt card={card} dark={dark} />
              </span>
            ))}
          </div>
        </header>

        <form onSubmit={submit} className="mt-6 space-y-5 rounded-2xl bg-[#14090d]/92 p-5 shadow-lg ring-1 ring-amber-400/35 sm:p-6">
          <Field label="Tu nombre">
            <input
              type="text"
              required
              maxLength={16}
              readOnly={Boolean(accountName)}
              className={`${INPUT} ${accountName ? "text-amber-200" : ""}`}
              aria-label="Tu nombre"
              value={accountName ?? config.player_name}
              onChange={(event) => setConfig({ ...config, player_name: event.target.value })}
            />
          </Field>

          <ConfigPanel
            fields={options.fields}
            values={config as unknown as OptionValues}
            onChange={(changes) => change(changes as Partial<PrismaConfig>)}
          />

          <details className="rounded-xl border border-amber-400/20 bg-black/25 p-3 text-sm text-stone-300">
            <summary className="cursor-pointer font-bold text-amber-200">Cómo se juega</summary>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {HOW_TO[mode].map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </details>

          <div className="flex flex-wrap gap-3">
            <button type="submit" className="btn-gold h-14 flex-1 px-6 text-lg uppercase tracking-wide">
              Empezar partida
            </button>
            {onCancel && (
              <button type="button" onClick={onCancel} className="btn-dark h-14 px-5">
                Volver a la mesa
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
