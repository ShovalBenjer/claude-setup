# 2026-08-15: research context audit and forecast

Session record, lane A. The operator supplied three LLM-assisted research surveys
(two in English covering 2025-2026 conference results and categorical methods, one
in Hebrew covering "agent factories" and a four-layer interpretability framing) and
asked two questions: grade the account's implementation depth against the material,
and map the material onto the account's repositories, including a forecast of which
techniques become high-attention subjects next.

Ground truth for every repo fact below is the cited code, not this file. The
forecast sections are dated judgment, written 2026-08-15, and should be re-scored
against reality no later than 2027-02. Each forecast row names the observable that
would refute it.

## Method

- Two subagent surveys over this repo: the tools tree (125 Python files, 33,327
  lines, plus a 386-line Rust crate), tests, and state ledgers, with the hash
  chains recomputed independently rather than through `bus.py verify`.
- One subagent survey over five sibling repos: new-recruit, sqltok,
  daily-deep-learning, protobuf-fuzz-guard, agenteval-bench (shallow clones at the
  head commits of 2026-08-15).
- Ten citation checks against the live web, covering every flagship claim in the
  three documents. Verdicts are split three ways: verified, garbled, invented.

## Part 1: implementation depth grades

| Dimension | Grade | Anchor evidence |
|---|---|---|
| Verification and meta-testing | 5/5 | `tools/hookgate/regen_rules.py` fuzz-proves the soundness direction of its regex prescan; `tools/hookgate/diff_oracle.py` differentially tests Python `re` against Rust `fancy-regex`; `tools/audit/mutate.py` runs 271 semantic mutations with a green-baseline precondition; `tests/test_bus_lock.py` is an AST-level lock-placement oracle with a check that the oracle can go red |
| Systems integration | 4.5/5 | new-recruit: 31k lines, 829 test functions, hash-bound approval gates, an import-graph reachability test proving the WhatsApp miner cannot be reached from the scheduler |
| Classical algorithms | 4/5 | sqltok: CELF lazy-greedy submodular maximization with the Khuller-Moss-Sviridenko correction, hand-rolled MinHash whose unbiasedness is verified numerically by its own suite, banded LSH, hypothesis property tests on the budget invariant |
| ML implementation (training, interpretability, GPU) | 1/5 | No training loop, SAE, crosscoder, or GPU kernel exists anywhere in the surveyed account; numpy appears only inside the voice-metrics skill |
| Formal methods (SMT, category theory, NN verification) | 1/5 | Referenced in the reading, absent from the code |

Ledger scale behind the 5/5: 15,164 gate runs and 833 refutations (140 REFUTED)
in `state/`, and 3,877 of 3,877 resource-ledger rows re-verified by independent
hash recomputation.

Two cracks mirror the documents' own worst habit and are the cheapest fixes on
the account:

- sqltok's README headline (97.4 percent full recall at 2,000 tokens) has no
  committed artifact under `benchmarks/results/`, which holds only `.gitkeep`.
- agenteval-bench's README describes v0.2 features as shipped; the code is 385
  source lines, its `run_ci` accepts and ignores a `threshold` parameter, its
  "schema validation" checks only top-level key presence, and its
  `max_input_tokens` bound is loaded but never enforced.

## Part 2: the three documents

Citation forensics across all three, every flagship claim checked:

