import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 백엔드(FastAPI :8000)로 /api, /ws 프록시
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // 5173 고정 (폴백 포트로 인한 stop 누락 방지)
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
