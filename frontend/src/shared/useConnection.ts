import { useCallback, useEffect, useRef, useState } from "react";
import type { User } from "./account";
import { useAccount } from "./AccountContext";
import { getGuestId } from "./guest";

const RECONNECT_MS = 1500;
// Con este código cierra el servidor el WebSocket de quien no tiene sesión.
const SIGNED_OUT_CODE = 4401;

/** Lo que manda el servidor de cualquier juego por su WebSocket. */
export type ServerMessage<State, Options> =
  | {
      type: "hello";
      game: string;
      options: Options;
      user: User | null;
      elsewhere: number; // fichas de mi cuenta sentadas en otras mesas
      state: State | null;
    }
  | { type: "state"; state: State | null }
  | { type: "error"; message: string };

export interface Connection<Options, ClientMessage> {
  connected: boolean;
  options: Options | null;
  user: User | null; // la cuenta con la que el servidor me reconoce
  elsewhere: number; // fichas de mi cuenta sentadas en otras mesas: no se pueden traer a esta
  error: string | null;
  waiting: boolean; // hay una intención enviada y el servidor aún no ha contestado
  send: (message: ClientMessage) => void;
  reconnect: () => void; // tras entrar o salir de la cuenta: el servidor me identifica al conectar
}

/** El servidor no reconoce la sesión (caducó o se cerró en otra pestaña): hay que volver a entrar. */
export class SignedOut extends Error {}

/**
 * Pide al servidor mi partida de un juego (si no tengo, la crea) y devuelve su
 * id. Soy yo según la cookie de sesión. El identificador de invitado solo lo
 * mira un servidor de desarrollo que deja jugar sin cuenta.
 */
export async function openPartida(game: string, fetcher: typeof fetch = fetch): Promise<string> {
  const response = await fetcher("/api/partidas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ game, guest_id: getGuestId() }),
    credentials: "same-origin",
  });
  const data = (await response.json()) as { partida_id?: string; message?: string };
  if (response.status === 401) throw new SignedOut(data.message ?? "Entra en tu cuenta para jugar");
  if (!response.ok || !data.partida_id) throw new Error(data.message ?? "No se pudo abrir la partida");
  return data.partida_id;
}

/** Dirección del WebSocket de una partida. */
export function partidaUrl(game: string, partidaId: string): string {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const guest = encodeURIComponent(getGuestId());
  return `${scheme}://${location.host}/ws/${game}/${encodeURIComponent(partidaId)}?guest_id=${guest}`;
}

/**
 * Conexión con la partida de un juego. El cliente solo muestra el estado y
 * envía intenciones: el servidor decide todo.
 *
 * Primero se pide la partida por HTTP y luego se abre su WebSocket
 * (`/ws/{juego}/{partida_id}`). Cada estado recibido se entrega a `onState`;
 * `instant` vale `true` para el que llega al conectar: no se vio lo anterior,
 * así que no hay nada que animar.
 *
 * Quién soy lo decide el servidor con la cookie de sesión: cada cuenta tiene
 * su partida. Si cambia la cuenta, se vuelve a conectar; si el servidor ya no
 * reconoce la sesión, se vuelve a leer la cuenta y la web pide entrar.
 */
export function useConnection<State, Options, ClientMessage>(
  game: string,
  onState: (state: State | null, instant: boolean) => void,
): Connection<Options, ClientMessage> {
  const { identity, refresh } = useAccount();
  const [connected, setConnected] = useState(false);
  const [options, setOptions] = useState<Options | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [elsewhere, setElsewhere] = useState(0);
  const [connection, setConnection] = useState(0); // sube cada vez que hay que volver a conectar
  const [error, setError] = useState<string | null>(null);
  const [waiting, setWaitingState] = useState(false);
  // La misma marca en un ref: un doble clic llega antes de que React vuelva a dibujar.
  const waitingRef = useRef(false);
  const socketRef = useRef<WebSocket | null>(null);
  const onStateRef = useRef(onState);

  useEffect(() => {
    onStateRef.current = onState;
  }, [onState]);

  const setWaiting = useCallback((value: boolean) => {
    waitingRef.current = value;
    setWaitingState(value);
  }, []);

  useEffect(() => {
    let closed = false;
    let retry: number | undefined;

    function again() {
      if (closed) return;
      setConnected(false);
      setWaiting(false);
      retry = window.setTimeout(connect, RECONNECT_MS);
    }

    async function connect() {
      let partidaId: string;
      try {
        // Se pide cada vez: si el servidor se reinició, la partida es otra.
        partidaId = await openPartida(game);
      } catch (problem) {
        if (problem instanceof SignedOut) void refresh();
        again();
        return;
      }
      if (closed) return;
      const socket = new WebSocket(partidaUrl(game, partidaId));
      socketRef.current = socket;

      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        if (closed) return; // mensaje rezagado de una conexión que ya se dejó
        const message = JSON.parse(event.data) as ServerMessage<State, Options>;
        setWaiting(false);
        if (message.type === "error") {
          setError(message.message);
          return;
        }
        if (message.type === "hello") {
          setOptions(message.options);
          setUser(message.user ?? null);
          setElsewhere(message.elsewhere ?? 0);
        }
        setError(null);
        onStateRef.current(message.state, message.type === "hello");
      };
      socket.onclose = (event) => {
        if (event.code === SIGNED_OUT_CODE) void refresh();
        again();
      };
    }

    void connect();
    return () => {
      closed = true;
      window.clearTimeout(retry);
      socketRef.current?.close();
      setWaiting(false);
    };
  }, [game, identity, refresh, setWaiting, connection]);

  const reconnect = useCallback(() => setConnection((current) => current + 1), []);

  const send = useCallback(
    (message: ClientMessage) => {
      // Una intención cada vez: hasta que el servidor conteste no se envía otra.
      if (waitingRef.current) return;
      const socket = socketRef.current;
      if (socket?.readyState === WebSocket.OPEN) {
        setWaiting(true);
        socket.send(JSON.stringify(message));
      } else {
        setError("Sin conexión con el servidor. Reintentando…");
      }
    },
    [setWaiting],
  );

  return { connected, options, user, elsewhere, error, waiting, send, reconnect };
}
