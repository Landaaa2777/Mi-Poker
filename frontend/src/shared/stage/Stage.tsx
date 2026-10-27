import { useLayoutEffect, useMemo, useRef, type CSSProperties, type ReactNode, type Ref } from "react";
import type { TableView } from "../settings";
import { onPlane, project, stageFor, type Camera, type Point, type Stage3D } from "./camera";
import { registerStage } from "./measure";

// El escenario de una mesa: el mismo lienzo de siempre, plano (2D) o con el
// tapete inclinado en perspectiva (3D).
//
// Cada mesa reparte lo que dibuja en dos capas:
// - `table`: lo que está sobre el tapete (cartas, mazo, dibujos del tapete).
//   En 3D se tumba con él, en perspectiva.
// - `hud`: lo que se tiene que leer (placas, nombres, avisos, fichas). En 3D
//   va plano por encima, en el punto de la pantalla donde cae su sitio.
// En 2D las dos capas van juntas en el mismo lienzo, como siempre.

/** Cómo colocar cada cosa en el escenario, según la vista. */
export interface Placement {
  view: TableView;
  stage: Stage3D | null; // null en 2D
  /** Posición (left/top) de algo que va sobre el tapete. */
  onTable: (point: Point) => CSSProperties;
  /**
   * Posición de algo que va en la capa de encima. En 3D se encoge con la
   * distancia: "full" como lo que está en la mesa, "soft" a medias (para que
   * los textos lejanos se sigan leyendo), "none" nada.
   */
  overTable: (point: Point, depth?: "full" | "soft" | "none") => CSSProperties;
  /** Escala de la perspectiva en un punto (1 en 2D). */
  depthAt: (point: Point) => number;
  /**
   * Cuánto ocupa en el lienzo 2D algo de `length` px tumbado en el tapete. En
   * 3D, lo tumbado se ve acortado (las cartas, por ejemplo); en 2D, igual.
   */
  lying: (length: number) => number;
}

const flat = (point: Point): CSSProperties => ({ left: point.x, top: point.y });

/** Las medidas de la mesa para la vista elegida. `camera` tiene que ser siempre el mismo objeto. */
export function usePlacement(view: TableView, layout: { width: number; height: number }, camera: Camera): Placement {
  return useMemo(() => {
    if (view === "2d") {
      return { view, stage: null, onTable: flat, overTable: flat, depthAt: () => 1, lying: (length) => length };
    }
    const stage = stageFor(layout.width, layout.height, camera);
    return {
      view,
      stage,
      onTable: (point) => flat(onPlane(stage, point)),
      overTable: (point, depth = "soft") => {
        const seen = project(stage, point);
        const scale = depth === "full" ? seen.depth : depth === "soft" ? 1 - (1 - seen.depth) * 0.5 : 1;
        return { left: seen.x, top: seen.y, scale: scale.toFixed(4) };
      },
      depthAt: (point) => project(stage, point).depth,
      lying: (length) => length / stage.stretch,
    };
  }, [view, layout, camera]);
}

/** El alto de un lienzo en 3D, para ajustar la mesa a la ventana (ver `useFit`). */
export function stageHeight(camera: (layout: { width: number; height: number }) => Camera) {
  return (layout: { width: number; height: number }) =>
    stageFor(layout.width, layout.height, camera(layout)).stageHeight;
}

interface Props {
  placement: Placement;
  layout: { width: number; height: number };
  scale: number; // escala a la que se dibuja el lienzo entero
  height: number; // alto del lienzo (en 3D, el de la mesa inclinada)
  label: string; // nombre de la mesa para los lectores de pantalla
  shape: string; // clases de la forma del tapete (esquinas redondeadas)
  shapeStyle?: CSSProperties; // forma que no cabe en una clase
  shade: string; // sombreado del tapete hacia los bordes
  table: ReactNode;
  hud?: ReactNode;
  sectionRef: Ref<HTMLElement>;
}

/** La mesa entera: tapete, lo que hay sobre él, la capa de encima y las capas de efectos. */
export function Stage({ placement, layout, scale, height, label, shape, shapeStyle, shade, table, hud, sectionRef }: Props) {
  const canvas = useRef<HTMLDivElement>(null);
  const { stage } = placement;
  useLayoutEffect(() => {
    if (stage && canvas.current) registerStage(canvas.current, stage);
  }, [stage]);

  if (!stage) {
    return (
      <section
        ref={sectionRef}
        className={`felt rim relative w-full overflow-hidden ${shape}`}
        style={{ height: layout.height * scale, ...shapeStyle }}
        aria-label={label}
        data-view="2d"
      >
        {/* Sombra hacia los bordes, para dar profundidad al tapete. */}
        <div className={`absolute inset-0 ${shade}`} />
        <div
          ref={canvas}
          data-canvas
          className="absolute left-1/2 top-0 origin-top"
          style={{ width: layout.width, height: layout.height, transform: `translateX(-50%) scale(${scale})` }}
        >
          {table}
          {hud}
          {/* Capa de efectos: por aquí cruzan las fichas y las cartas que se retiran. */}
          <div data-zone="fx" className="pointer-events-none absolute inset-0 z-40" />
        </div>
      </section>
    );
  }

  return (
    <section ref={sectionRef} className="stage-3d relative w-full" style={{ height: height * scale }} aria-label={label} data-view="3d">
      <div
        ref={canvas}
        data-canvas
        className="absolute left-1/2 top-0 origin-top"
        style={{
          width: layout.width,
          height: stage.stageHeight,
          transform: `translateX(-50%) scale(${scale})`,
          perspective: `${stage.distance}px`,
          perspectiveOrigin: `${layout.width / 2}px ${stage.originY}px`,
        }}
      >
        {/* El canto de la mesa: dos capas de madera bajo el tapete que asoman por
            delante. Van fuera del tapete (cada una plana, con su perspectiva): así
            el navegador no tiene que ordenarlas en 3D con las cartas en cada fotograma. */}
        {/* Sombra de la mesa en el suelo, bajo su borde cercano. */}
        <div
          aria-hidden
          className="stage-floor"
          style={{ left: "6%", width: "88%", top: stage.base - 50, height: 120 }}
        />
        {[26, 12].map((depth) => (
          <div
            key={depth}
            aria-hidden
            className={`stage-edge ${depth > 20 ? "stage-edge-low" : "stage-edge-high"} ${shape}`}
            style={{
              ...shapeStyle,
              top: stage.planeTop,
              width: layout.width,
              height: stage.planeHeight,
              transform: `rotateX(${stage.tilt}deg) translateZ(-${depth}px)`,
            }}
          />
        ))}
        {/* El tapete, inclinado sobre su borde cercano. */}
        <div
          data-plane
          className="stage-plane absolute left-0"
          style={{
            top: stage.planeTop,
            width: layout.width,
            height: stage.planeHeight,
            transform: `rotateX(${stage.tilt}deg)`,
          }}
        >
          <div className={`felt rim absolute inset-0 overflow-hidden ${shape}`} style={shapeStyle}>
            <div className={`absolute inset-0 ${shade}`} />
          </div>
          <div className="stage-top absolute inset-0">{table}</div>
          {/* Capa de efectos tumbada en el tapete: cartas que se retiran deslizándose. */}
          <div data-zone="fx-table" className="stage-top pointer-events-none absolute inset-0" />
        </div>
        <div className="stage-hud absolute inset-0">{hud}</div>
        {/* Capa de efectos plana, por encima de todo: fichas que vuelan. */}
        <div data-zone="fx" className="pointer-events-none absolute inset-0 z-40" />
      </div>
    </section>
  );
}
