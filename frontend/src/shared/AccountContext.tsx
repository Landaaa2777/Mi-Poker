import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchMe, logout, type User } from "./account";
import { AccountDialog } from "./components/AccountDialog";
import { ProfileDialog } from "./components/ProfileDialog";

/**
 * La cuenta, vista desde toda la plataforma: el menú, la cabecera y cada juego.
 *
 * El saldo de la cabecera sigue al juego que esté en pantalla: una mesa fija
 * con `setTableBalance` el saldo que debe verse (al ritmo de sus animaciones);
 * fuera de las mesas se ve el que dice el servidor.
 */
export interface AccountState {
  user: User | null; // la cuenta con sesión iniciada; null = invitado
  ready: boolean; // ya se sabe quién soy
  /** Cambia al entrar o salir de una cuenta: las partidas vuelven a conectar con la nueva identidad. */
  identity: string;
  balance: number | null; // el saldo que se enseña ahora mismo; null si soy invitado
  /** Una mesa fija el saldo que debe verse; `undefined` deja de fijarlo. */
  setTableBalance: (balance: number | null | undefined) => void;
  refresh: () => Promise<void>; // vuelve a leer la cuenta del servidor
  openSignIn: () => void;
  openProfile: () => void;
  signOut: () => Promise<void>;
  signingOut: boolean;
}

const AccountContext = createContext<AccountState | null>(null);

export function useAccount(): AccountState {
  const account = useContext(AccountContext);
  if (!account) throw new Error("useAccount necesita un <AccountProvider> por encima");
  return account;
}

export function AccountProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [tableBalance, setTableBalanceState] = useState<number | null | undefined>(undefined);
  const [dialog, setDialog] = useState<"sign-in" | "profile" | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  const refresh = useCallback(async () => {
    setUser(await fetchMe());
    setReady(true);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setTableBalance = useCallback((balance: number | null | undefined) => {
    setTableBalanceState(balance);
  }, []);

  const signOut = useCallback(async () => {
    setDialog(null);
    setSigningOut(true);
    await logout();
    setSigningOut(false);
    await refresh();
  }, [refresh]);

  const value = useMemo<AccountState>(
    () => ({
      user,
      ready,
      identity: user ? `user:${user.username}` : "guest",
      balance: user ? (tableBalance === undefined ? user.balance : tableBalance) : null,
      setTableBalance,
      refresh,
      openSignIn: () => setDialog("sign-in"),
      openProfile: () => setDialog("profile"),
      signOut,
      signingOut,
    }),
    [user, ready, tableBalance, setTableBalance, refresh, signOut, signingOut],
  );

  return (
    <AccountContext.Provider value={value}>
      {children}
      {dialog === "sign-in" && (
        <AccountDialog
          onClose={() => setDialog(null)}
          onSignedIn={() => {
            setDialog(null);
            void refresh();
          }}
        />
      )}
      {dialog === "profile" && user && (
        <ProfileDialog
          user={user}
          balance={value.balance}
          onClose={() => setDialog(null)}
          onSignOut={() => void signOut()}
        />
      )}
    </AccountContext.Provider>
  );
}
