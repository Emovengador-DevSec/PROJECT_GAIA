import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { viteStaticCopy } from "vite-plugin-static-copy";
import { spawn, type ChildProcess } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const cesiumSrc = "node_modules/cesium/Build/Cesium";
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const API_PORT = 8000; // internal only: bound to 127.0.0.1, reached through /api on 5173

// Starts the FastAPI backend together with `npm run dev`, so the whole app lives on localhost:5173.
// Set GAIA_EXTERNAL_API=1 to skip it when the API is already running elsewhere.
function gaiaApi(): Plugin {
  let child: ChildProcess | undefined;
  return {
    name: "gaia-api",
    apply: "serve",
    configureServer() {
      if (process.env.GAIA_EXTERNAL_API === "1" || child) return;
      child = spawn(
        "uv",
        ["run", "uvicorn", "app.main:app", "--app-dir", "services/api", "--host", "127.0.0.1", "--port", String(API_PORT), "--reload", "--reload-dir", "services/api"],
        { cwd: repoRoot, stdio: "inherit", shell: process.platform === "win32" },
      );
      const stop = () => { if (child && !child.killed) child.kill(); };
      process.once("exit", stop);
      process.once("SIGINT", () => { stop(); process.exit(0); });
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    gaiaApi(),
    // Cesium necesita sus Workers y Assets servidos como archivos estáticos.
    viteStaticCopy({
      targets: ["Workers", "ThirdParty", "Assets", "Widgets"].map((d) => ({
        src: `${cesiumSrc}/${d}`,
        dest: "cesium",
      })),
    }),
  ],
  define: { CESIUM_BASE_URL: JSON.stringify("/cesium") },
  server: { port: 5173, strictPort: true, proxy: { "/api": `http://127.0.0.1:${API_PORT}` } },
});
