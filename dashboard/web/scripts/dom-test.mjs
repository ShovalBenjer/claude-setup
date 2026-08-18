// DASH-1 v2 verification: a real-DOM content-diff test, the jsdom
// approach named in the task (Playwright browser deps are missing in
// this sandbox, no sudo -- confirmed, not assumed). Bundles the app's
// real testEntry.tsx with Vite (same React/TS source the shipped build
// uses, only main.tsx swapped for one that skips the CSS import), loads
// the bundle into a real jsdom Window/document, stubs
// window.__TAURI__.core.invoke to answer with real rows read from
// state/gate-runs.jsonl and the actual ModuleDescriptor/MemeEvent shapes
// (the IPC boundary the webview would normally supply -- not fabricated
// product data), then drives real click() calls on each rail button and
// asserts the main panel's rendered text differs and is non-empty per
// entry. This proves the redesigned rail actually routes to distinct
// content, the same class of bug PR #85 fixed for the old sidebar.
import { build } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { JSDOM, VirtualConsole } from "jsdom";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, "..");
const repoRoot = join(webRoot, "..", "..");

function realGateRunRows(limit) {
  const path = join(repoRoot, "state", "gate-runs.jsonl");
  const lines = readFileSync(path, "utf8").trim().split("\n");
  const tail = lines.slice(-limit);
  const rows = [];
  let skipped = 0;
  for (const line of tail) {
    try {
      const raw = JSON.parse(line);
      rows.push({
        ts: raw.ts,
        project: raw.project,
        project_path: raw.project_path,
        commit: raw.commit,
        dirty: raw.dirty,
        fingerprint: raw.fingerprint,
        partial: raw.partial,
        verdict: raw.verdict === "PASS" ? "pass" : raw.verdict === "FAIL" ? "fail" : raw.verdict === "PARTIAL" ? "partial" : { unknown: String(raw.verdict) },
        domains: raw.domains ?? {},
        blocking: raw.blocking ?? [],
        waivers_unconfirmed: raw.waivers_unconfirmed ?? [],
        unmeasured: raw.unmeasured ?? [],
        duration_seconds: raw.duration_seconds ?? null,
        domain_seconds: raw.domain_seconds ?? null,
      });
    } catch {
      skipped += 1;
    }
  }
  return { rows, skipped, total_lines: lines.length, first_error: null };
}


async function bundleTestEntry() {
  const result = await build({
    root: webRoot,
    logLevel: "warn",
    plugins: [tailwindcss(), react()],
    define: { "process.env.NODE_ENV": JSON.stringify("production") },
    build: {
      write: false,
      minify: false,
      target: "es2020",
      lib: {
        entry: join(webRoot, "src", "testEntry.tsx"),
        formats: ["iife"],
        name: "DashTestBundle",
        fileName: () => "test-bundle.js",
      },
      rollupOptions: {
        output: { inlineDynamicImports: true },
      },
    },
  });
  const chunks = Array.isArray(result) ? result : [result];
  const output = chunks[0].output[0];
  return output.code;
}

function makeInvokeStub() {
  const gateReport = realGateRunRows(20);
  // Force a known verdict on the *latest* row rather than trusting
  // whatever state/gate-runs.jsonl happens to end with (that tail is
  // real but not deterministic across runs/branches). This is what makes
  // the assertion below meaningful: gate-runs and overview dots must
  // read exactly "fail" here, not merely "a valid tone", so the test
  // proves the dot is actually wired to GateRun.verdict and not left at
  // its "unknown" default.
  const KNOWN_LATEST_VERDICT = "fail";
  const gateReportWithKnownLatest = {
    ...gateReport,
    rows: gateReport.rows.length
      ? [
          ...gateReport.rows.slice(0, -1),
          { ...gateReport.rows[gateReport.rows.length - 1], verdict: KNOWN_LATEST_VERDICT },
        ]
      : gateReport.rows,
  };
  const latestRun = gateReportWithKnownLatest.rows[gateReportWithKnownLatest.rows.length - 1] ?? null;
  const modules = [{ id: "meme", name: "Meme events", enabled: true }];
  const memeEvents = [
    { id: "ev-1", query: "tests failed", trigger: "gate:fail" },
    { id: "ev-2", query: "ship it", trigger: "gate:pass" },
  ];
  return async function invoke(cmd, args) {
    switch (cmd) {
      case "latest_gate_verdict":
        return latestRun;
      case "read_gate_runs":
        return gateReportWithKnownLatest;
      case "read_agent_spawns_cmd":
        return { rows: [], skipped: 0, total_lines: 0, first_error: null };
      case "list_modules":
        return modules;
      case "set_module_enabled":
        return undefined;
      case "meme_list_events":
        return memeEvents;
      case "meme_find":
        return [{ hub: "reaction-images", score: 0.91, queries: [String(args?.query ?? "")] }];
      default:
        throw new Error(`dom-test.mjs invoke stub: unhandled command ${cmd}`);
    }
  };
}

function summarizeText(el) {
  return el.textContent.replace(/\s+/g, " ").trim();
}

