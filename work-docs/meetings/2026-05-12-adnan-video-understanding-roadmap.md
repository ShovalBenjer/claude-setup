# Video Understanding Roadmap — meeting with Adnan

**Date:** 2026-05-12
**Attendees:** Shoval, Adnan
**Channel:** call

## Bottom line
Adnan is becoming the primary content tester / business owner for the Video Understanding pipeline. He'll feed edge-case TikTok URLs and MP4s. Three priorities locked in: get the deployed app working (current crash blocks his testing), wrap the pipeline as a secured Telegram bot, and stand up an Azure-native learning loop that turns ingested videos into a generative-script feature.

## Decisions
- Adnan is the dogfood owner for the pipeline — he sends edge-case videos, we react
- Multilingual auto-detect (ar / es / pt / en, GCC + LATAM) is part of the product, not a nice-to-have — already shipped to the worktree
- Deploy will move to Yasha's structure: PR → Azure DevOps pipeline → Bicep `what-if` → Bicep deploy (no more manual `az` from local). Target compute is Azure Container Apps, not the manual App Service that's currently crashing
- Telegram bot will accept TikTok URL OR direct MP4 upload, return summary + HTML + JSON. Secured (token + Entra-gated webhook, no public bot)
- Data store: every ingested video keyed by content-hash for dedup; same SHA = same brief, never re-process. Stored in Azure (Blob + table/Postgres TBD)
- Learning loop is in-scope: from RL signal collection (which scripts perform) up through fine-tuning, Azure-native only (Foundry / AOAI fine-tune, not OpenAI platform)
- End goal: pipeline produces *new scripts* (generative), not just analyzes existing ones

## Action items
- [ ] Shoval — ship v3 to ACA via Yasha's pipeline (PR + Bicep) — by EOW
- [ ] Shoval — kill `app-video-understanding-prod` App Service after ACA is healthy — by EOW
- [ ] Shoval — draft architecture for Telegram bot phase (auth, TikTok ingest, dedup) — next session
- [ ] Shoval — draft data + learning architecture (Blob + DB + RL → fine-tune → generation) — next session
- [ ] Adnan — send batch of edge-case TikTok URLs covering ar/es/pt/en — ASAP
- [ ] Adnan — review the @assadtradess brief he already has, confirm content is correct (the "(2).html" he saw was a stale download, not the actual ssstik output)

## Open questions / blockers
- New ACR `acrazaivideogen` (per Bicep) doesn't exist — decide: create it (matches Yasha's design intent) or repoint Bicep params to existing `sentimarkregistry`
- ACA min-replicas: scale-to-zero gives ~10s cold start; for Adnan's interactive testing that's annoying. Keep `min=0` for cost or bump to `min=1`?
- Telegram bot phase: bot framework choice — `python-telegram-bot` (proven, easy) vs Azure Bot Service (more boilerplate, native auth) — defer until phase 2 starts
- Learning loop scope: RL on what reward signal? CTR / engagement / Adnan's manual rating? Needs a follow-up with Adnan on what "good script" means measurably

## Context
Adnan is the business creative owner; Shoval is solution engineer; Yasha owns infra/deploy hygiene. The video-understanding tool is the AI Department's flagship analysis surface — currently used to dissect competitor Gulf-Arabic short-form ads, expanding to LATAM and EN markets. Pipeline: ffmpeg → ElevenLabs scribe → Azure DI OCR → gpt-5.4-SIU vision + synth → Jinja HTML brief.

## Verbatim notes
- "i want to deploy via pr via pipelines, bicep and pipeline structured" (Yasha, relayed by Shoval)
- "create a skill that you write my meeting" (Shoval → request for this very file)
- Three priorities, in order: (1) deployed app working (2) telegram bot wrapping (3) data store + learning → generation
