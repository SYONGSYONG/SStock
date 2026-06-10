import { resolve } from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// 포트/호스트는 저장소 루트 .env 한 곳에서 읽는다(단일 출처). 미설정 시 기본값 사용.
// 백엔드는 같은 PC 안에서 프록시로 전달되므로 BACKEND_HOST는 보통 127.0.0.1 유지.
export default defineConfig(({ mode }) => {
  const repoRoot = resolve(process.cwd(), "..");
  const env = loadEnv(mode, repoRoot, ""); // prefix="" → 루트 .env의 모든 키 로드(시크릿 없음)

  const backendHost = env.BACKEND_HOST || "127.0.0.1";
  const backendPort = env.BACKEND_PORT || "8000";
  const frontendPort = Number(env.FRONTEND_PORT || "8001");
  // FRONTEND_HOST=true → 0.0.0.0(LAN 노출). 그 외 문자열(127.0.0.1 등)은 그대로 바인딩.
  const frontendHost: string | boolean =
    env.FRONTEND_HOST === "true" ? true : env.FRONTEND_HOST || "127.0.0.1";

  return {
    plugins: [react()],
    server: {
      host: frontendHost,
      port: frontendPort,
      strictPort: true, // 포트 고정(폴백으로 인한 stop 누락 방지)
      proxy: {
        "/api": { target: `http://${backendHost}:${backendPort}`, changeOrigin: true },
        "/ws": { target: `ws://${backendHost}:${backendPort}`, ws: true },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test-setup.ts"],
    },
  };
});
