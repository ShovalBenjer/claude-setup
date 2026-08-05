# Next-Gen Game-Grade Design Research (2026-07-23)

Status: active. Supersedes UI-DEEP-RESEARCH-ARKHERON.md as the design-direction
source (Arkheron doc stays as a reference corpus). Commissioned after the
operator rejected the incremental material pass ("looks lame") and unfroze all
design work. Research: 28 verified web searches/fetches by a dedicated agent +
a full sweep of the operator's Perplexity corpus. Every claim carries a URL;
unverifiable items were dropped.

## Why the last pass failed (the honest diagnosis)

It was CSS increments on the same layout: better borders, same bones. No
fiction, no bespoke assets, no motion identity, no scene. Research confirms
this entire class of change reads as default-follower in 2026:

- Glassmorphism/Liquid Glass is now contested, not premium. Apple is publicly
  rowing back after readability backlash and record-low ~45% adoption
  (https://techcrunch.com/2026/06/08/apple-is-tweaking-its-controversial-liquid-glass-design/,
  https://www.geeky-gadgets.com/apple-liquid-glass-adoption-rate/).
- The replacement movement is tactile maximalism: layered textured surfaces,
  scanned paper, grain, fabric, metal
  (https://www.snix.mt/post/tactile-maximalism-web-design-2026,
  https://wannathis.one/blog/web-design-trends-2026).
- Awwwards Site of the Year 2025 is Ponpon Mania, a 100% hand-illustrated
  WebGL comic (https://www.awwwards.com/sites/ponpon-mania). The year's best
  site is bespoke drawing, not glass panels.

## Operator-corpus anchors (his own words set the bar)

- "Feels generic ui slop" doc (Perplexity, 2026-07): gradient banners scream
  template; identical clone cards scream template; emoji cliches; placeholder
  mad-libs; design vocabulary must anchor to something REAL, not an invented
  palette mashup. Restraint where structure doesn't earn its place.
- Terminal-renaissance doc: he studies bespoke renderer identity (Claude
  Code's Ink internals) — motion/renderer identity is a thing he values.
- Living Codex build prompt: dark academia, quest cards, XP trees, motes — his
  own original fiction vocabulary.
- Rejection history (5 passes): slop-merge, non-WoW tree, compressed feel,
  generic-AI, lame material pass. Pattern: he rejects DECORATION and accepts
  only committed, specific, layered worlds.

---

# The agent's full report

## Track 1 — Open-source game-UI implementations worth studying

Skinning frameworks (the "every element gets the fiction" pattern):
- RPGUI — https://github.com/RonenNess/RPGUI — 953★, zlib. Complete old-school
  RPG GUI in CSS: 4 framed-container styles, styled sliders/progress/dropdowns,
  pixel cursors. Demo https://ronenness.github.io/RPGUI/. TAKE: the
  framed-container taxonomy — every panel/list/control skinned under one
  fiction, cursor included. Inactive since 2016: lift technique, not dependency.
- NES.css — https://github.com/nostalgic-css/NES.css — 21.8k★, MIT. TAKE: the
  discipline of skinning EVERY element (inputs, radios, dialogs, badges) so no
  element breaks the fiction. The star count proves totality is what people love.
- PSone.css — https://github.com/micah5/PSone.css — era icon set + type as
  identity carrier.
- Genre index — https://github.com/matt-auckland/retro-css — the genre stalled
  at retro pastiche; no strong 2024-26 successor. That gap is exactly what a
  custom "game academy" identity can occupy.

Asset corpora (CC0/open — raw material for bespoke frames):
- Kenney UI Pack — https://kenney.nl/assets/ui-pack — 430+ UI sprites, CC0,
  vector sources; companion UI Audio pack https://kenney.nl/assets/ui-audio.
  TAKE: 9-slice-ready panels + the sound layer of juice, zero licensing cost.
- Fantasy UI Borders — https://opengameart.org/content/fantasy-ui-borders —
  130+ ornate 9-slice border PNGs.
- wow-ui-textures — https://github.com/Gethe/wow-ui-textures (+ wow-ui-source)
  — study-only mirror of Blizzard's actual frame construction (corner pieces,
  edge repeats, inset shadows). Study the construction, never ship the assets.

Shader-driven and hybrid UI:
- curtains.js — https://github.com/martinlaxenaire/curtainsjs — MIT, WebGL
  planes that track DOM position/scroll. Lowest-friction shader-UI path.
- Codrops corpus — https://github.com/codrops; 2025 pieces: WebGL shader
  transitions (tympanus.net/codrops/2025/01/22/) and real-time dithering
  (tympanus.net/codrops/2025/06/04/).
- tsParticles — https://github.com/tsparticles/tsparticles — MIT, vanilla
  particles/confetti/fireworks.
- Theatre.js — https://github.com/theatre-js/theatre — 11k★, keyframe any JS
  variable; editor-precision choreography shipped as plain JS.
- afterglow-crt — https://github.com/HauntedCrusader/afterglow-crt — MIT,
  pure-CSS CRT overlay driven by 15+ CSS variables. Canonical write-up:
  https://aleclownes.com/2017/02/01/crt-display.html.
- nine-slice-frame — https://github.com/callum-gander/nine-slice-frame — ~1KB
  modern 9-slice component.

Web games with readable source (proof of ceiling):
- Vampire Survivors ran on Phaser (HTML5/JS) until v1.6 —
  https://phaser.io/news/2024/02/vampire-survivors-space-54. A game that sold
  millions shipped its FEEL (screenshake, damage numbers) on browser tech.
  The ceiling is not the platform.
- shapez.io — https://github.com/tobspr-games/shapez.io — MIT, shipped Steam
  game; HTML/CSS chrome over canvas (the hybrid pattern).
- Sandspiel — https://github.com/MaxBittker/sandspiel — minimal chrome around
  a living simulation; restraint makes the toy feel premium.

## Track 2 — What next-gen looks like (named winners 2025-26)

1. Ponpon Mania — Site of the Year 2025 — hand-illustrated WebGL comic; one
   fiction, creative code in its service
   (https://www.awwwards.com/sites/ponpon-mania).
2. Order and Chaos — SOTD Sep 2025 — a CSS Grid comic where THE LAYOUT ITSELF
   follows the narrative and the grid visibly breaks as the story unravels
   (https://www.awwwards.com/sites/order-and-chaos). Layout-as-storytelling
   with no engine — directly transplantable to a static PWA.
3. Lacoste Polo Factory (Merci Michel) — SOTD Jul 2026 + Developer Award — a
   brand page built AS a playable game (https://www.awwwards.com/websites/games/).
4. Gucci: Mystery Unfolds (MONOGRID) — SOTD Jun 2026 — game-mystery mechanics
   as site structure.
5. Race Condition (North Kingdom) — https://www.northkingdom.com/case/racecondition
   — agent state generating structured UI components (A2UI), the frontier
   beyond static screens.
6. KPR / KPRVERSE — https://kprverse.com/ — SOTY 2022, still the canonical
   "game-world as website" every 2025-26 site iterates on.

Trend read: texture/materiality is the premium signal; diegetic UI (interface
exists inside the fiction: https://nativeui.substack.com/p/diegetic-interfaces)
is live; kinetic/variable type carries identity
(https://www.wix.com/wixel/resources/typography-trends). Reference corpora:
https://www.gameuidatabase.com/ (55k screenshots), https://interfaceingame.com/.
Use these as the moodboard, not Dribbble.

## Track 3 — Mobile-game depth principles (what AAA mobile does)

1. Balatro — the feedback STACK: shake + flip + accelerating count-up + fire +
   chip sounds under a CRT shader; cards have inertia and magnetic damping
   (https://blakecrosley.com/guides/design/balatro,
   https://80.lv/articles/balatro-s-card-movements-shaders-recreated-in-unity).
   PRINCIPLE: an event isn't shown, it's PERFORMED — motion+sound+particles+
   numbers together, scaled to importance.
2. Marvel Snap — depth lives in the earned OBJECT (cards gain parallax,
   frame-break, FX as they upgrade); chrome stays calm
   (https://www.artstation.com/artwork/GemNDd). PRINCIPLE: concentrate depth
   in the few objects users earn and touch; keep navigation quiet.
3. Honkai: Star Rail — ONE fixed ~10s celebration ritual with escalating
   rarity tells; users learn to read the tells, which is the dopamine
   (https://www.pcgamer.com/honkai-star-rails-gacha-animations-have-no-right-to-go-this-hard/).
4. Zenless Zone Zero — menus as art-directed editorial graphic design with
   mascots INHABITING them (https://www.behance.net/gallery/188673799/).
   PRINCIPLE: a menu is a place where a character lives.
5. Persona 5 — asymmetry + perpetual motion as brand; menus built by posing 3D
   and rendering to 2D for hand-made energy
   (https://www.siliconera.com/atlus-reveals-design-secrets-behind-persona-5s-distinctive-ui/).
   PRINCIPLE: a signature angle system + signature easing, everywhere.
6. Juice canon — Juice it or Lose it
   (https://gamejuice.co.uk/resources/juice-it-or-lose-it), Disney 12
   principles applied to UI (https://gamejuice.co.uk/articles/disney-12-animation-principles-games),
   juice on the web (https://valdemird.com/blog/game-feel-on-the-web/).
   PRINCIPLE: squash-stretch, anticipation, follow-through on buttons, cards,
   transitions.

## Track 4 — Technique reality for a no-build PWA on iOS (July 2026)

WORKS, CHEAP, UNIVERSAL:
- border-image 9-slice ornate frames (free perf; assets: Kenney CC0, Fantasy
  UI Borders; construction ref: wow-ui-textures).
- linear() spring easing — Safari 17.2+ (https://www.joshwcomeau.com/animation/linear-timing-function/).
- Web Animations API choreography — iOS 13.4+; chain animation.finished.
- Sprite-sheet steps() animation + image-rendering:pixelated — near free.
- feTurbulence/feDisplacementMap texturing — pre-render static regions to
  PNG/WebP; never animate the filter (perf).
- Pure-CSS CRT overlay (afterglow-crt pattern) — cheap if gradients-only.
- Canvas particle bursts (tsParticles) — cap counts, idle-kill.

WORKS WITH GATES:
- Scroll-driven animations (animation-timeline) — Safari 26+ (Sep 2025); ship
  behind @supports with static fallback
  (https://webkit.org/blog/17101/a-guide-to-scroll-driven-animations-with-just-css/).
- WebGPU — universal on iOS since Safari 26 — one hero surface only
  (https://web.dev/blog/webgpu-supported-major-browsers).
- curtains.js WebGL planes — one plane OK, never every panel.

SKIP (researched, rejected):
- CSS Houdini Paint — still not native in Safari 2026 (https://web.dev/articles/houdini-how).
- backdrop-filter glass as identity — perf-capped (3-5 blurs max) AND
  trend-dated (https://github.com/shadcn-ui/ui/issues/327).
- Rive/Lottie — 200KB/60KB runtimes vs sprites for a no-build PWA
  (https://unicornicons.com/learn/rive-vs-lottie).
- Web haptics as dependency — navigator.vibrate absent on iOS; the
  checkbox-switch trick patched in iOS 26.5 (https://github.com/tijnjh/ios-haptics).
  Progressive enhancement only.

RTL: all direction-neutral or logical-property compatible; use
margin-inline-start/inset-inline; WAAPI transforms need dir-aware sign flips.

## Track 5 — Anti-slop rules (sourced)

Named slop markers (https://www.925studios.co/blog/ai-slop-web-design-guide):
Inter-by-default, purposeless purple-blue gradients, uniform 16px radius,
identical 24px padding flatness, vague oversized heroes, too-smooth symmetric
AI illustration, identical fade-ins. Antidotes: personality display type,
semantic color, bespoke illustration, state-tied micro-interactions.

Slop is a system failure fixed by design memory
(https://trilogyai.substack.com/p/fixing-visual-ai-slop): codify taste as
tokens + written rationale (DESIGN.md) so every screen inherits ONE set of
decisions instead of re-deciding.

Taste is the scarce asset (https://linear.app/now/design-for-the-ai-age,
https://www.opale-ui.design/blog/taste).

Extracted rules from the winners:
(a) ONE fiction, total commitment — every element in-world.
(b) Bespoke assets over library assets — drawn frames, custom icons, a mascot.
(c) Asymmetry and angle as identity.
(d) Motion identity — one signature easing family reused everywhere.
(e) Texture over translucency.
(f) Specificity in copy and iconography — name things in the fiction's language.

## Ranked: 6 highest depth-per-effort techniques for THIS app

1. 9-slice border-image bespoke frames — the single biggest game-vs-web jump.
2. linear() springs + WAAPI choreography — performed events, platform-native.
3. Sprite-sheet mascot with reaction states — cheapest AAA presence.
4. Baked feTurbulence texturing — the tactile-maximalism signal.
5. One juice stack for one celebration ritual — count-up + shake + particles
   + sound, scaled by magnitude.
6. Scroll-driven parallax layers behind @supports.

---

# The three candidate directions (operator picks; no reskin ships unapproved)

## A. The Illustrated Academy (total fiction / tactile maximalism)
הסדנה becomes a drawn place. Bespoke 9-slice frames (built from CC0 bases,
recut to the ink+gold identity), baked parchment/stone texture on every
surface, a drawn mascot with reaction states (sprite steps()), one custom SVG
glyph language, diegetic framing (the daily page is a workbench ledger; the
tree is a carved guild board). NES.css totality rule: no element left
unskinned. Largest asset effort; the Ponpon/tactile path; the layout itself
gets redrawn, not re-bordered.

## B. The Performed Interface (motion identity / Balatro path)
Identity through choreography, not chrome. One signature spring family
(linear()), every event performed: answers count up, streaks shake, cards
squash-stretch, page transitions anticipate and settle; ONE fixed celebration
ritual with escalating rarity tells; depth concentrated in earned objects
(rank tokens, skill cards get Marvel-Snap-style parallax/FX as they level);
navigation stays quiet. Kenney UI audio layer optional. Zero asset
dependency, fastest to ship, the feel is FELT on phone within a day.

## C. Persona Slash (graphic radical / asymmetry)
High-contrast 3-color identity (ink/red/gold), a diagonal angle system cut
through every panel, menus never static, kinetic Hebrew display type
(variable font), layout-as-narrative (the Order-and-Chaos lesson: the grid
itself tells the day's state — clean at day start, progressively stamped/
broken as sections complete). Boldest visual break, highest RTL/readability
risk, most "nothing else looks like this."

Recommendation: B first (ships this week, transforms feel, zero asset risk),
then A's frame+texture+mascot layered on top as the destination; C's angle
system only if A+B still feels tame. But the pick is the operator's.
