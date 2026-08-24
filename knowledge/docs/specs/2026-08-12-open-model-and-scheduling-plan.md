---
PRD: prd/autonomy-ecosystem.md
Ticket: SETUP-OS
Status: proposed, operator decides the numbered blocks at the end
---

# Open-model lanes and the scheduling fabric: the plan, before any spend

Ordered 2026-08-12: "i approve running system with deepseek v4 flash 3107 or qwen 3.6
or huggingface models suggested 12 08 august. tell me the plan how we do it, look for
monthly gpu/computing subscription, start with what i suggested on oracle/aws free
tiers first." Also, same morning: "regarding local and remote crons, tell me the full
suggestion for me to decide." This is that plan. Research date 2026-08-12; every price
names its source and prices this volatile should be re-checked at signup time.

## 1. What the named models actually are

| model | identity | license | serve cost | role here |
| --- | --- | --- | --- | --- |
| "deepseek v4 flash 3107" | deepseek-ai/DeepSeek-V4-Flash-0731, the 2026-07-31 checkpoint of V4-Flash (284B), trending on HF today | MIT, open weights | API: $0.14/M in (cache miss), $0.0028/M cached, $0.28/M out (deepseek pricing page, read 2026-08-03 by pricepertoken); self-host floor ~110 GB, out of free-tier reach | the API workhorse lane: 50 to 180 times cheaper than the Anthropic lanes per token |
| "qwen 3.6" | Qwen3.6-27B (dense) and Qwen3.6-35B-A3B (MoE, 3B active), April 2026 | Apache 2.0 | self-hostable: 35B-A3B at Q4 is ~20 GB and only 3B active per token, CPU-viable | the self-host lane: the one that runs on free ARM compute |
| Qwen/Qwen-AgentWorld-35B-A3B | NOT a coding agent. A world model that SIMULATES seven agent environments (MCP, Search, Terminal, SWE, Android, Web, OS): given an action it predicts the environment's next state. CPT then SFT then RL(GSPO) from Qwen3.5-35B-A3B-Base, arxiv 2606.24597 | Apache 2.0 | same MoE shape as above | the TRAINING half: a synthetic environment for RL on our own agents, pairs with PrimeIntellect's verifiers/prime-rl (repo-compare run 1 ADOPT) |
| HF trending 2026-08-12 | DeepSeek-V4-Flash-0731 (above), moonshotai/Kimi-K3, LiquidAI/LFM2.5-2.6B (small text model, edge-sized) | varies | LFM2.5-2.6B runs on anything | Kimi-K3: watch; LFM2.5-2.6B: candidate for the tiny always-on classifier lane |

The important correction from the research: AgentWorld is the simulator you train
AGAINST, not a model you drive the harness WITH. The pipeline the operator has been
circling for a month (prime-agent row 28, "a model I can train on") is: capture our
own trajectories, train a driver model (Qwen3.6-27B LoRA) against AgentWorld-style
environments, evaluate with the eval pipeline. The data prerequisite is prompt and
trajectory capture, which is exactly PR #60 and PR #53, both in today's merge batch.

## 2. Free tiers first, as instructed

**Oracle: act before 2026-08-18.** OCI cut the Always Free Ampere A1 allowance from
4 OCPU / 24 GB to 2 OCPU / 12 GB effective 2026-06-15 (InfoQ), and instances above
the new limit get TERMINATED on or after 2026-08-18, six days from now. Pay As You Go
accounts keep the full 4 OCPU / 24 GB at $0. So: if an OCI account exists here with
an A1 instance, it must be checked this week; if none exists, sign up directly as
PAYG (card on file, still $0 for A1) and skip the trap. On 24 GB, Qwen3.6-35B-A3B at
Q4 fits with room and the 3B-active MoE makes CPU serving usable for background
lanes (reference point from the same guides: a dense 7B Q4 does 5 to 8 tok/s on the
4-OCPU shape; a 3B-active MoE lands in the same class). On the reduced 12 GB shape,
only the small-model lane fits (LFM2.5-2.6B class).

**AWS free tier: rejected for this.** No GPU in free tier, t-class CPUs are too small
for anything above the 2.6B class. AWS re-enters only if we later want spot GPU
by the hour, where it is not the cheap option anyway.

**Zero-spend API lanes that already have clients in this repo:** `tools/nvidia/nim.py`
(keyless NVIDIA NIM free endpoints, wired 2026-07-29) and `tools/openrouter/`
(OpenRouter, which carries free-tier open models). Both predate this plan and neither
is routed to any lane. That is wiring, not procurement.

## 3. The wiring, in adoption order

1. **Bridge layer.** The stock Claude Code CLI retargets to any endpoint speaking the
   Anthropic wire format via `ANTHROPIC_BASE_URL` (glm-harness pattern, repo-compare
   run 1; their DeepSeek profile is marked documented-untested). New `tools/backends/`
   with one env profile per target: `deepseek-v4-flash.env` (their API is
   OpenAI-compatible, so it goes through a LiteLLM proxy translating Anthropic wire),
   `qwen-local.env` (llama.cpp server on the OCI box, same proxy), `nim.env`,
   `openrouter.env`. Validate each against glm-harness's mock server first: zero
   spend, plumbing only.
