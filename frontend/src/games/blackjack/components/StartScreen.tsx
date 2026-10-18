import { useState, type CSSProperties, type FormEvent } from "react";
import { PlayingCard } from "../../../shared/cards/PlayingCard";
import { ConfigPanel } from "../../../shared/components/ConfigPanel";
import { DailyChipsNote, Field, INPUT } from "../../../shared/components/form";
import { formatChips } from "../../../shared/format";
import { numberProblem, type OptionValues } from "../../../shared/options";
import { BlackjackIcon } from "../icon";
import type { BlackjackConfig, Options } from "../types";

interface Props {
  options: Options;
  initial: BlackjackConfig;
  accountName?: string; // con cuenta, el nombre en la mesa es el de la cuenta
  balance: number | null; // con cuenta, las fichas de la mesa salen de este saldo
  atStake: number; // lo apostado en una ronda a medias: se pierde al empezar otra partida
  elsewhere: number; // fichas sentadas en otras mesas: no se pueden traer a esta
  nextChipsAt: number | null; // con cuenta, cuándo llegan las próximas fichas diarias
  onStart: (config: BlackjackConfig) => void;
  onCancel?: () => void; // hay una partida a la que se puede volver
}

/** Pantalla de inicio del blackjack: presentación y opciones de la mesa. */
export function StartScreen({
  options,
  initial,
  accountName,
  balance,
  atStake,
  elsewhere,
  nextChipsAt,
  onStart,
  onCancel,
}: Props) {
  // Con cuenta no se puede llevar a la mesa más de lo que se tiene libre.
  const available = balance === null ? null : Math.max(0, balance - atStake - elsewhere);
  const [config, setConfig] = useState<BlackjackConfig>(() => {
    if (available === null || initial.starting_stack <= available) return initial;
    return { ...initial, starting_stack: Math.max(available - (available % 10), 10) };
  });
  const noChips = available !== null && available < config.min_bet;

  const fieldProblem = options.fields
    .map((field) =>
      field.type === "number"
        ? numberProblem(
            field,
            Number(config[field.key as keyof BlackjackConfig]),
            field.key === "starting_stack" && available !== null ? available : undefined,
          )
        : null,
    )
    .find((problem) => problem !== null);
  const problem = noChips
    ? "No te quedan fichas libres para sentarte a una mesa."
    : (fieldProblem ??
      (config.min_bet > config.max_bet
        ? "La apuesta mínima no puede superar a la máxima."
        : config.starting_stack < config.min_bet
          ? "Las fichas iniciales deben cubrir al menos la apuesta mínima."
          : null));

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!problem) onStart(accountName ? { ...config, player_name: accountName } : config);
  }

  return (
    <div className="felt rim relative mx-auto w-full max-w-4xl overflow-hidden rounded-[1.75rem]">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_50%,rgb(0_0_0/0.4))]" />
      <div className="relative p-5 sm:p-8">
        <header className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <BlackjackIcon className="h-16 w-16 shrink-0 text-amber-300 sm:h-20 sm:w-20" />
            <div>
              <h1 className="gold-text font-display text-4xl font-black tracking-tight sm:text-5xl">Blackjack</h1>
              <p className="mt-1 text-emerald-50/85">Suma 21 sin pasarte y gánale al crupier</p>
            </div>
          </div>
          <div
            className="relative mr-4 hidden h-36 w-40 shrink-0 sm:block"
            style={{ "--card-w": "84px" } as CSSProperties}
            aria-hidden
          >
            <span className="absolute left-0 top-2 -rotate-[10deg]">
              <PlayingCard card="Ah" interactive="tilt" float={0.2} />
            </span>
            <span className="absolute left-14 top-0 rotate-[9deg]">
              <PlayingCard card="Ks" interactive="tilt" float={0.2} />
            </span>
          </div>
        </header>

        <form
          onSubmit={submit}
          className="mt-6 space-y-5 rounded-2xl bg-[#14090d]/92 p-5 shadow-lg ring-1 ring-amber-400/35 sm:p-6"
        >
          <Field label="Tu nombre">
            {accountName ? (
              <input
                type="text"
                readOnly
                className={`${INPUT} text-amber-200`}
                aria-label="Tu nombre"
                title="Juegas con el nombre de tu cuenta"
                value={accountName}
              />
            ) : (
              <input
                type="text"
                required
                maxLength={16}
                className={INPUT}
                aria-label="Tu nombre"
                value={config.player_name}
                onChange={(event) => setConfig({ ...config, player_name: event.target.value })}
              />
            )}
          </Field>

          <ConfigPanel
            fields={options.fields}
            values={config as unknown as OptionValues}
            onChange={(changes) => setConfig((current) => ({ ...current, ...changes }))}
            maxFor={available !== null ? { starting_stack: available } : {}}
            labelFor={
              available !== null
                ? { starting_stack: `Fichas para la mesa (tienes ${formatChips(available)} libres)` }
                : {}
            }
          />

          {balance !== null && (
            <DailyChipsNote nextAt={nextChipsAt} outOfChips={noChips ? problem : null} />
          )}

          {atStake > 0 && balance !== null && (
            <p className="text-sm text-amber-100/85">
              Tienes una ronda a medias: si empiezas otra partida ahora, pierdes las{" "}
              {formatChips(atStake)} fichas que llevas apostadas en ella.
            </p>
          )}
          {elsewhere > 0 && balance !== null && (
            <p className="text-sm text-amber-100/85">
              Tienes {formatChips(elsewhere)} fichas sentadas en otra mesa: no se pueden traer a
              esta mientras sigan allí.
            </p>
          )}

          {/* Sin fichas, el motivo ya sale en el aviso de las fichas diarias. */}
          {problem && !noChips && <p className="text-sm font-semibold text-amber-300">{problem}</p>}

          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={problem !== null}
              className="btn-gold h-14 flex-1 px-6 text-lg uppercase tracking-wide"
            >
              Sentarse a la mesa
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
