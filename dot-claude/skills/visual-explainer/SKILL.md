---
name: visual-explainer
description: Generate a diagram or visual via Azure Foundry gpt-image-2-general and embed inline. Triggers on "i don't understand" / "show me" / "draw it" signals (en/he/ar) detected by the UserPromptSubmit hook.
model: claude-haiku-4-5-20251001
allowed-tools: ["Bash($HOME/.claude/bin/generate-visual.py *)", "Bash($HOME/.claude/bin/pop-visual.sh *)"]
---

# Visual Explainer

Generate a diagram or visual via Azure Foundry `gpt-image-2-general` and embed it inline in markdown when the user asks for a visual explanation or signals they're not following a text-only response.

## When to invoke

- User says "i don't understand", "show me", "draw it", "visualize this", "make a diagram", "explain visually", "i'm lost", "i'm confused"
- User asks "what does this look like" / "how does this flow"
- A `UserPromptSubmit` hook (`~/.claude/hooks/visual-explainer-trigger.sh`) injects the hint `"User indicated they need a visual explanation"` — that's your cue to use this skill.
- The current explanation involves: data flow, state machine, file-tree, hierarchy, multi-step pipeline, three-or-more-component interaction, anything the user has asked clarification on twice.

Do NOT invoke for:
- Pure code blocks (a code fence is already a visual)
- One-step or trivially linear explanations
- When the user is moving fast and just wants confirmation

## How to use

Call the helper:

```bash
~/.claude/bin/generate-visual.py "<concept to visualize>" --out-name <slug>
```

The helper:
1. Fetches the Foundry cog-svc key (no env needed if `az login` is current)
2. Calls `gpt-image-2-general` deployment in Foundry
3. Saves PNG to `~/.claude/assets/visuals/<slug>-<unix>.png`
4. Prints a markdown reference line on stdout

Embed the printed line in your response inline at the explanation point. Example:

```markdown
The agent-control state files form this loop:

![agent-control-state-loop](/home/shovalbe/.claude/assets/visuals/agent-control-state-loop-1714515600.png)

Each routine writes to one file (single-writer rule). The cockpit reads all four.
```

## Prompt engineering

Pass a description optimized for technical-diagram generation:

- **Good**: "data flow between three planes: cloud routines (top), local timers (middle), interactive sessions (bottom). Arrows show writes to a shared KB in the center. Each plane labeled. Minimal lines, monochrome plus one accent."
- **Avoid**: "make a nice picture of my system" (too vague)
- **Avoid**: "real photo of a developer at a desk" (this skill is for technical diagrams, not stock imagery)

The helper appends a default style suffix (`minimalist technical diagram, clean, monochrome with minimal accent color, labeled boxes and arrows`) — override with `--style "..."` only if your concept demands a different visual register (e.g., flowchart vs swimlanes vs timeline).

## Sizing

- `--size 1024x1024` (default) — most diagrams
- `--size 1536x1024` — wide flow / pipeline / timeline
- `--size 1024x1536` — tall hierarchy / tree / stack

Larger sizes cost more; default is a good middle.

## Cost & limits

`gpt-image-2-general` is deployed under `brn-azai` in `AZAI_group`. One image ≈ $0.04–0.08 depending on size. Don't over-generate — one or two images per response max. If the user asks for "more variations", produce one alternative, not five.

## Output to user

Always:
- Show the markdown reference inline so the image renders in their viewer.
- Briefly caption what the image is showing (one sentence above OR alt text in the embed).
- Mention the absolute path so they can find or copy the file.

## Files involved

- Helper: `~/.claude/bin/generate-visual.py`
- Output dir: `~/.claude/assets/visuals/`
- Trigger hook: `~/.claude/hooks/visual-explainer-trigger.sh` (UserPromptSubmit)

## Hebrew/Arabic

The user codes-switches Hebrew/English (and occasionally Arabic technical terms). The trigger hook matches Hebrew confusion phrases ("איני מבין", "לא מבין", "תסביר לי", "תראה לי"). When generating the image, the prompt to the model can be in English even if the user wrote in Hebrew — the diagram itself doesn't need text labels in the user's language unless explicitly requested.
