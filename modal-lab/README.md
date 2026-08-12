# modal-lab

First stop of the GPU-provider evaluation decided 2026-08-13 (Modal now; Paperspace,
then Fireworks/Together/OpenRouter or RunPod next). Two experiments in one app:

1. Serve Muse Glimmer 30B as a scale-to-zero OpenAI-compatible endpoint on a
   rented GPU (vLLM, A100-80G, per-second billing, $30/mo free credit covers
   light use).
2. Prove per-agent persistent dynamic memory on ephemeral compute: every memory
   mutation is a write-through to a `modal.Volume` (JSONL ledger per agent), so
   an agent is a resurrectable thing (state on disk), not a running thing
   (process on a box). ADR-0010 one level down.

## Commands

```bash
uv tool install modal          # done on this machine, client 1.5.4
python3 -m modal setup         # operator: browser auth, one time

modal run modal-lab/glimmer_service.py           # memory smoke test, no GPU
modal deploy modal-lab/glimmer_service.py        # deploy the Glimmer endpoint
# endpoint URL is printed on deploy; then:
curl -s $ENDPOINT/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"muse-glimmer-30b","messages":[{"role":"user","content":"17*23? number only."}]}'
```

## What to measure before comparing providers

- Cold-start seconds from scale-to-zero to first token (the serverless tax).
- Effective $/hr from the Modal dashboard after a real session, not the rate card.
- Whether the memory ledger survives: run the smoke test, kill everything,
  run it again, expect the previous rows back.

## Status (2026-08-13)

- VERIFIED: per-agent memory persistence. Three `modal run` invocations, three
  fresh containers, ledger grew 1 -> 2 -> 3 rows on the `agent-memory` Volume
  (run ap-XzQVEKJ18P0OgCywujfVaX shows row 3). Free tier, no GPU.
- BLOCKED on operator: the Glimmer GPU endpoint (`glimmer_endpoint.py`). Modal
  refuses to register any A100 function without a payment method on the
  account, even undeployed, which is why the endpoint is a separate file from
  the free-tier memory app. Adding a card is a spend decision, so it waits.
- Auth: done, workspace `shovalbenjer`, token in `~/.modal.toml`.