| Claim in the documents | Verdict | Primary source |
|---|---|---|
| Artificial Hivemind, NeurIPS 2025 best paper | Verified | arXiv 2510.x, NeurIPS blog 2025-11-26 |
| 1000-layer self-supervised RL, NeurIPS 2025 best paper | Verified | NeurIPS blog 2025-11-26 |
| AlphaEdit, ICLR 2025 outstanding paper | Verified | arXiv 2410.02355 |
| Shallow safety alignment, ICLR 2025 outstanding paper | Verified | Qi et al. |
| Explicit lossless vertex expanders, FOCS 2025 best paper | Verified | arXiv 2504.15087 |
| TAR trajectories as an SE evaluation practice | Verified as a study, overstated as a "standard" | arXiv 2506.18824 (ASE 2025), arXiv 2604.01437 |
| BatchTopK crosscoders, latent decoupling | Verified | arXiv 2504.02922 |
| Quantum catalytic space, QCL simulates TC1, DQC1 containment | Verified (venue is TQC 2025, not FOCS) | arXiv 2506.16324 |
| Lee, Kondor, Ngo on latent agentic substructures and log pooling | Verified, ICML 2026 | arXiv 2509.06701 |
| Directional Sheaf Hypergraph Networks, ICLR 2026 | Verified | arXiv 2510.04727 |
| Categorical deep learning, categorical cybernetics, optics for RL | Verified research programs | Gavranovic et al.; Hedges et al. |
| Interpretable Context Methodology (folder structure as architecture) | Verified | arXiv 2603.16021 |
| Marr's levels plus a fourth learning level | Verified for Poggio 2012; the "Gest and Martin" attribution is unsupported | Poggio, Perception 2012 |
| AlphaEdit update formula as printed | Garbled: rank-1 special case; the printed projector is ill-formed for singular C (the paper uses an SVD-thresholded projector) | arXiv 2410.02355 |
| "SAT (Satisfiability Modulo Theories)" | Garbled conflation of SAT and SMT | n/a |
| Catalytic subroutines recycling KV caches; borrowing other processes' RAM as a catalytic tape | Invented as engineering; the theory is real but no OS allows it and uncomputation requires storing what was claimed unstored | n/a |
| "Mesostructured knowledge" as a named concept | Unsupported as standard terminology | n/a |
| Resume metrics in the blueprints (64 percent KL recovery, zero sandbox escapes, 0.00 percent degradation) | Invented: stated before any falsifier exists | n/a |

Document verdicts:

- Document A (conference survey): curation A-, synthesis C+. The papers are real
  and well-chosen; the math transcription and the "production" claims are not
  reliable.
- Document B (categorical cybernetics): same profile. Two of its three project
  blueprints are sound if rescoped; the catalytic memory manager is not
  implementable as described.
- Document C (agent factories, four-layer framing): weakest glue, strongest
  punchline. It recycles documents A and B, invents terminology, and presents its
  own synthesis (XAI principles mapped onto ICM folders) as an established
  standard. Its catalytic-computing-as-context-window analogy is a metaphor, not
  a theorem: attention does not mutate the context, and nothing enforces exact
  restoration. But its central citation is real, and it lands close to home: ICM
  (arXiv 2603.16021) is a formalization of exactly the pattern this repo already
  runs, with numbered stages, per-stage contracts, filesystem as state machine,
  and plain text as the interface. This repo is an ICM implementation that
  predates the label, and it carries verification instruments (gate, refuter,
  mutation specs, hash-chained ledgers) that the ICM paper does not have.

The consistent failure mode across all three documents is a synthesis layer that
upgrades real citations into overclaimed engineering, and pre-writes metrics for
systems that do not exist. The account's own claim-plus-falsifier discipline
(`state/claims.jsonl`, `tools/refute/refute.py`) is the correct antidote and
should be applied to README claims, not only to harness claims.

## Part 3: per-repo actions

1. agenteval-bench (largest gap, cheapest leverage): adopt Thought-Action-Result
   triples as the data model per the ASE 2025 study; hash-chain trajectory
   storage by porting `canonical` and `row_hash` from `tools/bus/bus.py` (stdlib
   only); replace key-presence checking with real jsonschema; enforce or delete
   `threshold` and `max_input_tokens`. This converts the weakest repo into the
   one that matches its README.
2. New repo, one only: a BatchTopK crosscoder model-diff on a small base/chat
   pair (for example Gemma-2-2B), reproducing the latent-decoupling findings of
   arXiv 2504.02922 so every claim is checkable against published numbers. This
   fills the 1/5 ML row. Second choice if extending the verification identity
   instead: train a linear safety probe on final hidden states and verify its
   threshold over an input box with Z3. Do not build a GWT orchestrator (this
   repo already is one) and do not build the catalytic memory manager (not
   implementable as described).
