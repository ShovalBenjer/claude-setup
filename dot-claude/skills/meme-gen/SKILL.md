---
name: meme-gen
description: Create a meme image or short video with Gemini via the logged-in Chrome session. Triggers on /meme, "make a meme", "meme this", "surprise me with a meme". Takes a moment/joke/screenshot as input, or picks one from recent context when asked to surprise. Browser-driven, no API key.
---

# meme-gen

Generate a meme through gemini.google.com in the operator's own Chrome session
(claude-in-chrome tools). The operator already uses Gemini image generation by
hand; this skill automates the loop and adds guardrails.

## Flow

1. **Pick the moment.** From the request, or, on "surprise me", from recent
   conversational context (a WhatsApp exchange, a session event, a gate
   verdict). Funny beats clever; specific beats generic.
2. **Scrub before prompting.** The prompt sent to Gemini must contain NO
   personal identifiers: no real names, phone numbers, employer names, or
   message text verbatim. Recast the moment as a scene. pii-scrubber rules
   apply to outbound prompts.
2b. **Reference image (the 2026-08-17 correction: text-only scored ~100 on the
   catch but missed the reference).** Default to grounding the meme on a real
   photo when one fits: use the composer's plus control to attach, from Google
   Photos (the operator's own account integration) or a local file the
   operator names. Operator-picked photos of himself or photos he explicitly
   approves are allowed; never auto-select photos of other people, and when in
   doubt name the candidate photo and ask before attaching. The prompt then
   says "use the attached photo as the subject/scene reference".
3. **Drive Chrome.** Load claude-in-chrome tools via ToolSearch (one batched
   select). Engine rotation, operator-set 2026-08-17: default
   https://gemini.google.com; second engine https://chatgpt.com (free-tier
   image gen, use until the tier is exhausted and needs to reset, then rotate
   back). Both are the logged-in web UIs, never an API key. New tab, wait for
   the composer, type an image-generation prompt of the form:
   "Generate a meme image: <scene>. Style: <pick one: photoreal absurdist /
   classic impact-font two-panel / 2000s deep-fried>. Add the caption
   '<caption>' in bold meme lettering." Submit, wait for the render.
   Known quirk (measured 2026-08-17): with RTL/Hebrew text in the composer,
   Return may not submit; click the send arrow instead.
4. **Video variant** (only when asked): same flow but request a short video
   clip; Gemini's video generation may be gated by account tier; if the UI
   offers no video option, say so and deliver the image instead.
5. **Capture and deliver.** Screenshot the result region (zoom to the image,
   save_to_disk: true) so the operator sees it in the terminal, and download
   the full image via the UI's download control when present (downloads need
   explicit user OK per the browser rules; the screenshot alone needs none).
6. **Close the tab.**

## Guardrails

- Never generate memes of real private individuals, and never include chat
  text verbatim; the scene is always a recast, per step 2.
- One generation attempt, one retry on a garbled render, then stop and show
  what happened. No infinite regeneration loops.
- Outward posting (sending the meme anywhere) stays with the operator.
