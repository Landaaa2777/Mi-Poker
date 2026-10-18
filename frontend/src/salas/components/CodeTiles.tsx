import { useEffect, useRef, useState } from "react";

interface TilesProps {
  code: string;
  /** Las letras entran volteándose una a una (la animación de "¡Partida encontrada!"). */
  reveal?: boolean;
}

/** El código de la sala en fichas grandes, una por carácter: fácil de leer y de dictar. */
export function CodeTiles({ code, reveal = false }: TilesProps) {
  return (
    <div className="flex justify-center gap-1.5 sm:gap-2" role="img" aria-label={`Código ${[...code].join(" ")}`}>
      {[...code].map((char, index) => (
        <span
          key={index}
          className={`${reveal ? "code-tile-in" : ""} flex h-12 w-10 items-center justify-center rounded-lg border border-amber-300/60 bg-gradient-to-b from-[#2b1a21] to-[#130a0e] font-numbers text-2xl font-black text-amber-200 shadow-[inset_0_1px_0_rgb(255_255_255/0.08),0_6px_14px_rgb(0_0_0/0.5)] sm:h-16 sm:w-12 sm:text-4xl`}
          style={reveal ? { animationDelay: `${140 + index * 90}ms` } : undefined}
          aria-hidden
        >
          {char}
        </span>
      ))}
    </div>
  );
}

/** Copia un texto: con el portapapeles del navegador o, si no lo deja (sin https), a la antigua. */
async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.append(area);
    area.select();
    const done = document.execCommand("copy");
    area.remove();
    return done;
  }
}

interface CopyProps {
  text: string;
  label: string;
  className?: string;
}

/** Botón que copia un texto y lo confirma un momento ("¡Copiado!"). */
export function CopyButton({ text, label, className = "btn-dark h-10 px-4 text-sm" }: CopyProps) {
  const [result, setResult] = useState<"copied" | "failed" | null>(null);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copy() {
    setResult((await copyText(text)) ? "copied" : "failed");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setResult(null), 1600);
  }

  return (
    <button type="button" className={className} onClick={() => void copy()} aria-live="polite">
      {result === "copied" ? "¡Copiado!" : result === "failed" ? "Cópialo a mano" : label}
    </button>
  );
}
