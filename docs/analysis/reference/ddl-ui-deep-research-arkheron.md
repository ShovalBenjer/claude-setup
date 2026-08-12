# Game-Grade UI Research: Arkheron + Modern Benchmarks (2026-07-22)

Commissioned after the operator set Arkheron as the design bar. Sources verified
by web research (agent run, 33 tool calls); no fabricated features. This doc is
the design-system input for the next visual upgrade pass.

## What Arkheron is

A real, current game: team-based PvP "tower royale" by **Bonfire Studios**
(founded by ex-Blizzard CCO Rob Pardo). Revealed Jan 2025; **closed beta July
15-26, 2026** (now); release 2026 (PC/PS5/Xbox). Diablo × Hades register:
isometric, dark surreal tower "constructed from emotionally-charged memories."
Its UI is specifically praised for team-information density without clutter
(ally Relic cooldowns always visible), and Bonfire spent the pre-beta cycle on
"gameplay clarity, UI, performance."

## Arkheron design grammar (sourced patterns)

1. World-material surfaces: decayed marble over void, memory-light flicker;
   menus inherit the fiction (painted backgrounds even for settings screens).
2. Clarity-first squad HUD: all critical state always visible, zero clutter.
3. Status lives ON the object: consumable charges as a bar above health;
   empowerment renders as fire on the health bar itself.
4. Glyph stacking: set-bonus icons on nameplates AND HUD for at-a-glance reads.
5. Map glyph taxonomy: one iconographic language for shops/specials/threats.
6. Ping-as-outline: selection = rim highlight; communication without words.
7. Two-tier loot ontology: generic items vs named 4-piece Relic sets with
   2pc/4pc bonuses; typed slots; duplicates upgrade tiers.
8. Rarity color anchoring (strict ramp, never decorative reuse).
9. Legibility patch cycles: icons re-cut "for improved clarity" per patch.
10. Ceremony screens: impactful victory/defeat visuals; stats after the moment.
11. Hero-shot staging: the prep screen is a character showcase beat.
12. Onboarding as a mode ("Learning Spires"): stepwise, low-pressure, in-fiction.

## Benchmarks

- **Hades II**: every menu illustrated (Jen Zee art direction); strict boon
  rarity ramp (white→blue→purple→red + special classes); portrait-led choice cards.
- **Diablo IV**: gothic-minimal chrome (dark thin frames, Rembrandt palette) so
  item art pops; icons carry the read; tooltips are designed, contested surfaces.
- **Baldur's Gate 3**: customizable radial menus; peek-vs-commit input (preview
  on light press, lock on hard press); ambient color semantics.
- **Destiny 2**: the acknowledged benchmark: Swiss typography (Futura/Neue Haas)
  loose-tracked over painterly space; free-cursor hover-to-commit; hundreds of
  icons in one geometric language.

## Web implementation map (static PWA, no frameworks)

| Pattern | Technique |
|---|---|
| Decayed-marble panels | layered gradients + seamless texture under `mix-blend-mode:overlay`; `feTurbulence` noise; `border-image` ornate frames |
| Memory-light accents | radial-gradient glows, drop-shadow, slow hue/opacity keyframes, reduced-motion gated |
| Rarity rims | padding-box/border-box double background or conic border-image; per-rarity custom property drives rim+glow |
| Glyph taxonomy | one SVG sprite (`symbol`/`use`), `currentColor` state tinting |
| Status-on-bar | stacked divs or canvas; `mask-image` silhouettes; fire = `steps()` sprite animation |
| Ping outline | outline pulse or SVG `stroke-dasharray` march |
| Engraved titles | display serif (e.g., Cinzel-class) small-caps, wide tracking, dual text-shadow; `background-clip:text` metallics |
| Ceremony | fullscreen overlay + Web Animations API choreography + canvas embers |
| Peek-vs-commit | Pointer Events: short-press preview, long-press confirm |
| Tooltip cards | Popover API + `backdrop-filter:blur` + grid stat groups |
| Radial menu | conic-gradient segments + SVG hit paths |
| Swiss data hierarchy | custom-property type scale; tracking on titles only |

## The 10 rules (design constitution for הסדנה)

1. The UI is set-dressing of the world: every panel uses the fiction's
   materials; no generic chrome.
2. One glance = full state: the learner's "cooldowns" (due reviews, streak,
   pool) always visible, never cluttered.
3. Color is grammar: one strict progression ramp; never decorative reuse.
4. Icons carry the read; text confirms.
5. Two-voice typography: Swiss sans for data, engraved small-caps serif for
   titles only.
6. Status lives on the object (rims, fills), not in legends.
7. Reward with ceremony; stats after the moment.
8. Sets over singles: content grouped into named sets with visible bonuses;
   the collection screen is the motivation engine.
9. Onboarding is a mode, not a modal.
10. Patch legibility like a live game: icons/tooltips re-cut against real usage.

## Application order (post the GPT-audit truth/safety pass, per plan)

1. Token pass: rarity ramp variables, two-voice type scale, sprite icon sheet.
2. Panel material pass: marble/void textures + ornate border-image frames on
   plates and the talent panel.
3. Status-on-object pass: node rims by investment tier, due-review "charges"
   on the day header, ping-outline selection states.
4. Ceremony pass: day-complete and level-up choreography with embers.
5. Set system: concept "relic sets" in the treasury (2pc/4pc = collection
   bonuses over concept clusters).

Full agent report with all 26 source URLs retained in the session log; key
sources: arkheron.com (patch notes, beta announcements), thesixthaxis/cgmagazine
/butwhytho previews, destructoid alpha impressions, Hades II reviews (rpgsite),
Diablo IV UI analyses, BG3 PlayStation blog, Destiny 2 UI portfolios (cand.land,
baileykalesti, behance).
