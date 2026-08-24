# Where you fit — honest assessment from CV + GitHub + LinkedIn + 5-month evidence

> **Sources cross-checked:** `shoval_benjer_resume.docx` (Nov-style CV), `github.com/ShovalBenjer` profile, LinkedIn profile via Apify scrape (apimaestro/linkedin-profile-detail), and the 5-month git/Azure evidence from `~/docs/SHOVAL-BENJER-5MO-CONTEXT-2026-05-08.md`.
> **Generated:** 2026-05-08

---

## ⚠ Security flag (read first)

While sourcing `~/.env` for the Apify token, bash choked on a hyphen-named line and **echoed the value of `FOUNDRY-API-KEY` to stdout**. That value is now in this conversation transcript. **Rotate that key in `brn-azai` immediately:**

```
az cognitiveservices account keys regenerate --name brn-azai -g AZAI_group --key-name Key1
```

Then update wherever it's referenced (Azure DevOps variable groups, Key Vault, local `.env`). The other keys in `.env` (APIFY_API_TOKEN, DEVOPS_PAT) were not exposed.

Long-term fix: rename `FOUNDRY-API-KEY=` → `FOUNDRY_API_KEY=` so bash sourcing works, and anything still tracking the old name updates over time.

---

## 1. The three-surface mismatch

You're telling three different stories across the surfaces a recruiter reads. This isn't fatal — most engineers do it accidentally — but for the calibre of role you're aiming at, alignment is leverage.

| Surface | Title | Anchor message |
|---|---|---|
| **CV** | "AI Engineer \| LLM Fine-Tuning & E2E System Deployment" | Fast-paced sec-tech startup; vision system 91.1% recall; LLM fine-tuning with QLoRA |
| **GitHub bio** | "Solution Engineer" | "For every one of our failures, we had spreadsheets that looked awesome" |
| **LinkedIn headline** | "AI Engineer @Be Z" | "2027 will be around optimizing around human related metadata… still scared and aroused from mathematical notations" |

Pick ONE story. Right now they read like three different candidates: the resume sells "LLM fine-tuner who deploys end-to-end", GitHub sells "solution eng who deploys things", LinkedIn sells "agentic-protocol-pilled futurist". A US senior recruiter screening 80 profiles in an hour will not reconcile this for you — they'll bounce.

