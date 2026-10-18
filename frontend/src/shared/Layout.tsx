import { createContext, useContext, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Link, Outlet, useLocation } from "react-router";
import { AccountProvider, useAccount } from "./AccountContext";
import { AccountMenu } from "./components/AccountMenu";
import { Wordmark } from "./components/Emblem";
import { SettingsMenu } from "./components/SettingsMenu";
import { WelcomePage } from "./components/WelcomePage";
import { SettingsProvider, usePlatformSettings } from "./SettingsContext";

/** Huecos de la cabecera que rellena el juego que está en pantalla. */
interface HeaderSlots {
  info: HTMLElement | null; // junto al nombre: mano, fase, ciegas…
  actions: HTMLElement | null; // botones del juego, antes de "Menú"
}

const HeaderSlotsContext = createContext<HeaderSlots>({ info: null, actions: null });

/**
 * Pinta `info` y `actions` en la cabecera común, en los huecos reservados para
 * el juego. Se usa desde la página de cada juego.
 */
export function HeaderContent({ info, actions }: { info?: ReactNode; actions?: ReactNode }) {
  const slots = useContext(HeaderSlotsContext);
  return (
    <>
      {info && slots.info && createPortal(info, slots.info)}
      {actions && slots.actions && createPortal(actions, slots.actions)}
    </>
  );
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor" aria-hidden>
      <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.4" />
      <rect x="9" y="1.5" width="5.5" height="5.5" rx="1.4" />
      <rect x="1.5" y="9" width="5.5" height="5.5" rx="1.4" />
      <rect x="9" y="9" width="5.5" height="5.5" rx="1.4" />
    </svg>
  );
}

function Shell() {
  const account = useAccount();
  const { settings, update, animations, reducedMotion } = usePlatformSettings();
  const inGame = useLocation().pathname !== "/";
  const [info, setInfo] = useState<HTMLElement | null>(null);
  const [actions, setActions] = useState<HTMLElement | null>(null);

  return (
    <HeaderSlotsContext.Provider value={{ info, actions }}>
      <div className="mx-auto flex max-w-page flex-col gap-gutter p-3">
        <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
            <Link
              to="/"
              className="rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber-300"
              aria-label="mi-poker: ir al menú principal"
            >
              <Wordmark className="text-2xl" />
            </Link>
            <div ref={setInfo} className="contents" />
          </div>
          {/* En pantallas estrechas los botones bajan a otra fila en vez de salirse. */}
          <div className="flex flex-wrap items-center gap-2">
            <div ref={setActions} className="contents" />
            {inGame && (
              <Link
                to="/"
                className="btn-dark flex h-9 items-center gap-1.5 whitespace-nowrap px-3 text-sm"
              >
                <MenuIcon />
                Menú
              </Link>
            )}
            {account.user && (
              <AccountMenu
                user={account.user}
                balance={account.balance}
                disabled={account.signingOut}
                onSignOut={() => void account.signOut()}
                onProfile={account.openProfile}
              />
            )}
            <SettingsMenu
              settings={settings}
              animations={animations}
              reducedMotion={reducedMotion}
              onChange={update}
            />
          </div>
        </header>
        <main className="flex flex-col gap-gutter">
          {/* Sin cuenta no se juega: en cualquier dirección se pide entrar, y al
              entrar se ve lo que había en ella (el menú, una mesa o una sala). */}
          {account.ready &&
            (account.user ? (
              <Outlet />
            ) : (
              <WelcomePage onSignedIn={() => void account.refresh()} />
            ))}
        </main>
      </div>
    </HeaderSlotsContext.Provider>
  );
}

/** Marco de toda la plataforma: preferencias, cuenta, la cabecera común y la entrada sin sesión. */
export function Layout() {
  return (
    <SettingsProvider>
      <AccountProvider>
        <Shell />
      </AccountProvider>
    </SettingsProvider>
  );
}
