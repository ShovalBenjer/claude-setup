import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

// DASH-1 v2 test-only entry point: identical to main.tsx except it skips
// index.css (Tailwind is not needed to prove DOM structure/content, and
// the jsdom test harness runs this bundle outside a Vite dev/build
// pipeline that would resolve the CSS import). Never referenced by
// index.html or the shipped build -- only by scripts/dom-test.mjs.
createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