3. claude-setup: formalize the ledgers' TAR shape as a schema and publish
   trajectories as gate artifacts; give `/diverge` a measurable form via a
   self-similarity metric in `tools/prose_metrics.py` (the Hivemind result is the
   citable grounding); cite ICM in the docs now that the practice has a paper.
   The thin modules the survey flagged (`tools/selfimprove/scan.py` with its
   hardcoded ranking constants and one-proposal-per-run break, `tools/slop_lint.py`
   with no selftest) are the next TODO rows; the coverage instrumentation already
   points at them.
4. new-recruit: derive every quantitative resume line from a ledger row with a
   falsifier attached, in the style of `state/claims.jsonl`. The documents'
   impact-statement format is usable; their invented numbers are the anti-pattern.
5. sqltok: commit the benchmark artifacts so the README's 97.4 percent claim
   becomes reproducible before it is cited anywhere else. The CELF and MinHash
   work is already the account's best algorithmic evidence.
6. protobuf-fuzz-guard: add SCC-based cycle detection so mutual recursion
   (A to B to A) is caught deliberately; disclose the current limit until then.
7. daily-deep-learning: ingest the verified paper list as an SRS reading track;
   the existing four-way confidence signals are a working metacognition
   implementation worth a lesson unit.

## Part 4: forecast, what buzzes next and why

Anchors for calibration: speculative decoding became a buzzing subject in
2023-2024 because inference cost was the binding constraint and the technique
gave an order-of-magnitude lever without retraining. Long-horizon agent evals are
buzzing in 2025-2026 because agent deployment outran the ability to measure it.
The pattern: a subject buzzes when a binding constraint meets a technique with
working code and a forcing event. Applied to the material visited here:

Tier 1, already inflecting, mainstream within 6 to 18 months:

1. Trajectory-level agent evaluation and deterministic replay (TAR and
   successors). Mechanism: enterprises cannot ship agents without audit trails,
   and regulators are converging on logging obligations; final-answer scoring is
   known to be insufficient. Evidence now: ASE 2025 trajectory study, the
   reproducible-agentic-evaluation line (arXiv 2604.01437), every major lab
   building internal replay harnesses. Trigger: the first high-profile
   agent-caused production incident whose post-mortem hinges on a missing
   trajectory. Refuted if, by 2027-02, no major eval framework ships a
   trajectory-level schema as a first-class object.
2. Model diffing for post-training audits (crosscoders, diff methods).
   Mechanism: open-weight fine-tuning is exploding and the question "what did
   fine-tuning change" has no cheaper answer; diff review beats full review for
   the same reason it does in software. Evidence now: arXiv 2504.02922 with
   released code, follow-on delta-crosscoder work. Trigger: a fine-tune-injected
   backdoor incident that a diff would have caught. Refuted if crosscoder-style
   diffing stays a research-only tool with no CI-style adoption by 2027-06.
3. Diversity collapse metrics and entropy-aware post-training. Mechanism: mode
   collapse now has a best-paper citation (Artificial Hivemind), and it directly
   damages synthetic-data pipelines, creative products, and multi-agent
   ensembles; the self-consuming-loop literature gives it a second engine.
   Evidence now: Infinity-Chat benchmark, 70-model homogenization measurements.
   Trigger: a flagship model release visibly flattened by RLHF, measured
   publicly. Refuted if no diversity-preserving objective appears in a major
   post-training stack by 2027-06.
4. Runtime latent-space guardrails and activation steering inside inference
   engines. Mechanism: steering is cheap at inference, needs no retraining, and
   inference engines (vLLM, SGLang) now have plugin surfaces; representation
   engineering matured from demo to method. Evidence now: steering-vector
   literature, probe-based refusal monitors, early engine hooks. Trigger: a
   deployment mandate for concept-level monitoring in a regulated sector.
   Refuted if no mainstream inference engine ships a first-party activation-hook
   API by 2027-06.

Tier 2, strong fundamentals, 18 to 36 months:

5. Null-space constrained updates generalizing from editing to unlearning and
   continual learning. Mechanism: right-to-be-forgotten pressure plus the
   catastrophic-forgetting tax; AlphaEdit showed the projection trick is one
   line once the covariance is in hand. Refuted if null-space methods remain
   editing-benchmark-only through 2028.
