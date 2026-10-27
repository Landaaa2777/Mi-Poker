import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// En desarrollo, el servidor de Vite reenvía el WebSocket y la API al backend.
// Sin cambiar la cabecera Host: el backend comprueba que las peticiones vienen
// de la misma página que ve el navegador (localhost:5173), y si no, las rechaza.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false },
    },
  },
});
