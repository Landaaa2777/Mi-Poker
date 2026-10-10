import { useState } from "react";
import { ConfigPanel } from "./components/ConfigPanel";
import { Controls } from "./components/Controls";
import { HandLog } from "./components/HandLog";
import { ResultPanel } from "./components/ResultPanel";
import { Table } from "./components/Table";
import { useGame } from "./useGame";

const NOTICE = "Solo para entretenimiento. Sin dinero real.";

export default function App() {
  const { connected, options, state, error, send } = useGame();
  const [configuring, setConfiguring] = useState(false);
  const showConfig = options !== null && (state === null || configuring);

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">mi-poker</h1>
        <p className="rounded bg-amber-500 px-3 py-1 text-sm font-semibold text-slate-900">
          {NOTICE}
        </p>
      </header>

      {!connected && (
        <p className="rounded bg-slate-700 px-3 py-2 text-sm">Conectando con el servidor…</p>
      )}
      {error && (
        <p role="alert" className="rounded bg-rose-800 px-3 py-2 text-sm">
          {error}
        </p>
      )}

      {showConfig && (
        <ConfigPanel
          options={options}
          initial={state?.config ?? options.defaults}
          onStart={(config) => {
            send({ type: "new_game", config });
            setConfiguring(false);
          }}
          onCancel={state ? () => setConfiguring(false) : undefined}
        />
      )}

      {state && !showConfig && (
        <>
          <Table state={state} />
          <Controls
            state={state}
            onAction={(action, amount) => send({ type: "action", action, amount: amount ?? 0 })}
          />
          <ResultPanel
            state={state}
            onNextHand={() => send({ type: "next_hand" })}
            onRestart={() => send({ type: "restart" })}
            onConfigure={() => setConfiguring(true)}
          />
          <HandLog state={state} />
          <footer className="flex items-center justify-between text-xs text-slate-400">
            <span>Las fichas son virtuales y no tienen valor fuera del juego.</span>
            <button className="underline" onClick={() => setConfiguring(true)}>
              Nueva partida
            </button>
          </footer>
        </>
      )}
    </div>
  );
}