**Recommended unifier (because it's actually what you do):**
> "AI Engineer building production agent systems — multi-agent orchestration, MCP/A2A protocols, eval infrastructure. Tel Aviv."

Specifically:
- LinkedIn About: drop the "scared and aroused" line for any role you're applying to in the US (it reads as edgy-Twitter, not exec-presence). Keep it ONLY if you're targeting startup-founder networks where it works.
- GitHub bio: replace the spreadsheet quote with one line that names what you ship.
- Resume title is fine, but the i-sdd / Be Z Online year of work is the strongest signal you have and it's nearly invisible on your CV.

---

## 2. What your CV says vs. what you actually did

**The CV omits or undersells the strongest evidence.** Your CV (Nov-style) lists Halevi Partner (06/2025–present, the Wien sec-tech startup, side advisory role) and Phantom Reach (10/2024–02/2025) as your main AI work. **i-sdd / Be Z Online is missing entirely.**

Yet in the last 5 months you've:
- Authored **136 completed PRs** across the Corp Domain Azure DevOps org
- Made **210 commits** to a single production Chatwoot/Foundry CS agent (`axia-seekapa-cs-agents`)
- Lifted that agent's eval pass rate **24% → 64%** in a single prompt iteration (v107.3) backed by a measurable eval suite
- Built a Streamable-HTTP MCP server hardened against an 8-finding codex-driven security review (Entra federation, OAuth issuer assertion, RFC 9728 metadata, PII redaction) — closed in 2 days
- Owned 6 production Azure resources end-to-end (3 Function Apps + 3 Web Apps in Sweden Central) plus 2 Foundry agents (`seekapa`, `AxiaCS`) running on GPT-5.5
- Iterated 12 prompt versions (v97 → v109) under TDD with vertical tracer bullets, no mocks, real fixtures

The CV captures roughly **0% of this**. It captures Halevi (4-month side gig, by far the smallest scope) and Phantom Reach (a 4-month accelerator team project). **Fix the CV first.** Without the i-sdd / Be Z body of work, the resume reads like a recent grad with hobby projects. With it, the resume reads like a senior IC who shipped a production multi-agent system solo.

---

## 3. What's rare about your evidence

Most candidates with your title don't have these:

1. **Solo ownership of a deployed production AI agent at scale.** 210 commits, 12 prompt versions, full CI/CD, eval gate, multilingual rollout. Most "AI Engineers" are one of three: model fine-tuners, RAG-pipeline-pluggers, or agent-tooling-hobbyists. You're none of those — you're an **agent SRE**. That's a niche that's hiring.

2. **Streamable-HTTP MCP server in production.** RFC 9728 protected-resource metadata, dual-trailing-slash `aud` claim, Entra federation, MSI-to-Key-Vault. Almost nobody has done this. Anthropic, Glean, Cursor, Cohere, Sourcegraph — all of them are spending eng cycles on MCP right now. You've already shipped against their clients.

3. **A2A bridge in production.** Synchronous Claude orchestrator → Codex executor with audit logging. The "two-model orchestrator/executor split" is the kind of thing labs are still arguing about; you've operated it for months.

4. **Eval-driven prompt engineering with cost ceilings.** ≤1500 input / ≤120 output tokens per row, primary/audit judge separation (grok-4-1-fast / DeepSeek-V3.2), Foundry SDK auto-eval inlined into Deploy. This is real eval infra discipline, not vibes.

5. **Multilingual agent work.** Hebrew + Arabic + English, Yasha intake flow v108 → v109 multilingual. For Israeli + GCC + LATAM markets that's gold; for US-only markets it's neutral.

6. **40 FB + 37 GAds + LinkedIn/TikTok/Snap/Taboola Windsor surface.** Ad-tech data eng at material scale. Most "AI eng" candidates can't speak to ad-tech ops; you can.

---

## 4. Where you've under-invested

These are the gaps that show up when calibrating against US senior-tier roles:

1. **No public showcase repo.** Your pinned GitHub repo is `phantomreach/phase-1` (1 star). Your most polished personal project — Time Twist Visualizer (Rust TUI for git history) — is private/dormant. **Time Twist is your best move:** Rust signals systems chops, the topic (git visualization) is recruiter-friendly, no employer entanglement. Make it public and pin it.

2. **No upstream PRs.** Zero merged PRs to vLLM, HF TRL, DeepEval, or any frontier-stack repo. For Navan / Anthropic / OpenAI calibre, **one merged PR to any of those outweighs five new personal repos.** Easiest path: a DeepEval contribution since you already have judge-pipeline expertise.

3. **No public writeup of your eval work.** The 24% → 64% lift, the Foundry SDK auto-eval inlining, the cost-bounded judge — all of this is portfolio-worthy and currently not shared. A blog post titled "From 24% to 64% on a Production CS Agent: What Actually Moved the Number" with the eval methodology (no proprietary data — the *pattern* is the artifact) is the single highest-leverage thing you could ship in a weekend.

4. **LinkedIn Skills section is empty.** Zero skills listed. Recruiters search by skill, and you're invisible. Add 30 skills (Python, Azure Functions, Azure AI Foundry, MCP, A2A, LangChain, PyTorch, Hugging Face, RAG, Vector DB, LanceDB, vLLM if you've actually used it, Bicep, Azure DevOps, CI/CD, Chatwoot, eval engineering, prompt engineering, multilingual NLP, etc.).

5. **LinkedIn About is anti-recruiter.** "Scared and aroused from mathematical notations" reads as in-group humor with founder/researcher Twitter — it'll filter out half the recruiters who'd otherwise click. Rewrite as a 4-line paragraph naming concrete shipped systems.

6. **Brigade General Excellence Award (2020) is missing from LinkedIn.** It's on the resume. Add it to LinkedIn under Honors & Awards. Israeli military awards are real signal in IL hiring and don't hurt elsewhere.

7. **No Hugging Face presence beyond a profile.** Your CV says "Hugging Face" in the contact strip; the profile (per the resume) hosts SoloSolve gemma-3-270m. Pin a model card with eval numbers. HF profile is the fastest "credibility on the model side" you can build.

---

## 5. Where your best chances are — ranked

The following ranking is based on **what your evidence actually supports**, not what's most prestigious or what pays most.

### Tier 1 — Strong fit, apply now
*You'd be in the top half of applicants. Realistic offer probability if pipeline opens up.*

#### a. **MCP / agent-platform engineer at frontier-model or AI-tooling companies**
Anthropic (Forward Deployed Engineer, Applied AI), Cursor, Glean, Cohere, Sourcegraph, Clay, Hex. Your Streamable-HTTP MCP + A2A + eval-infra story is exactly what these teams are hiring for, and few applicants have shipped it. The Israel office angle helps for Anthropic/OpenAI which both have IL footprints; Cursor and Glean are remote-friendly.
**Why you fit:** rare combination of agent SRE + protocol-implementer + eval discipline.
**Bar:** one merged upstream PR + one public eval writeup + cleaned-up GitHub showcase. ~3 weekends of work.

#### b. **Senior AI Engineer / Agent Operations Lead at Israeli scale-ups**
AI21 Labs, Lemonade, Wiz, Sentra, Pinecone (IL office), MyEsho, Run:AI (now NVIDIA), Datagen, Hagshama, Twiggle. Same skill match as Tier-1a but lower bar, comp around ₪50k–70k/mo.
**Why you fit:** 5-month evidence is overwhelming for senior IC. You can own a production agent solo.
**Bar:** the CV fix above is enough. Apply this month.

