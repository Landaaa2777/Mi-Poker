import { useEffect, useRef, useState } from "react";

/** La hora actual en segundos desde 1970, puesta al día cada `everyMs`: para textos como "dentro de 3 h". */
export function useNow(everyMs = 60_000): number {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now() / 1000), everyMs);
    return () => window.clearInterval(timer);
  }, [everyMs]);
  return now;
}

// Lo máximo que espera setTimeout (unos 24 días); más allá dispararía enseguida.
const MAX_WAIT_MS = 2 ** 31 - 1;

/**
 * Llama a `callback` cuando llega el momento `at` (segundos desde 1970), si la
 * página sigue abierta. Sirve para volver a leer el saldo cuando llegan las
 * fichas diarias. Con `at` nulo no hace nada.
 */
export function useWhenDue(at: number | null | undefined, callback: () => void): void {
  const callbackRef = useRef(callback);
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (at == null) return;
    // Un segundo de margen: el reloj del navegador y el del servidor no van exactos.
    const wait = Math.max(0, at * 1000 - Date.now()) + 1000;
    if (wait > MAX_WAIT_MS) return;
    const timer = window.setTimeout(() => callbackRef.current(), wait);
    return () => window.clearTimeout(timer);
  }, [at]);
}
