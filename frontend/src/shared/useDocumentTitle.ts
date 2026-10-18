import { useEffect } from "react";

/** Pone el título de la pestaña mientras la página está abierta (y deja el anterior al salir). */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    const previous = document.title;
    document.title = title;
    return () => {
      document.title = previous;
    };
  }, [title]);
}
