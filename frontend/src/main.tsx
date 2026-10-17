import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";
import { GAME_PAGES } from "./games";
import { HubPage } from "./hub/HubPage";
import "./index.css";
import { Layout } from "./shared/Layout";

// Rutas: el menú en "/" y cada juego en "/<su id>", todos dentro del marco común.
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