async function flushMicrotasksAndTimers(dom, rounds = 20) {
  for (let i = 0; i < rounds; i++) {
    await new Promise((resolve) => dom.window.setTimeout(resolve, 10));
  }
}

async function main() {
  const code = await bundleTestEntry();

  const virtualConsole = new VirtualConsole();
  for (const level of ["log", "info", "warn", "error", "debug"]) {
    virtualConsole.on(level, (...args) => console[level]("[jsdom console]", ...args));
  }
  virtualConsole.on("jsdomError", (err) => {
    console.error("jsdom error:", err.message, err.detail ? String(err.detail).slice(0, 2000) : "");
  });
  const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
    url: "http://localhost/",
    runScripts: "dangerously",
    pretendToBeVisual: true,
    virtualConsole,
  });

  dom.window.__TAURI__ = { core: { invoke: makeInvokeStub() } };

  const scriptEl = dom.window.document.createElement("script");
  scriptEl.textContent = code;
  dom.window.document.body.appendChild(scriptEl);

  await flushMicrotasksAndTimers(dom, 30);

  const root = dom.window.document.getElementById("root");
  if (!root || !root.textContent.trim()) {
    throw new Error("root did not render any content -- App failed to mount in jsdom");
  }

  const railButtons = Array.from(root.querySelectorAll("[data-rail-entry]"));
  if (railButtons.length < 4) {
    throw new Error(`expected at least 4 rail entries, found ${railButtons.length}`);
  }
  console.log(`rail entries found: ${railButtons.map((b) => b.getAttribute("data-rail-entry")).join(", ")}`);

  const seen = new Map();
  for (const btn of railButtons) {
    const view = btn.getAttribute("data-rail-entry");
    btn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    await flushMicrotasksAndTimers(dom, 15);
    const main2 = dom.window.document.querySelector("main");
    const text = summarizeText(main2);
    if (!text) {
      throw new Error(`view "${view}" rendered empty main content after click`);
    }
    seen.set(view, text);
    console.log(`[${view}] -> ${text.slice(0, 140)}${text.length > 140 ? "..." : ""}`);
  }

  const texts = Array.from(seen.values());
  const distinct = new Set(texts);
  if (distinct.size !== texts.length) {
    throw new Error(`expected every rail entry to render distinct main content, got ${distinct.size} distinct out of ${texts.length}`);
  }

  const dots = Array.from(root.querySelectorAll("[data-status-dot]"));
  if (dots.length === 0) {
    throw new Error("no status dots rendered on the rail");
  }
  const badTone = dots.find((d) => !["pass", "fail", "partial", "unknown"].includes(d.getAttribute("data-status-dot")));
  if (badTone) {
    throw new Error(`status dot with invalid tone: ${badTone.getAttribute("data-status-dot")}`);
  }
  const railDots = Array.from(root.querySelectorAll("[data-rail-entry] [data-status-dot]"));
  const ticketsDot = railDots.find((d) => d.closest("[data-rail-entry]")?.getAttribute("data-rail-entry") === "prompt-tickets");
  const spawnsDot = railDots.find((d) => d.closest("[data-rail-entry]")?.getAttribute("data-rail-entry") === "agent-spawns");
  if (ticketsDot && ticketsDot.getAttribute("data-status-dot") !== "unknown") {
    throw new Error(`prompt-tickets rail dot must be "unknown" (no reader wired), got "${ticketsDot.getAttribute("data-status-dot")}"`);
  }
  if (spawnsDot && spawnsDot.getAttribute("data-status-dot") !== "unknown") {
    throw new Error(`agent-spawns rail dot must be "unknown" (reader is a stub), got "${spawnsDot.getAttribute("data-status-dot")}"`);
  }

  // Assert the gate-runs (and overview) rail dot is actually driven by
  // GateRun.verdict, not merely present with a valid-looking tone. The
  // stub above pins the latest row's verdict to a known value ("fail"),
  // so this checks the rendered dot equals that exact tone -- a dot stuck
  // at its "unknown" default would pass every other assertion in this
  // file but fail this one.
  const gateRunsDot = railDots.find((d) => d.closest("[data-rail-entry]")?.getAttribute("data-rail-entry") === "gate-runs");
  if (!gateRunsDot) {
    throw new Error("gate-runs rail entry has no status dot");
  }
  if (gateRunsDot.getAttribute("data-status-dot") !== "fail") {
    throw new Error(`gate-runs rail dot must reflect the known latest verdict "fail", got "${gateRunsDot.getAttribute("data-status-dot")}"`);
  }
  const overviewDot = railDots.find((d) => d.closest("[data-rail-entry]")?.getAttribute("data-rail-entry") === "overview");
  if (overviewDot && overviewDot.getAttribute("data-status-dot") !== "fail") {
    throw new Error(`overview rail dot must reflect the same latest verdict, got "${overviewDot.getAttribute("data-status-dot")}"`);
  }

  console.log("PASS: all rail entries render distinct, non-empty content; no fabricated pass/fail dots on unwired sources");
  dom.window.close();
}

main().catch((err) => {
  console.error("FAIL:", err.message);
  process.exit(1);
});
