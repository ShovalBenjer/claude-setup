import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri expects a fixed dev port (see src-tauri/tauri.conf.json devUrl) and
// a relative asset base so the built bundle loads correctly from the
// file:// origin Tauri serves it from.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
  },
  build: {
    outDir: "dist",
  },
});
