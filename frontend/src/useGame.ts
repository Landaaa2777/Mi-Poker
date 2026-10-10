import { useCallback, useEffect, useRef, useState } from "react";
import { getGuestId } from "./guest";
import type { ClientMessage, GameState, Options, ServerMessage } from "./types";

const RECONNECT_MS = 1500;

export interface GameConnection {
  connected: boolean;
  options: Options | null;
  state: GameState | null;
  error: string | null;
  send: (message: ClientMessage) => void;
}

/** Conexión con el servidor. El cliente solo muestra el estado y envía intenciones. */
export function useGame(): GameConnection {
  const [connected, setConnected] = useState(false);
  const [options, setOptions] = useState<Options | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

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
        if (message.type === "error") {
          setError(message.message);
          return;
        }
        if (message.type === "hello") setOptions(message.options);
        setState(message.state);
        setError(null);
      };
      socket.onclose = () => {
        if (closed) return;
        setConnected(false);
        retry = window.setTimeout(connect, RECONNECT_MS);
      };
    }

    connect();
    return () => {
      closed = true;
      window.clearTimeout(retry);
      socketRef.current?.close();
    };
  }, []);

  const send = useCallback((message: ClientMessage) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
    else setError("Sin conexión con el servidor. Reintentando…");
  }, []);

  return { connected, options, state, error, send };
}
