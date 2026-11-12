import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteStaticCopy } from "vite-plugin-static-copy";

const cesiumSrc = "node_modules/cesium/Build/Cesium";

export default defineConfig({
  plugins: [
    react(),
    // Cesium necesita sus Workers y Assets servidos como archivos estáticos.
    viteStaticCopy({
      targets: ["Workers", "ThirdParty", "Assets", "Widgets"].map((d) => ({
        src: `${cesiumSrc}/${d}`,
        dest: "cesium",
      })),
    }),
  ],
  define: { CESIUM_BASE_URL: JSON.stringify("/cesium") },
  server: { proxy: { "/api": "http://localhost:8000" } },
});