6. Formal verification of the monitor, not the model: zonotope and SMT
   certificates for probes and guardrail heads. Mechanism: verifying an LLM is
   intractable, verifying a linear or shallow head is routine, and "certified
   monitor" is a sellable artifact in finance and medical deployments. Refuted
   if no vendor ships a certificate for a deployed guardrail head by 2028.
7. Persona stability as quantitative alignment engineering. Mechanism: the
   Lee-Kondor-Ngo log-pooling results turn the Waluigi effect from folklore into
   theorems with design consequences (three-outcome pooling, manifest-then-
   suppress); persona products keep having drift incidents. Refuted if no
   persona-robustness eval suite exists by 2028.
8. Filesystem-as-architecture and context engineering standardization (ICM and
   successors). Mechanism: the practice is already universal (CLAUDE.md, skills
   trees, numbered stage folders); papers now name it; standardization follows
   naming. This one is partially post-buzz: the practice preceded the theory.
   Refuted if no interop convention (shared stage-contract format) emerges by
   2028.

Tier 3, deliberate anti-calls, real theory that will not become engineering buzz
on this horizon:

9. Catalytic computing as a memory-management technique for ML systems. The
   theory line (CL captures TC1, QCL in EQP, DQC1 simulations, the CBPL equals
   CL derandomization) is real and advancing, but no operating system lends
   another process's RAM, and uncomputation requires retaining exactly the
   information the claim removes. Expect continued TCS results, zero production
   systems. This stays a complexity-theory subject.
10. Categorical deep learning and categorical cybernetics as mainstream
    practice. The unification is real and the optics formulation of RL is
    elegant, but the adoption bottleneck is tooling and the absence of a
    performance win; the buzz version will arrive diluted as "compositional AI"
    marketing. Sleeper risk: one framework with genuinely good developer
    experience could flip this.
11. Active inference as a named production paradigm. A decade of imminent
    breakout; the LLM-as-generative-model implementations visited in the
    documents are prompt engineering under new vocabulary. The ideas will ship,
    the brand will not.
12. Expander-graph routing for MoE and TDA over embeddings: both real, both
    staying niche diagnostics or theory on this horizon.

## Part 5: build order for the account

1. agenteval-bench TAR upgrade (weeks, pure Python, reuses bus.py primitives).
2. Crosscoder diff repo (one to two months, one GPU, checkable against published
   numbers). This is the portfolio's missing ML artifact and its subject sits in
   Tier 1.
3. Probe-verification extension (Z3 over a trained safety head) if the
   verification identity is the chosen differentiator.
4. Ledger-derived resume claims in new-recruit; committed benchmarks in sqltok.
5. Curriculum ingestion in daily-deep-learning.

The strategic through-line is unchanged from the v1 assessment and strengthened
by document C: the 2025-2026 research wave legitimizes exactly the thing this
account already does at depth, deterministic and adversarial verification of
agent systems. The portfolio position is "builds the instruments that check
whether any of this works", extended by one real ML artifact so the ML column
stops being the gap.

## Sources

- NeurIPS 2025 best papers: https://blog.neurips.cc/2025/11/26/announcing-the-neurips-2025-best-paper-awards/
- AlphaEdit: https://arxiv.org/abs/2410.02355
- Latent agentic substructures: https://arxiv.org/abs/2509.06701
- Quantum catalytic space: https://arxiv.org/abs/2506.16324
- TAR trajectory study: https://arxiv.org/abs/2506.18824
- Reproducible agentic evaluation: https://arxiv.org/abs/2604.01437
- Crosscoder sparsity artifacts: https://arxiv.org/abs/2504.02922
- Directional sheaf hypergraph networks: https://arxiv.org/abs/2510.04727
- Lossless vertex expanders: https://arxiv.org/abs/2504.15087 and https://focs.computer.org/2025/best-paper-awards/
- Interpretable Context Methodology: https://arxiv.org/abs/2603.16021
- Poggio, the levels of understanding framework revised: https://journals.sagepub.com/doi/10.1068/p7299
