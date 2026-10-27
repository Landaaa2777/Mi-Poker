import { useEffect, useRef, useState } from "react";
import { audio } from "../audio/engine";
import type { Settings, TableView } from "../settings";
import { ViewSwitch } from "./ViewSwitch";

interface Props {
  settings: Settings;
  animations: boolean; // valor efectivo: lo elegido o, si no se eligió, lo que pide el sistema
  reducedMotion: boolean; // el sistema pide reducir el movimiento
  view: TableView; // vista de las mesas en uso
  onChange: (changes: Partial<Settings>) => void;
}

function SpeakerIcon({ muted }: { muted: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" fill="currentColor" />
      {muted ? (
        <path d="M16 9.5l5 5m0-5l-5 5" />
      ) : (
        <path d="M15.5 9a4.2 4.2 0 0 1 0 6M18 6.5a7.8 7.8 0 0 1 0 11" />
      )}
    </svg>
  );
}

interface SliderProps {
  label: string;
  value: number; // de 0 a 1
  onChange: (value: number) => void;
  onRelease?: () => void;
}

function VolumeSlider({ label, value, onChange, onRelease }: SliderProps) {
  const percent = Math.round(value * 100);
  return (
    <label className="grid grid-cols-[4.5rem_1fr_2.2rem] items-center gap-2 text-sm">
      <span>{label}</span>
      <input
        type="range"
        min={0}
        max={100}
        step={1}
        value={percent}
        aria-label={`Volumen de ${label.toLowerCase()}`}
        onChange={(event) => onChange(Number(event.target.value) / 100)}
        onPointerUp={onRelease}
        onKeyUp={onRelease}
      />
      <span className="text-right tabular-nums text-stone-400">{percent}</span>
    </label>
  );
}

/** Controles de audio y de animaciones: un botón para silenciar y un panel pequeño. */
export function SettingsMenu({ settings, animations, reducedMotion, view, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  // El panel se cierra con Escape o al pulsar fuera.
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    const onPointer = (event: PointerEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  const toggleMute = () => onChange({ muted: !settings.muted });

  return (
    <div ref={container} className="relative flex items-center gap-2">
      <button
        className={`flex h-9 w-9 items-center justify-center ${settings.muted ? "btn-red" : "btn-dark"}`}
        aria-pressed={settings.muted}
        aria-label={settings.muted ? "Activar el sonido" : "Silenciar todo"}
        title={settings.muted ? "Activar el sonido" : "Silenciar todo"}
        onClick={toggleMute}
      >
        <SpeakerIcon muted={settings.muted} />
      </button>
      <button
        className="btn-dark h-9 px-3 text-sm"
        aria-expanded={open}
        aria-controls="settings-panel"
        onClick={() => setOpen((current) => !current)}
      >
        Ajustes
      </button>

      {open && (
        <div
          id="settings-panel"
          className="panel absolute right-0 top-full z-30 mt-2 w-72 space-y-3 p-4 shadow-2xl"
        >
          <h2 className="gold-text text-xs font-extrabold uppercase tracking-[0.16em]">Sonido</h2>
          <VolumeSlider
            label="Música"
            value={settings.musicVolume}
            onChange={(musicVolume) => onChange({ musicVolume })}
          />
          <VolumeSlider
            label="Efectos"
            value={settings.effectsVolume}
            onChange={(effectsVolume) => onChange({ effectsVolume })}
            // Al soltar suena una muestra, para oír cómo ha quedado.
            onRelease={() => audio.play("chips")}
          />
          <button
            className={`w-full px-3 py-2 text-sm ${settings.muted ? "btn-red" : "btn-dark"}`}
            aria-pressed={settings.muted}
            onClick={toggleMute}
          >
            {settings.muted ? "Silenciado: pulsa para activar" : "Silenciar todo"}
          </button>

          <div className="border-t border-amber-400/25 pt-3">
            <h2 className="gold-text text-xs font-extrabold uppercase tracking-[0.16em]">Mesa</h2>
            <div className="mt-2 flex items-center justify-between gap-3 text-sm">
              <span>Vista</span>
              <ViewSwitch view={view} onChange={(next) => onChange({ view: next })} />
            </div>
            <p className="mt-1 text-xs text-stone-400">
              {view === "3d"
                ? "Mesa en perspectiva: cartas y fichas con relieve y física."
                : "Mesa plana, vista desde arriba, como siempre."}
            </p>
          </div>

          <div className="border-t border-amber-400/25 pt-3">
            <label className="flex cursor-pointer items-center justify-between gap-3 text-sm">
              <span>Animaciones</span>
              <input
                type="checkbox"
                className="h-4 w-4 accent-amber-400"
                checked={animations}
                onChange={(event) => onChange({ animations: event.target.checked })}
              />
            </label>
            <p className="mt-1 text-xs text-stone-400">
              {animations
                ? "La mano se reproduce paso a paso."
                : "Cada jugada se muestra al instante."}
              {reducedMotion && " Tu sistema pide reducir el movimiento."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
