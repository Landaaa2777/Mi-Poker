import { Suspense, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import { GAME_ROOMS } from "../games";
import { audio } from "../shared/audio/engine";
import { ConfirmDialog } from "../shared/components/ConfirmDialog";
import { HeaderContent } from "../shared/Layout";
import { usePlatformSettings } from "../shared/SettingsContext";
import { useDocumentTitle } from "../shared/useDocumentTitle";
import { useLeaveGuard, type LeaveTexts } from "../shared/useLeaveGuard";
import { FoundAnimation } from "./components/FoundAnimation";
import { Lobby } from "./components/Lobby";
import { joinSala, normalizeCode, type SalaView } from "./salas";
import { useSala } from "./useSala";

// Cuánto se ve cada parte de la animación de entrada (con las animaciones activadas).
const SEARCH_MS = 900; // "Buscando la sala…", como poco
const FOUND_MS = 1700; // "¡Partida encontrada!"

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

/** Lo que pasa si abandonas la partida de cada juego. */
const ABANDON: Record<string, string> = {
  poker: "Te retiras de la mano en curso (pierdes lo que hayas apostado en ella) y dejas la mesa con tus fichas.",
  blackjack: "Tu ronda se juega sola (te plantas) y, al terminar, dejas la mesa con tus fichas.",
  prisma: "Un bot ocupa tu sitio y sigue con tus cartas.",
};

const AWAY: LeaveTexts = {
  title: "¿Salir de la mesa?",
  message:
    "Tu sitio se guarda: vuelve cuando quieras con el mismo enlace. Mientras no estés, cuando se acabe tu tiempo se jugará por ti lo más prudente.",
  confirmLabel: "Salir",
  cancelLabel: "Seguir jugando",
};

/**
 * /sala/{código}: entrar en una sala (con su animación) y, dentro, la sala de
 * espera o la mesa de la partida.
 */
export default function SalaPage() {
  const params = useParams();
  const code = normalizeCode(params.code ?? "");
  // Quien acaba de crear la sala no tiene nada que buscar.
  const created = (useLocation().state as { created?: boolean } | null)?.created === true;
  const { animations } = usePlatformSettings();
  const animated = useRef(animations);
  const [phase, setPhase] = useState<"searching" | "found" | "inside" | "error">(created ? "inside" : "searching");
  const [problem, setProblem] = useState<string | null>(null);
  useDocumentTitle(code ? `Sala ${code} · mi-poker` : "Salas con amigos · mi-poker");

  useEffect(() => {
    if (created || !code) return;
    let cancelled = false;
    const started = performance.now();
    void joinSala(code).then(async (result) => {
      if (cancelled) return;
      if (!result.ok) {
        setProblem(result.message);
        setPhase("error");
        return;
      }
      // Que la búsqueda se vea un momento, aunque el servidor conteste enseguida.
      if (animated.current) await sleep(Math.max(0, SEARCH_MS - (performance.now() - started)));
      if (cancelled) return;
      setPhase("found");
      audio.play("win");
      await sleep(animated.current ? FOUND_MS : 600);
      if (!cancelled) setPhase("inside");
    });
    return () => {
      cancelled = true;
    };
  }, [code, created]);

  if (!code || phase === "error") {
    return (
      <section className="panel mx-auto flex w-full max-w-lg flex-col items-center gap-4 p-6 text-center">
        <h1 className="gold-text text-2xl font-black">No se pudo entrar en la sala</h1>
        <p className="text-amber-100">{code ? problem : "Ese enlace no tiene un código de sala válido."}</p>
        <div className="flex flex-wrap justify-center gap-2">
          <Link to="/salas" className="btn-gold flex h-11 items-center px-5">
            Probar otro código
          </Link>
          <Link to="/" className="btn-dark flex h-11 items-center px-5">
            Volver al menú
          </Link>
        </div>
      </section>
    );
  }
  if (phase !== "inside") return <FoundAnimation phase={phase} code={code} />;
  return <SalaInside code={code} />;
}

/** Dentro de la sala: la espera o la partida, en tiempo real. */
function SalaInside({ code }: { code: string }) {
  const room = useSala(code);
  const { sala, closed } = room;
  const [abandoning, setAbandoning] = useState(false);
  const playing = sala?.status === "playing";
  // Cada partida nueva de la sala monta su mesa desde cero: solo se mira cuándo
  // empieza una partida, no cada cambio de la sala.
  const [games, setGames] = useState(0);
  const [shown, setShown] = useState<string | null>(null); // el juego de la última mesa
  const game = sala?.game ?? null;
  useEffect(() => {
    if (playing) {
      setGames((count) => count + 1);
      setShown(game);
    }
  }, [playing]);
  const leaveGuard = useLeaveGuard(playing, AWAY);

  if (closed) {
    return (
      <section className="panel mx-auto flex w-full max-w-lg flex-col items-center gap-4 p-6 text-center">
        <h1 className="gold-text text-2xl font-black">{closed}</h1>
        <div className="flex flex-wrap justify-center gap-2">
          <Link to="/salas" className="btn-gold flex h-11 items-center px-5">
            Ir a las salas
          </Link>
          <Link to="/" className="btn-dark flex h-11 items-center px-5">
            Volver al menú
          </Link>
        </div>
      </section>
    );
  }
  if (!sala) return <p className="panel px-3 py-2 text-sm">Conectando con la sala…</p>;

  // La mesa se ve durante la partida y, al terminar, hasta que se cambia de juego.
  const Table = shown && shown === sala.game && (playing || sala.game_over) ? GAME_ROOMS[shown] : undefined;

  return (
    <>
      <HeaderContent
        info={
          <span className="text-sm text-amber-100/60">
            Sala {sala.code} · {sala.game_name}
          </span>
        }
        actions={
          playing && (
            <button className="btn-red h-9 whitespace-nowrap px-4 text-sm" onClick={() => setAbandoning(true)}>
              Abandonar
            </button>
          )
        }
      />
      {!room.connected && <p className="panel px-3 py-2 text-sm">Reconectando con la sala…</p>}
      {room.error && (
        <p role="alert" className="rounded-lg bg-rose-800 px-3 py-2 text-sm">
          {room.error}
        </p>
      )}
      {Table && (
        <Suspense fallback={<p className="panel px-3 py-2 text-sm">Cargando la mesa…</p>}>
          <Table key={games} play={room} />
        </Suspense>
      )}
      {playing ? <People sala={sala} /> : <Lobby sala={sala} send={room.send} onLeave={() => room.send({ type: "leave" })} />}
      {abandoning && (
        <ConfirmDialog
          title="¿Abandonar la partida?"
          message={`${ABANDON[sala.game] ?? ""} No podrás volver a esta partida.`}
          confirmLabel="Abandonar"
          cancelLabel="Seguir jugando"
          onConfirm={() => {
            setAbandoning(false);
            room.send({ type: "leave" });
          }}
          onCancel={() => setAbandoning(false)}
        />
      )}
      {leaveGuard}
    </>
  );
}

/** Durante la partida: quién hay en la sala y si está conectado. */
function People({ sala }: { sala: SalaView }) {
  return (
    <section className="panel flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2 text-sm" aria-label="Personas en la sala">
      <span className="font-bold text-amber-200">Sala {sala.code}</span>
      {sala.members.map((member) => (
        <span key={member.name} className="flex items-center gap-1.5">
          <span className={`h-2 w-2 rounded-full ${member.connected ? "bg-emerald-400" : "bg-stone-600"}`} />
          {member.name}
          {member.name === sala.you && <span className="text-stone-400">(tú)</span>}
          {!member.connected && <span className="text-stone-500">· desconectado</span>}
        </span>
      ))}
    </section>
  );
}
