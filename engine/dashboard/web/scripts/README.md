# dashboard/web/scripts

Node-only verification scripts for the dashboard web frontend, run outside
the Vite dev/build pipeline. `dom-test.mjs` bundles the real app source
(via `src/testEntry.tsx`) with Vite into a classic IIFE script, loads it
into a real jsdom `Window`/`document` (jsdom does not execute inline
`type="module"` scripts, hence the IIFE format), stubs the
`window.__TAURI__.core.invoke` IPC boundary with real rows read from
`state/gate-runs.jsonl` plus the actual module/meme-event shapes, then
drives real `click()` events on each rail entry and asserts the main
panel renders distinct, non-empty content per entry with no fabricated
pass/fail status dot on a data-source that has no reader wired. This
exists because Playwright's browser deps are not installed in this
sandbox (no sudo); jsdom + a real Vite-built bundle is the closest
available substitute for a real-DOM click-through test. Run via
`npm run test:dom` from `dashboard/web`.