#### c. **Forward-Deployed Engineer / Solution Architect at AI vendors selling into Israel/GCC**
Anthropic SE (if hiring IL), Vercel, Supabase, MongoDB, Databricks, OpenAI ATA. You ARE literally a solution engineer right now, with the en/he/ar coverage that GCC accounts need. Comp may regress vs. pure IC senior-eng tracks but the lifestyle (less prod ownership, more breadth, travel) suits people who want different exposure.
**Why you fit:** language coverage + ad-tech surface + production agent + customer-facing track record.

### Tier 2 — Reach, but not absurd
*30–40% offer probability if the pipeline opens. Need the portfolio polish first.*

#### a. **Senior ML Engineer at Navan / late-stage US scale-ups**
The role you've been calibrating against in your memory. Honest read: **stretch but not absurd.** The fine-tuning work on the resume (gemma-3-270m QLoRA on SoloSolve) is ~4-mo accelerator output, not production. The production work is agent-ops, not ML modeling. US senior-ML pay-band roles want either deep ML (papers, SOTA) or deep production ML pipelines (PyTorch/JAX at scale). You have neither *yet* — you have prod agent ops which is adjacent but not the same.
**To convert:** the three things from §4 (public showcase + 1 merged PR + eval writeup) close half the gap. The other half is one quarter of demonstrable PyTorch/training-pipeline work — which you could stand up by hosting a vLLM+quantized 7B locally and writing it up.

#### b. **Founding Engineer at a YC / pre-seed AI startup**
Cold reach, but your "I shipped a production agent solo" story is exactly what early-stage founders want. Israeli founder networks, AlphaWave alumni, anyone you met through Phantom Reach. Comp is variable; equity is the real upside.

### Tier 3 — Possible but weaker fit
*Only if Tier 1/2 don't pan out within 4–6 months.*

- **Pure ML research / RL roles** — you don't have publications, no SOTA, no RL hands-on. Pass.
- **Pure data engineer / DE roles** — you can do it, but it'd be a regress from agent ops.
- **Frontend / full-stack senior** — you have the skills but not the signal density. Pass.

### Where I would NOT spend cycles

- Big-tech FAANG senior eng — too much process, not enough portfolio work upstream, you'd time out at the "leetcode + system design" loop without the comp prep window.
- Pure prompt-engineering job titles — undersells what you actually do. Apply to "AI Engineer" or "Senior Engineer, Agents" instead.

---

## 6. Concrete next 30 days

If you want one ranked list of moves:

1. **Rotate the leaked Foundry key.** (Today.)
2. **Fix the .env** — rename `FOUNDRY-API-KEY=` to `FOUNDRY_API_KEY=`. (Today.)
3. **Rewrite the CV** to put i-sdd / Be Z work as the primary current role, with three or four bullets on what you actually shipped (210 commits, eval 24→64, MCP hardening, multilingual). Move Halevi Partner to "Side advisory" or remove it. (1 evening.)
4. **Unify the three surfaces** — same title, same one-line pitch on CV / GitHub / LinkedIn. Drop the "scared and aroused" line for any non-founder context. (1 hour.)
5. **Make Time Twist Visualizer public + pin it** on GitHub. Replace `phantomreach/phase-1` as your pinned repo. (1 evening if it's already polished.)
6. **Fill LinkedIn Skills section** with 30 skills + add Brigade General Excellence Award. (30 minutes.)
7. **Write the "24 → 64" eval blog post.** Methodology only, no proprietary data. Publish on Medium or your own static site. Link from CV + LinkedIn + GitHub. (1 weekend.)
8. **Open one upstream PR** to DeepEval (easiest path given your eval-judge expertise) or HF TRL. (1 weekend.)
9. **Stand up a vLLM container** serving a quantized 7B model locally. Write it up. Host it cheaply on a small box. This is the single best move for the Navan-tier reach roles, and it doubles as a Seekapa internal eval-judge cost reducer. (1 weekend.)
10. **Apply.** Tier-1b roles in IL first (lowest friction, fastest feedback). Tier-1a US roles after the showcase repo + one PR are live.

If you do 1–6 in the next two weekends, the resume + profiles align with the evidence and Tier-1 roles open up. Items 7–9 are the multipliers that move you toward Tier-2.

---

## 7. The bottom line

**You're a senior IC agent-systems engineer who's been positioning yourself as either (a) an LLM fine-tuner (CV) or (b) a solution engineer (GitHub/i-sdd title). Both undersell.** Your real lane is *production agent operations* — and there's a hiring market for it that's currently undersupplied. You'll get further by leaning into what you've actually shipped than by trying to look like a more research-y candidate.

Best single role to target first: a senior agent-platform engineer at an MCP/A2A-aligned company (Anthropic FDE, Cursor, Glean, Clay) or an Israeli scale-up senior agent role. Both fit the evidence, both pay reasonably, and both let you continue compounding the agent-ops body of work rather than restarting in a different lane.
