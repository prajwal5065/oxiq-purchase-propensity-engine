import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxies /api/* to the FastAPI backend during local dev so the frontend
// never needs CORS config or a hardcoded absolute URL. In production,
// VITE_API_BASE_URL (see .env.example) points straight at the deployed API.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
