import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Tauri expects a fixed dev port (see src-tauri/tauri.conf.json devUrl) and
// a relative asset base so the built bundle loads correctly from the
// file:// origin Tauri serves it from.
//
// Tailwind v4's first-party Vite plugin is the current recommended
// integration path (verified via tailwindcss.com/docs/installation/using-vite,
// fetched 2026-08-17): no tailwind.config.js/postcss.config.js needed, the
// plugin scans source files directly and CSS is driven by @import
// "tailwindcss" in src/index.css.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
  },
  build: {
    outDir: "dist",
  },
});
