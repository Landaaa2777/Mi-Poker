import { useCallback, useEffect, useRef, useState } from "react";
import { useAccount } from "../shared/AccountContext";
import { salaSocketUrl, type SalaView } from "./salas";

const RECONNECT_MS = 1500;
const LEFT = 4000; // el servidor cierra así: has salido de la sala, o se ha cerrado
const SIGNED_OUT = 4401;
const NOT_FOUND = 4404;

/** Lo que se recibe de la partida: el estado y si llega de golpe (al conectar, sin nada que animar). */
export type StateListener = (state: unknown, instant: boolean) => void;

export interface SalaConnection {
  sala: SalaView | null;
  connected: boolean;
  /** La sala ya no está a mi alcance (he salido, se ha cerrado o no existe), con el motivo. */
  closed: string | null;
  error: string | null;
  waiting: boolean; // hay una jugada enviada y el servidor aún no ha contestado
  send: (message: object) => void;
  /** Avisa de cada estado de la partida; al apuntarse, recibe el último que haya. */
  subscribe: (listener: StateListener) => () => void;
}

/**
 * La sala en tiempo real: quién está, sus opciones y, con la partida empezada,
 * lo que veo de la mesa. Si la conexión se corta, vuelve a conectar sola: el
 * sitio se guarda en el servidor.
 */
export function useSala(code: string): SalaConnection {
  const { refresh } = useAccount();
  const [sala, setSala] = useState<SalaView | null>(null);
  const [connected, setConnected] = useState(false);
  const [closed, setClosed] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waiting, setWaitingState] = useState(false);
  const waitingRef = useRef(false);
  const socketRef = useRef<WebSocket | null>(null);
  const listeners = useRef(new Set<StateListener>());
  const latest = useRef<{ state: unknown } | null>(null);
  const status = useRef<SalaView["status"] | null>(null);
  const fresh = useRef(true); // el próximo estado llega de golpe (al conectar o en una partida nueva)

  const setWaiting = useCallback((value: boolean) => {
    waitingRef.current = value;
    setWaitingState(value);
  }, []);

  useEffect(() => {
    let stopped = false;
    let retry: number | undefined;

    function connect() {
      const socket = new WebSocket(salaSocketUrl(code));
      socketRef.current = socket;
      fresh.current = true;
      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        if (stopped) return;
        const message = JSON.parse(event.data) as
          | { type: "sala"; sala: SalaView }
          | { type: "state"; state: unknown }
          | { type: "error"; message: string };
        setWaiting(false);
        if (message.type === "sala") {
          // Empieza una partida nueva: la mesa de la anterior ya no vale.
          if (message.sala.status === "playing" && status.current === "waiting") {
            latest.current = null;
            fresh.current = true;
          }
          status.current = message.sala.status;
          setSala(message.sala);
          setError(null);
        } else if (message.type === "state") {
          latest.current = { state: message.state };
          for (const listener of listeners.current) listener(message.state, fresh.current);
          fresh.current = false;
        } else {
          setError(message.message);
        }
      };
      socket.onclose = (event) => {
        if (stopped) return;
        setConnected(false);
        setWaiting(false);
        if (event.code === LEFT || event.code === NOT_FOUND) {
          setClosed(event.reason || "La sala se ha cerrado");
          return;
        }
        if (event.code === SIGNED_OUT) void refresh(); // sin sesión: la web pedirá entrar
        retry = window.setTimeout(connect, RECONNECT_MS);
      };
    }

    connect();
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      socketRef.current?.close();
    };
  }, [code, refresh, setWaiting]);

  const send = useCallback(
    (message: object) => {
      const socket = socketRef.current;
      if (socket?.readyState !== WebSocket.OPEN) {
        setError("Sin conexión con el servidor. Reintentando…");
        return;
      }
      const type = (message as { type?: string }).type;
      // Una jugada cada vez: hasta que el servidor conteste no se envía otra.
      // Lo de la sala (opciones, empezar, salir) no espera.
      if (type !== "configure" && type !== "start" && type !== "leave") {
        if (waitingRef.current) return;
        setWaiting(true);
      }
      socket.send(JSON.stringify(message));
    },
    [setWaiting],
  );

  const subscribe = useCallback((listener: StateListener) => {
    listeners.current.add(listener);
    if (latest.current) listener(latest.current.state, true);
    return () => {
      listeners.current.delete(listener);
    };
  }, []);

  return { sala, connected, closed, error, waiting, send, subscribe };
}
