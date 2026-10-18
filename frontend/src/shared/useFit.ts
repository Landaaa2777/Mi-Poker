import { useLayoutEffect, useRef, useState } from "react";

/** Un lienzo de tamaño fijo sobre el que se dibuja una mesa. */
export interface Canvas {
  width: number;
  height: number;
}

interface FitOptions {
  portraitBelow?: number; // ancho disponible por debajo del cual se usa el lienzo vertical
  maxHeightShare?: number; // en apaisado, parte del alto de la ventana que puede ocupar
  minScale?: number; // por debajo, el texto se vuelve ilegible: mejor desplazar la página
}

/**
 * Elige el lienzo (apaisado o vertical) y la escala para el ancho disponible.
 * La mesa se dibuja a tamaño fijo y se escala entera, como un tablero: así
 * nada se descoloca al cambiar el tamaño de la ventana.
 */
export function useFit<Layout extends Canvas>(
  landscape: Layout,
  portrait: Layout,
  { portraitBelow = 620, maxHeightShare = 0.66, minScale = 0.72 }: FitOptions = {},
) {
  const ref = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState({ layout: landscape, scale: 1 });

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const update = () => {
      const width = element.clientWidth;
      const layout = width < portraitBelow ? portrait : landscape;
      const byWidth = width / layout.width;
      const byHeight =
        layout === landscape ? (window.innerHeight * maxHeightShare) / layout.height : byWidth;
      const scale = Math.min(byWidth, Math.max(byHeight, minScale));
      setFit((current) =>
        current.layout === layout && current.scale === scale ? current : { layout, scale },
      );
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
    };
  }, [landscape, portrait, portraitBelow, maxHeightShare, minScale]);

  return { ref, ...fit };
}
