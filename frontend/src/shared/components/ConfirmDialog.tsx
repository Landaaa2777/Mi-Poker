import { useEffect, useId, useRef } from "react";

interface Props {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Ventana para confirmar algo importante. Escape o pulsar fuera es cancelar. */
export function ConfirmDialog({ title, message, confirmLabel, cancelLabel, onConfirm, onCancel }: Props) {
  const titleId = useId();
  const cancel = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // El foco empieza en la opción segura: seguir donde estaba.
    cancel.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="panel pop-in w-full max-w-sm p-5"
      >
        <h2 id={titleId} className="gold-text text-xl font-black">
          {title}
        </h2>
        <p className="mt-2 text-sm text-stone-300">{message}</p>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button ref={cancel} className="btn-dark h-10 px-4 text-sm" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button className="btn-gold h-10 px-4 text-sm" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