2. **First converted lane: eval audit.** The eval-runner design already names
   DeepSeek as audit model. Run the audit leg on V4-Flash-0731 API. At $0.14/$0.28
   per M this is pennies per nightly run. Measured acceptance: same 4-phase pipeline,
   agreement rate vs the current audit model logged per run.
3. **Second lane: background fan-out.** Inventory, classification, extraction
   subagents (the haiku tier in model-selection.md) move to the OCI Qwen box or NIM.
   Gate: `skill-eval-harness` paired with/without lift (repo-compare ADOPT) on 20
   sampled tasks before any lane is promoted, so the pivot is measured, not vibed.
4. **Lead lanes stay Anthropic.** Nothing in this plan touches the interactive lead
   or oracle edits. The pivot earns lanes from the bottom.
5. **Training (after PRs 53+60 land and capture runs for 2+ weeks).** LoRA
   Qwen3.6-27B on the captured trajectory corpus, rented 48 GB GPU by the hour, eval
   against AgentWorldBench-style checks plus our own gate. Not before the corpus
   exists; training on 10 days of hashes is how the last plan died.

## 4. Monthly GPU money, only if and when training starts

| option | price | monthly shape | verdict |
| --- | --- | --- | --- |
| RunPod RTX 4090 24GB | $0.74/hr (their pricing page via aicostcalculators, Aug 2026) | ~$65/mo at 3 h/day | recommended for LoRA runs, on-demand not subscription |
| Vast.ai 4090 spot | ~$0.35/hr marketplace, no SLA | ~$30/mo at 3 h/day | cheapest, fault-tolerant runs only |
| Lambda A100 80GB | $2.06/hr | $150+/mo at 3 h/day | only if 27B full-precision training ever matters |
| any 24/7 rental | $250 to $530/mo | standing cost | rejected: nothing here needs a warm GPU around the clock |

Recommendation: no monthly subscription at all. Prepay $10 to 25 on RunPod or Vast
per training burst. The standing infrastructure is the $0 OCI box.

## 5. Local and remote crons, the full suggestion

Three scheduler substrates exist here, with very different survival records:

- **systemd user timers (local WSL): the only one that never died.** agent-feed has
  fired every 30 minutes through every session change (and through five days of a
  broken payload, which proves the TIMER layer is solid even when the job is not).
- **CronCreate (harness-local): the one that killed Gastown.** 7-day expiry plus a
  weekly human re-bootstrap ritual; measured dead since 2026-06-03. Do not rebuild on
  it.
- **Cloud scheduled agents (/schedule routines): survive the PC being off,** run on
  subscription billing, no local filesystem. Right for GitHub-facing recurring work,
  wrong for anything reading local ledgers.

Per-job proposal for the 8 dead Gastown jobs, revive 3, fold 3, retire 2:

| old job | verdict | where | why |
| --- | --- | --- | --- |
| Mon trending research | revive as `/repo-compare` | cloud routine, Mon 09:15 | the skill exists now, needs only gh access |
| daily PR health check | revive | cloud routine, weekdays 08:15 | GitHub-only, no local state needed |
| Wed PR sweep | fold into daily PR check | same routine | one sweep, not two cadences |
| Trend Sentinel scoring | fold into repo-compare | same Mon routine | same corpus, same verdicts |
| Changelog Hound | fold into repo-compare fresh-search leg | same Mon routine | one fresh-repos sweep |
| Polecat idea-to-repo | retire | nowhere | portfolio-pump loop from the job-search era; revive only by name |
| Fri AEO/SEO audit | retire to manual | run on request | monthly value at best |
| Code Reviewer | already superseded | GitHub Actions | claude-code-review.yml reviews every PR push since 2026-08-05 |

Local systemd additions worth having regardless: a nightly `gate.py run` on
claude-setup (writes the ledger row so morning sessions inherit a gated tree), and
the agent-feed timer as is. Both read local state, so they belong on the machine,
not in the cloud.

Cost note: the two cloud routines spend subscription quota unattended, which is
exactly the class the-loop-may-act reserves. Nothing gets armed until the operator
answers block D below.

## 6. Decision blocks

- **A. DeepSeek API funding.** The eval-audit lane needs a funded DeepSeek API
  account (prepay, their minimum is small). Money, so yours. Recommended: yes, $5.
- **B. OCI account.** Does one exist, and is anything running on Always Free A1?
  If yes: upgrade to PAYG before 2026-08-18 or the instance dies. If no: PAYG signup
  fresh. Card touch, so yours. Recommended: PAYG either way, still $0.
- **C. GPU money.** $0 now; $10 to 25 per training burst later, on-demand. Approve
  the shape now or when the corpus is ready.
- **D. Arm the two cloud routines** (daily PR check, Monday repo-compare) plus the
  nightly local gate timer. Unattended subscription spend, so yours. Recommended:
  yes to all three.
- **E. Which lane converts first.** Recommended: eval audit (block A), then
  background fan-out behind the skill-eval lift gate. Lead lanes not in scope.
