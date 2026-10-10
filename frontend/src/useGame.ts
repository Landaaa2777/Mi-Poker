import { useCallback, useEffect, useRef, useState } from "react";
import type { User } from "./account";
import { getGuestId } from "./guest";
import type { ClientMessage, GameState, Options, ServerMessage } from "./types";

const RECONNECT_MS = 1500;

export interface GameConnection {
  connected: boolean;
  options: Options | null;
  user: User | null; // la cuenta con la que el servidor me reconoce; null = invitado
  error: string | null;
  waiting: boolean; // hay una intención enviada y el servidor aún no ha contestado
  send: (message: ClientMessage) => void;
  reconnect: () => void; // tras entrar o salir de la cuenta: el servidor me identifica al conectar
}

/**
 * Conexión con el servidor. El cliente solo muestra el estado y envía intenciones.
 *
 * Cada estado recibido se entrega a `onState`. `instant` vale `true` para el
 * que llega al conectar: no se vio lo anterior, así que no hay nada que animar.
 *
 * Quién soy lo decide el servidor al conectar: mira la cookie de sesión y, si
 * no hay cuenta, el identificador de invitado. Cada identidad tiene su partida.
 */
export function useGame(
  onState: (state: GameState | null, instant: boolean) => void,
): GameConnection {
  const [connected, setConnected] = useState(false);
  const [options, setOptions] = useState<Options | null>(null);
  const [user, setUser] = useState<User | null>(null);
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

    function connect() {
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      const url = `${scheme}://${location.host}/ws?guest_id=${encodeURIComponent(getGuestId())}`;
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        if (closed) return; // mensaje rezagado de una conexión que ya se dejó
        const message = JSON.parse(event.data) as ServerMessage;
        setWaiting(false);
        if (message.type === "error") {
          setError(message.message);
          return;
        }
        if (message.type === "hello") {
          setOptions(message.options);
          setUser(message.user ?? null);
        }
        setError(null);
        onStateRef.current(message.state, message.type === "hello");
      };
      socket.onclose = () => {
        if (closed) return;
        setConnected(false);
        setWaiting(false);
        retry = window.setTimeout(connect, RECONNECT_MS);
      };
    }

    connect();
    return () => {
      closed = true;
      window.clearTimeout(retry);
      socketRef.current?.close();
      setWaiting(false);
    };
  }, [setWaiting, connection]);

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

  return { connected, options, user, error, waiting, send, reconnect };
}
