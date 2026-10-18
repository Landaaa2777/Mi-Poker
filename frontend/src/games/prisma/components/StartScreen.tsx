import { useState, type CSSProperties, type FormEvent } from "react";
import { ConfigPanel } from "../../../shared/components/ConfigPanel";
import { Field, INPUT } from "../../../shared/components/form";
import type { OptionValues } from "../../../shared/options";
import { CardFaceArt } from "../cardArt";
import { PrismaIcon } from "../icon";
import type { Card, Options, PrismaConfig } from "../types";

// Cartas de muestra para la cabecera.
const SAMPLE: Card[] = [
  { id: 0, kind: "number", color: "halo", number: 7 },
  { id: 1, kind: "remolino", color: "cumbre", number: null },
  { id: 2, kind: "camaleon4", color: null, number: null },
];

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
  // La meta solo importa si se juega a puntos.
  const fields = options.fields.filter((field) => field.key !== "target" || config.scoring);

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
            {SAMPLE.map((card, index) => (
              <span
                key={card.id}
                className="absolute top-2 block overflow-hidden rounded-lg shadow-lg"
                style={{ left: index * 44, transform: `rotate(${(index - 1) * 11}deg)`, width: 84, height: 118 } as CSSProperties}
              >
                <CardFaceArt card={card} />
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
            fields={fields}
            values={config as unknown as OptionValues}
            onChange={(changes) => setConfig((current) => ({ ...current, ...changes }))}
          />

          <details className="rounded-xl border border-amber-400/20 bg-black/25 p-3 text-sm text-stone-300">
            <summary className="cursor-pointer font-bold text-amber-200">Cómo se juega</summary>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>Juega una carta del mismo color, número o símbolo que la de la mesa, o un Camaleón.</li>
              <li>Si no puedes (o no quieres), roba una; si te sirve, puedes jugarla ya.</li>
              <li>Pausa salta al siguiente; Remolino cambia el sentido; Carga +2 hace robar 2.</li>
              <li>Camaleón cambia el color; Camaleón +4 además hace robar 4 al siguiente.</li>
              <li>Al quedarte con una carta, pulsa «¡Última!» o te pueden pillar: robarías 2.</li>
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
