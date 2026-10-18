import { useEffect, useRef, useState } from "react";
import { GAME_ICONS } from "../../games";
import { fetchGames, type GameEntry } from "../../hub/hub";
import { Avatar } from "../../shared/components/Avatar";
import { ConfigPanel } from "../../shared/components/ConfigPanel";
import { CHOICE, CHOSEN, NOT_CHOSEN } from "../../shared/components/form";
import { numberProblem, type OptionValues } from "../../shared/options";
import { describeOptions, onlyHere, salaLink, type SalaView } from "../salas";
import { CodeTiles, CopyButton } from "./CodeTiles";

interface Props {
  sala: SalaView;
  send: (message: object) => void;
  onLeave: () => void;
}

/** La sala de espera: el código para invitar, quién está, las opciones y el botón de empezar. */
export function Lobby({ sala, send, onLeave }: Props) {
  const host = sala.you === sala.host;
  const link = salaLink(sala.code);
  const share = typeof navigator.share === "function";

  return (
    <div className="grid gap-gutter lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <section className="felt rim relative overflow-hidden rounded-[1.6rem] p-5 sm:p-7">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_50%,rgb(0_0_0/0.35))]" />
        <div className="relative flex flex-col items-center gap-4 text-center">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-100/75">
            {sala.game_name} · sala de {sala.host}
          </p>
          <h1 className="gold-text font-display text-3xl font-black sm:text-4xl">
            {sala.game_over ? "¿Otra partida?" : "Sala de espera"}
          </h1>
          <CodeTiles code={sala.code} />
          <div className="flex flex-wrap justify-center gap-2">
            <CopyButton text={sala.code} label="Copiar código" />
            <CopyButton text={link} label="Copiar enlace" />
            {share && (
              <button
                type="button"
                className="btn-dark h-10 px-4 text-sm"
                onClick={() =>
                  void navigator.share({ title: "mi-poker", text: `Únete a mi sala de ${sala.game_name}`, url: link }).catch(() => {})
                }
              >
                Compartir
              </button>
            )}
          </div>
          <input
            readOnly
            value={link}
            aria-label="Enlace de la sala"
            className="w-full max-w-md rounded-lg border border-amber-400/25 bg-black/40 px-3 py-2 text-center text-sm text-amber-100/85 outline-none focus:border-amber-300"
            onFocus={(event) => event.target.select()}
          />
          <p className="max-w-md text-sm text-emerald-50/85">
            Comparte el código o el enlace. Cuando estéis todos,{" "}
            {host ? "empieza la partida." : `${sala.host} empezará la partida.`}
          </p>
          {onlyHere(location.hostname) && (
            <p className="max-w-md rounded-lg bg-black/40 px-3 py-2 text-xs text-amber-100">
              Este enlace solo funciona en este ordenador. Para invitar a otros, abre la web con la
              dirección de tu red (la que dice <code>scripts/red_local.py</code> al arrancar) o la del
              túnel; el código sirve igual.
            </p>
          )}
        </div>
      </section>

      <section className="panel flex flex-col gap-3 p-5">
        <h2 className="gold-text text-lg font-black">
          Quién está <span className="text-sm font-semibold text-stone-400">({sala.members.length} de {sala.max_people})</span>
        </h2>
        <ul className="flex flex-col gap-2">
          {sala.members.map((member) => (
            <li key={member.name} className="flex items-center gap-3 rounded-xl bg-black/30 px-3 py-2">
              <Avatar name={member.name} size={36} ring={member.host ? "ring-amber-300" : "ring-white/25"} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold">
                  {member.name}
                  {member.name === sala.you && <span className="ml-1.5 text-xs text-stone-400">(tú)</span>}
                </div>
                <div className="text-xs text-stone-400">{member.host ? "Anfitrión" : "Invitado"}</div>
              </div>
              <span
                className={`flex items-center gap-1.5 text-xs ${member.connected ? "text-emerald-300" : "text-stone-500"}`}
              >
                <span className={`h-2 w-2 rounded-full ${member.connected ? "bg-emerald-400" : "bg-stone-600"}`} />
                {member.connected ? "Conectado" : "Desconectado"}
              </span>
            </li>
          ))}
        </ul>
        {sala.members.length < sala.min_people && (
          <p className="text-sm text-amber-100/70">Hacen falta al menos {sala.min_people} personas para empezar.</p>
        )}
      </section>

      <section className="panel flex flex-col gap-4 p-5 lg:col-span-2">
        <h2 className="gold-text text-lg font-black">La partida</h2>
        {host ? (
          <HostOptions sala={sala} send={send} />
        ) : (
          <ul className="grid gap-x-6 gap-y-1 text-sm text-stone-300 sm:grid-cols-2">
            <li className="font-semibold text-amber-100">Juego: {sala.game_name}</li>
            {describeOptions(sala.fields, sala.options).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex flex-wrap items-center gap-3 lg:col-span-2">
        {host ? (
          <button
            type="button"
            className="btn-gold h-14 flex-1 px-6 text-lg uppercase tracking-wide"
            disabled={!sala.can_start}
            onClick={() => send({ type: "start" })}
          >
            {sala.game_over ? "Empezar otra partida" : "Empezar partida"}
          </button>
        ) : (
          <p className="flex-1 text-amber-100/75">Esperando a que {sala.host} empiece la partida…</p>
        )}
        <button type="button" className="btn-dark h-14 px-5" onClick={onLeave}>
          Salir de la sala
        </button>
      </div>
    </div>
  );
}

/** Las opciones, para el anfitrión: el juego y su panel. Los cambios se envían solos. */
function HostOptions({ sala, send }: { sala: SalaView; send: (message: object) => void }) {
  const [games, setGames] = useState<GameEntry[]>([]);
  const [draft, setDraft] = useState<OptionValues>(sala.options);
  const pending = useRef<number | undefined>(undefined);

  useEffect(() => {
    void fetchGames().then(
      (list) => setGames(list.filter((game) => game.rooms)),
      () => setGames([]),
    );
  }, []);
  // Manda lo que diga el servidor, salvo mientras se está escribiendo un cambio.
  useEffect(() => {
    if (pending.current === undefined) setDraft(sala.options);
  }, [sala.options]);
  useEffect(() => () => window.clearTimeout(pending.current), []);

  const roomForBots = sala.max_people - sala.members.length;
  const problem =
    sala.fields
      .map((field) => numberProblem(field, Number(draft[field.key] ?? field.default), field.key === "bots" ? roomForBots : undefined))
      .find((found) => found !== null) ?? null;

  function change(changes: OptionValues) {
    const next = { ...draft, ...changes };
    setDraft(next);
    window.clearTimeout(pending.current);
    pending.current = window.setTimeout(() => {
      pending.current = undefined;
      const invalid = sala.fields.some(
        (field) => numberProblem(field, Number(next[field.key] ?? field.default), field.key === "bots" ? roomForBots : undefined) !== null,
      );
      if (!invalid) send({ type: "configure", options: next });
    }, 400);
  }

  return (
    <div className="flex flex-col gap-5">
      {games.length > 0 && (
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Juego">
          {games.map((game) => {
            const Icon = GAME_ICONS[game.id];
            const chosen = game.id === sala.game;
            return (
              <button
                key={game.id}
                type="button"
                role="radio"
                aria-checked={chosen}
                className={`${CHOICE} flex items-center gap-2 ${chosen ? CHOSEN : NOT_CHOSEN}`}
                onClick={() => {
                  if (!chosen) send({ type: "configure", game: game.id, options: {} });
                }}
              >
                {Icon && <Icon className="h-5 w-5" />}
                {game.name}
              </button>
            );
          })}
        </div>
      )}
      <ConfigPanel
        fields={sala.fields}
        values={draft}
        onChange={change}
        maxFor={{ bots: roomForBots }}
        labelFor={{ bots: `Bots (caben ${roomForBots})` }}
      />
      {problem && <p className="text-sm font-semibold text-amber-300">{problem}</p>}
    </div>
  );
}
