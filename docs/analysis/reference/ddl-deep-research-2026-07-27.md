# Deep research: platforms round 2, and the 3D question

Second research pass. Round 1 is COMPETITIVE-OSS-INVESTIGATION-2026-07-27.md
(FSRS, Exercism, freeCodeCamp, Duolingo). This covers three more platforms and
answers the operator's 3D and on-device-model question with measured numbers.

## Coverage boundary

Read at source or licence level this pass: `donnemartin/system-design-primer`
(licence text, solution index), `kamranahmedse/developer-roadmap` (licence text,
roadmap data index), `ossu/computer-science` (metadata and licence).

Verified by current web sources, not from model memory, because the cutoff makes
these unreliable: WebGPU status on iOS, iPhone Safari GPU memory limits, three.js
WebGPU renderer status, mobile polygon budgets.

Not investigated: Brilliant, boot.dev, Scrimba, Execute Program, Codecademy,
Khan Academy. All closed or partially closed; they would need behavioural study
rather than source reading.

## Platforms, round 2

### system-design-primer: the open ByteByteGo, and it is licence-clean

359k stars. **Licence: Creative Commons Attribution 4.0.** Free to use, adapt
and redistribute with attribution, including commercially.

This matters more than its star count. Our standing non-goal says no content
scraped from paid courses, which left ByteByteGo as an index only: we take the
chapter list and write every word ourselves. system-design-primer removes that
constraint for the parts it covers. It ships the primer plus eight fully worked
design solutions: pastebin, twitter, web crawler, mint, sales rank, social
graph, query cache, scaling AWS.

Change to M3: ByteByteGo stays the **index** because its 25-problem list is the
better interview map. system-design-primer becomes a **licence-clean source**
for the eight problems it overlaps, and for the primer concepts. Attribution
required and easy.

### developer-roadmap: the obvious thing to copy, and we cannot

362k stars, the biggest learning-path project in existence, and its roadmaps
include `ai-engineer`, which is the operator's primary resume arm.

**Licence, read in full: personal use only.** Verbatim: "You are allowed to use
this material for personal use but are not allowed to use it for any other
purpose including publishing the images, the project files or the content in the
images in any form either digital, non-digital, textual, graphical or written
formats."

So: he may read roadmap.sh. We may not derive our map from it, copy its node
lists, or adapt its content. Structure as an idea is not copyrightable; their
specific node sets and text are. The rule for this repo is that the roadmap
graph is re-derived from our own goals and ledger, and roadmap.sh is not opened
while doing it.

This is the single most important negative finding of the pass, because it is
the most tempting shortcut available.

### ossu/computer-science: MIT, and it seeds the PvE tree

207k stars, MIT. An open CS curriculum organised as a prerequisite graph over
free courses. MIT means we may adapt it.

It maps onto the PvE tree, which is currently the emptiest of the three: the
theory and personal-development side that has no enumerated content beyond the
judgment map. This is a licence-clean skeleton for it.

## The 3D question

The operator pointed at "I Built My Dream Game in 72 Hours, Assets by AI,
Gameplay by Claude Code" (channel Stefan 3D AI) and asked about fully autonomous
3D with Blender and Unreal capability, running on mobile.

### What has actually shipped

- **WebGPU is enabled by default in Safari on iOS 26**, built on Metal. Apple's
  mobile platform was the last holdout; it is no longer. GPU-accelerated 3D and
  GPU compute in a mobile browser are real as of now.
- **three.js r171+** exposes `WebGPURenderer` from `three/webgpu` with automatic
  WebGL2 fallback. MIT.
- Compression pipeline: glTF with **Draco** (50 to 80 per cent mesh reduction),
  **KTX2** textures (3 to 5 times smaller than JPG), LOD.

So the capability exists and is licence-clean. The question is budget.

### The measured gap, and it is large

Current mobile web budgets for 60fps: **under 10,000 polygons total** and
**under 100 draw calls**.

The video's own Blender viewport, read from a captured frame, reports
**110,975 triangles for a single building**.

That is roughly **eleven times the entire mobile budget, for one object**. A
scene of that fidelity cannot run at 60fps in mobile Safari. This is not a
pessimistic reading; it is one object against a whole-scene budget.

### What this means, honestly

The ambition is achievable, but not by porting that fidelity. Two facts point
the same way:

1. Mobile budget forces stylised low-poly with aggressive LOD.
2. The art references the operator named himself are Age of Empires 2, Diablo 2,
   MapleStory and World of Warcraft, all of which are **low-poly by
   construction**. AoE2 is sprites. Diablo 2 is pre-rendered sprites. Classic WoW
   models are a few thousand triangles.

