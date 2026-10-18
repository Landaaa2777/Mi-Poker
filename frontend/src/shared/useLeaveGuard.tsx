import type { ReactNode } from "react";
import { useBlocker } from "react-router";
import { ConfirmDialog } from "./components/ConfirmDialog";

export interface LeaveTexts {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
}

const PAUSED: LeaveTexts = {
  title: "¿Volver al menú?",
  message: "Tu partida queda en pausa: podrás continuarla desde el menú cuando quieras.",
  confirmLabel: "Ir al menú",
  cancelLabel: "Seguir jugando",
};

/**
 * Al salir de un juego con una partida en curso (botón Menú, el nombre del
 * juego, la flecha de atrás del navegador…) se pide confirmación. Contra bots
 * la partida no se pierde: queda en pausa en el servidor y el menú ofrece
 * continuarla. En una sala, cada juego da su propio aviso (`texts`).
 *
 * Devuelve la ventana de confirmación cuando hace falta enseñarla; el juego la
 * pinta donde quiera.
 */
export function useLeaveGuard(inProgress: boolean, texts: LeaveTexts = PAUSED): ReactNode {
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      inProgress && currentLocation.pathname !== nextLocation.pathname,
  );
  if (blocker.state !== "blocked") return null;
  return (
    <ConfirmDialog
      {...texts}
      onConfirm={() => blocker.proceed()}
      onCancel={() => blocker.reset()}
    />
  );
}
