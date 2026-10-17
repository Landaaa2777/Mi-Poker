import type { ReactNode } from "react";
import { useBlocker } from "react-router";
import { ConfirmDialog } from "./components/ConfirmDialog";

/**
 * Al salir de un juego con una partida en curso (botón Menú, el nombre del
 * juego, la flecha de atrás del navegador…) se pide confirmación. La partida no
 * se pierde: queda en pausa en el servidor y el menú ofrece continuarla.
 *
 * Devuelve la ventana de confirmación cuando hace falta enseñarla; el juego la
 * pinta donde quiera.
 */
export function useLeaveGuard(inProgress: boolean): ReactNode {
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      inProgress && currentLocation.pathname !== nextLocation.pathname,
  );
  if (blocker.state !== "blocked") return null;
  return (
    <ConfirmDialog
      title="¿Volver al menú?"
      message="Tu partida queda en pausa: podrás continuarla desde el menú cuando quieras."
      confirmLabel="Ir al menú"
      cancelLabel="Seguir jugando"
      onConfirm={() => blocker.proceed()}
      onCancel={() => blocker.reset()}
    />
  );
}
