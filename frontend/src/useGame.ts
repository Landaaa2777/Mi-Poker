import { useCallback, useEffect, useRef, useState } from "react";
import { getGuestId } from "./guest";
import type { ClientMessage, GameState, Options, ServerMessage } from "./types";

const RECONNECT_MS = 1500;

export interface GameConnection {
  connected: boolean;
  options: Options | null;
  error: string | null;
  waiting: boolean; // hay una intención enviada y el servidor aún no ha contestado
  send: (message: ClientMessage) => void;
}

/**
 * Conexión con el servidor. El cliente solo muestra el estado y envía intenciones.
 *
 * Cada estado recibido se entrega a `onState`. `instant` vale `true` para el
 * que llega al conectar: no se vio lo anterior, así que no hay nada que animar.
 */
export function useGame(
  onState: (state: GameState | null, instant: boolean) => void,
): GameConnection {
  const [connected, setConnected] = useState(false);
  const [options, setOptions] = useState<Options | null>(null);
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
        const message = JSON.parse(event.data) as ServerMessage;
        setWaiting(false);
        if (message.type === "error") {
          setError(message.message);
          return;
        }
        if (message.type === "hello") setOptions(message.options);
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
    };
  }, [setWaiting]);

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

  return { connected, options, error, waiting, send };
}