So the budget and the taste agree. The path is stylised low-poly 3D at a few
thousand triangles per node, not photoreal Blender assets. That is achievable
and it is closer to what he asked for aesthetically than the video's fidelity
would be.

One prior decision to re-open honestly: `tree3d.js` is dead code scheduled for
deletion, and it was killed partly because the 3D board looked bad. Reintroducing
3D is a reversal. The difference is that the old one was an unlit WebGL board
with no art direction, and this would be an art-directed low-poly map on a
renderer that did not exist for iOS when the first attempt was made.

### Cost, stated before anyone commits

Adding three.js plus glTF assets breaks two standing positions: the vendored-only
posture grows by roughly 600KB to 1MB for three.js and loaders, and the offline
precache budget grows by the asset payload. It does not require a bundler, since
three.js ships ES modules that a browser can import directly, but it does mean
the service worker precache list and the CSP need revisiting.

This is a real trade and should be an ADR, not a silent change.

## The on-device model question

The operator proposed a lightweight WASM or local iPhone GPU model to control
the gameplay engine.

### Measured constraints

- iPhone Safari imposes per-buffer GPU memory limits from **256MB on older
  iPhones to about 993MB on iPad Pro**.
- Practical ceiling for browser LLM inference is about **8B parameters
  quantised**, and that is a desktop figure. On an iPhone the realistic band is
  **0.5B to 2B at 4-bit**, fitting in 1 to 2GB.
- WebLLM reaches roughly 80 per cent of native speed on desktop hardware; mobile
  is materially lower.

### Recommendation: no local chat model, yes local embeddings

**Reject the local chat model.** The teacher already runs against a frontier
model through the daemon. Swapping it for a 0.5B to 2B local model would be a
large downgrade at the one job that matters, in exchange for offline capability
we do not need for a conversation. It also costs a several-hundred-megabyte
download and constant memory pressure on the device the app must feel light on.

**Adopt a local embedding model instead.** A sentence-embedding model is
20 to 40MB, runs in WASM without needing WebGPU at all, and buys three things
the app actually wants and does not have:

- Semantic search over the codex, corpus and every closed unit, offline.
- "Find the unit that teaches this" without an exact-match keyword.
- Free-text answer grading by similarity to the reference answer, which is the
  cheap half of requirement R23 and works with no network.

That is a small, offline, instant capability with a clear job, rather than a
large one with a vague job.

## Per-feature enhancement, from both research passes

| Feature | Today | Enhanced by | Source |
|---|---|---|---|
| Review scheduling | Leitner ladder, 4 fixed steps | FSRS: difficulty, stability, retrievability, retention target, fuzz | ts-fsrs, MIT |
| Grade signal | ok plus confidence, collapsed to a boolean | four-level grade already derivable from data we collect | ts-fsrs |
| Unit graph | requires by unit id | teaches and requires by concept, plus kind, difficulty, status | Exercism |
| Drills | task text, hints in a details block | hint pairs of sentence and executable assertion, plus a seed stub | freeCodeCamp |
| M1 content | to be written | implementations with explanations, MIT with attribution | javascript-algorithms |
| M3 content | ByteByteGo index only, all prose written here | index stays, plus a CC BY 4.0 source for 8 problems and the primer | system-design-primer |
| PvE tree | empty beyond the judgment map | MIT prerequisite graph over free courses | ossu/computer-science |
| The map | flat 2D SVG board | art-directed low-poly 3D, WebGPU with WebGL2 fallback, under 10k polys | three.js, WebGPU on iOS 26 |
| Codex search | keyword | offline semantic search, 20-40MB WASM embedding model | transformers.js class of tooling |
| Teacher grading | none | similarity grading offline, frontier model over the daemon for real feedback | both |

## Changes this forces in the spec

1. M3 gains a licence-clean content source. Attribution line required.
2. PvE tree gains an MIT skeleton.
3. **A hard rule: roadmap.sh content is off limits.** Personal reading only.
4. 3D becomes a real option with a budget: under 10,000 polygons, under 100 draw
   calls, stylised low-poly, Draco plus KTX2 plus LOD. Needs an ADR because it
   grows the vendor payload and touches CSP and precache.
5. Local chat model rejected with reasons. Local embedding model adopted for
   search and similarity grading.
6. `tree3d.js` deletion stands. Any new 3D is a separate, art-directed build on
   a renderer that did not exist for iOS at the time of the first attempt.
