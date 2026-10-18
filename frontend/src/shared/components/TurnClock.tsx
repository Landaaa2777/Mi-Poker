import { useEffect, useState, type CSSProperties } from "react";
import { secondsLeft, type TurnTimer } from "../room";

interface Props {
  timer: TurnTimer | null;
  label: string; // de quién es la decisión: "Te toca", "Turno de Ana"…
}

/**
 * La cuenta atrás de una decisión en una sala: los segundos que quedan y una
 * barra que se vacía. Cuenta desde que llegó el estado; con cada estado nuevo
 * vuelve a empezar desde lo que diga el servidor.
 */
export function TurnClock({ timer, label }: Props) {
  const [arrived, setArrived] = useState(() => performance.now());
  const [now, setNow] = useState(arrived);

  useEffect(() => {
    const moment = performance.now();
    setArrived(moment);
    setNow(moment);
  }, [timer?.seat, timer?.left]);

  useEffect(() => {
    if (!timer) return;
    const tick = window.setInterval(() => setNow(performance.now()), 250);
    return () => window.clearInterval(tick);
  }, [timer]);

  if (!timer) return null;
  const left = secondsLeft(timer, (now - arrived) / 1000);
  const urgent = left <= 10;
  const bar = {
    "--from": Math.min(1, timer.left / timer.total),
    animationDuration: `${timer.left}s`,
  } as CSSProperties;

  return (
    <div className="w-full max-w-sm" role="timer" aria-live="off" aria-label={`${label}: quedan ${left} segundos`}>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-semibold text-amber-100">{label}</span>
        <span className={`font-black tabular-nums ${urgent ? "text-rose-300" : "text-amber-300"}`}>{left} s</span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          key={`${timer.seat}-${timer.left}`}
          className={`turn-bar h-full rounded-full ${urgent ? "bg-rose-400" : "bg-amber-300"}`}
          style={bar}
        />
      </div>
    </div>
  );
}
