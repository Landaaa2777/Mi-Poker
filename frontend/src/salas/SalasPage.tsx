import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { GAME_ICONS } from "../games";
import { RoomsIcon } from "../hub/icons";
import { fetchGames, type GameEntry } from "../hub/hub";
import { INPUT } from "../shared/components/form";
import { useDocumentTitle } from "../shared/useDocumentTitle";
import { CODE_LENGTH, createSala, fetchMySala, normalizeCode, type SalaSummary } from "./salas";

/** /salas: crear una sala para jugar con amigos, o entrar en una con su código. */
export default function SalasPage() {
  useDocumentTitle("Salas con amigos · mi-poker");
  const navigate = useNavigate();
  const [games, setGames] = useState<GameEntry[] | null>(null);
  const [mine, setMine] = useState<SalaSummary | null>(null);
  const [code, setCode] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [creating, setCreating] = useState<string | null>(null);

  useEffect(() => {
    void fetchGames().then(
      (list) => setGames(list.filter((game) => game.rooms)),
      () => setProblem("No se pudo conectar con el servidor."),
    );
    void fetchMySala().then(setMine);
  }, []);

  async function create(game: string) {
    if (creating) return;
    setCreating(game);
    setProblem(null);
    const result = await createSala(game);
    setCreating(null);
    if (result.ok) navigate(`/sala/${result.sala.code}`, { state: { created: true } });
    else setProblem(result.message);
  }

  function join(event: FormEvent) {
    event.preventDefault();
    const normalized = normalizeCode(code);
    if (!normalized) {
      setProblem(`Un código tiene ${CODE_LENGTH} letras y números, por ejemplo K7P2QX.`);
      return;
    }
    navigate(`/sala/${normalized}`);
  }

  const gameName = (id: string) => games?.find((game) => game.id === id)?.name ?? id;

  return (
    <>
      <section className="felt rim relative overflow-hidden rounded-[1.6rem] px-5 py-6 sm:px-8 sm:py-8">
        <div className="flex items-center gap-4 sm:gap-6">
          <RoomsIcon className="h-16 w-16 shrink-0 text-amber-300 drop-shadow-[0_4px_10px_rgb(0_0_0/0.5)] sm:h-20 sm:w-20" />
          <div>
            <h1 className="gold-text font-display text-3xl font-black tracking-tight sm:text-4xl">Salas con amigos</h1>
            <p className="mt-1 text-sm text-emerald-50/85 sm:text-base">
              Crea una sala, comparte el código o el enlace y jugad juntos.
            </p>
          </div>
        </div>
      </section>

      {mine && (
        <p className="panel flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
          <span className="flex-1">
            Estás en la sala <strong className="text-amber-200">{mine.code}</strong> ({gameName(mine.game)}
            {mine.status === "playing" ? ", con la partida empezada" : ""}).
          </span>
          <Link to={`/sala/${mine.code}`} className="btn-green flex h-10 items-center px-4">
            Volver a la sala
          </Link>
        </p>
      )}

      {problem && (
        <p role="alert" className="rounded-lg bg-rose-800 px-3 py-2 text-sm">
          {problem}
        </p>
      )}

      <div className="grid gap-gutter lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <section className="panel flex flex-col gap-4 p-5">
          <div>
            <h2 className="gold-text text-xl font-black">Crear una sala</h2>
            <p className="text-sm text-stone-300">Elige el juego. Luego podrás cambiar las opciones y añadir bots.</p>
          </div>
          {!games && <p className="text-sm text-stone-400">Cargando juegos…</p>}
          <ul className="grid gap-3 sm:grid-cols-3">
            {games?.map((game) => {
              const Icon = GAME_ICONS[game.id];
              return (
                <li key={game.id}>
                  <button
                    type="button"
                    disabled={creating !== null}
                    className="hub-card flex h-full w-full flex-col items-center gap-2 rounded-tile border border-amber-400/30 bg-black/30 p-4 text-center outline-none hover:bg-white/5 focus-visible:ring-4 focus-visible:ring-amber-300/70 disabled:opacity-60"
                    onClick={() => void create(game.id)}
                  >
                    <span className="felt flex h-16 w-full items-center justify-center rounded-xl">
                      {Icon && <Icon className="h-11 w-11 text-gold" />}
                    </span>
                    <span className="gold-text font-display text-lg font-black">{game.name}</span>
                    <span className="text-xs text-amber-100/60">2 a {game.max_players} personas</span>
                    <span className="btn-gold mt-auto flex h-9 w-full items-center justify-center text-sm">
                      {creating === game.id ? "Creando…" : "Crear sala"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="panel flex flex-col gap-4 p-5">
          <div>
            <h2 className="gold-text text-xl font-black">Unirme con un código</h2>
            <p className="text-sm text-stone-300">Te lo da quien creó la sala. También puedes abrir su enlace.</p>
          </div>
          <form className="flex flex-col gap-3" onSubmit={join} noValidate>
            <label className="sr-only" htmlFor="sala-code">
              Código de la sala
            </label>
            <input
              id="sala-code"
              className={`${INPUT} text-center font-numbers text-3xl font-black uppercase tracking-[0.3em]`}
              placeholder="K7P2QX"
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              maxLength={CODE_LENGTH + 2}
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
            <button type="submit" className="btn-gold h-12 uppercase tracking-wide">
              Buscar la sala
            </button>
          </form>
        </section>
      </div>
    </>
  );
}
