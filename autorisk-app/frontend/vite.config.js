import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Anything the frontend calls at /api/* during `npm run dev` gets
    // forwarded to FastAPI on port 8000. This avoids CORS entirely in
    // dev (the browser thinks it's all one origin: localhost:5173).
    proxy: {
      "/api": {
        // API_PROXY_TARGET lets the automated E2E tests (testing/e2e) point
        // a second dev server at their own backend + test database.
        target: process.env.API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
