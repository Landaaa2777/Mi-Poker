import { lazy, StrictMode, Suspense, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";
import { GAME_PAGES } from "./games";
import { HubPage } from "./hub/HubPage";
import "./index.css";
import { Layout } from "./shared/Layout";

// Las salas con amigos se cargan al entrar en ellas, como los juegos.
const SalasPage = lazy(() => import("./salas/SalasPage"));
const SalaPage = lazy(() => import("./salas/SalaPage"));

function Loading({ children }: { children: ReactNode }) {
  return <Suspense fallback={<p className="panel px-3 py-2 text-sm">Cargando…</p>}>{children}</Suspense>;
}

// Rutas: el menú en "/", cada juego en "/<su id>" y las salas con amigos en
// "/salas" y "/sala/<código>", todos dentro del marco común.
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <HubPage /> },
      ...Object.entries(GAME_PAGES).map(([id, Page]) => ({
        path: id,
        element: (
          <Suspense fallback={<p className="panel px-3 py-2 text-sm">Cargando la mesa…</p>}>
            <Page />
          </Suspense>
        ),
      })),
      {
        path: "salas",
        element: (
          <Loading>
            <SalasPage />
          </Loading>
        ),
      },
      {
        path: "sala/:code",
        element: (
          <Loading>
            <SalaPage />
          </Loading>
        ),
      },
      // Una dirección que no existe lleva al menú.
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
