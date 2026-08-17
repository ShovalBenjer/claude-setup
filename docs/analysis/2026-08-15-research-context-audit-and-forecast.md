# 2026-08-15: research context audit and forecast

Session record, lane A. The operator supplied five LLM-assisted research surveys
(two in English covering 2025-2026 conference results and categorical methods, one
in Hebrew covering "agent factories" and a four-layer interpretability framing, a
fourth covering the algebraic-topological turn, discrete diffusion, test-time
compute, and information-theoretic aesthetics, and a fifth that is a citation-free
catalog of roughly thirty techniques across mathematics, systems, software
engineering, linguistics, cognitive science, and computational arts) and asked two
questions: grade the account's implementation depth against the material, and map
the material onto the account's repositories, including a forecast of which
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
- Sixteen citation checks against the live web, covering every flagship claim in
  the first four documents and the two uncertain items in the fifth; the fifth
  document names no papers, so its audit is technique triage against primary
  knowledge rather than citation forensics. Verdicts are split three ways:
  verified, garbled, invented.

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
| GAIA, topos-theoretic generative AI | Verified as a theoretical program (single-author line, no working systems); "functorial backpropagation guarantees no representation drift" is overclaimed | arXiv 2402.18732, arXiv 2508.08293 |
| GLGENN, Clifford-algebra equivariant networks, ICML 2025 | Verified; the "8x fewer parameters than ResNets" and "eliminates ViT FFN bottlenecks" framing is garbled (the paper compares against baseline equivariant models on equivariant benchmarks) | arXiv 2506.09625 |
| Discrete masked diffusion LMs (MDLM) and trajectory-conditioned CaDDi | Verified; CaDDi is NeurIPS 2025 and the trajectory-conditioning description is accurate | arXiv 2406.07524, arXiv 2502.09767 |
| Test-time compute scaling and process reward models | Verified and already mainstream; the printed search objective is decorative pseudo-math | Lightman et al. 2023, Snell et al. 2024 |
| Intermittent active inference (threshold-triggered re-planning) | Verified, Entropy 2026 | doi 10.3390/e28030269 |
| DisCoCat, DisCoCirc, density matrices for lexical ambiguity | Verified research program (Coecke, Sadrzadeh, Clark line; lambeq tooling) | Coecke et al. 2010 onward |
| Birkhoff-Berlyne combined aesthetic measure with Kolmogorov complexity | Invented: the components are real (Birkhoff 1933, Berlyne 1971) but the printed measure divides by an uncomputable quantity and appears in no literature; "spectral curvature loss" is unsupported as a named method | n/a |
| Code Brutalism and anti-automation design wave | Real as a cultural trend, not a formal method | n/a |

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

- Document D (algebraic-topological turn, diffusion, test-time compute): the best
  citation hit rate of the four. Every novel anchor checked out, including two
  that read as invented and are not (GAIA and intermittent active inference). The
  glue fails the same way as the others: an aesthetic formula built on an
  uncomputable quantity, engineering overclaims for topos theory and Clifford
  networks, and the recycled catalytic KV-cache claim. Its real contribution to
  this audit is naming two subjects the v1 forecast underweighted: discrete
  diffusion language models and step-level process verification.

- Document E (technique catalog): the highest base-rate accuracy of the five,
  because it names techniques rather than papers. Triage of its roughly thirty
  items:
  - Real and correctly described: tropical geometry of ReLU networks, sheaf
    Laplacians for GNN pathologies (mitigate, not "completely resolve"), Fisher
    information geometry and natural gradient, SETH-conditional lower bounds on
    subquadratic attention (conditional, not "mathematically impossible"),
    test-time training layers, state space duality and the Mamba-2 line, JEPA,
    KTO and SimPO (the printed SimPO loss is correct), MX microscaling formats
    (E8M0 shared scales over 32-element blocks is accurate; "zero loss" at FP4
    is not), processing-in-memory for KV streaming, tree-structured speculative
    decoding, code property graphs, eBPF sandboxing, LLM-directed mutation
    testing, differential fuzzing for quantization, rational speech acts,
    construction grammar probing of LLMs, hierarchical predictive coding,
    complementary learning systems, bounded rationality as metareasoning (the
    printed stopping rule is the Russell-Wefald value of computation),
    adversarial stylometry.
  - Overclaimed absolutes: "completely resolve over-smoothing", "zero loss in
    perplexity", "guarantee generated code is free of memory leaks", "proving
    that specific mid-layer induction heads represent constructions natively"
    (the actual CxG probing literature finds models weakest on schematic
    constructions).
  - Confabulations: univalence-based verification of Triton kernels in Lean 4
    (Lean's type theory is not univalent; kernel verification exists, not via
    HoTT), MCP as a formally verified protocol with cryptographically signed
    messages (MCP is JSON-RPC schema contracts, no signing layer), the FPT
    treewidth pruning theorem as stated (no paper at that intersection was
    found), "inhibitory split-brain modular reasoning" as a named method, and
    "spectral curvature regularization", which recurs from document D and
    remains unsupported.

The consistent failure mode across all five documents is a synthesis layer that
upgrades real material into overclaimed engineering: invented citations in the
early documents, invented absolutes and confabulated hybrids in the later ones,
and pre-written metrics for systems that do not exist throughout. The account's own claim-plus-falsifier discipline
(`state/claims.jsonl`, `tools/refute/refute.py`) is the correct antidote and
should be applied to README claims, not only to harness claims.

## Part 3: per-repo actions

The full conversion of these actions into per-repo work items with acceptance
falsifiers lives in the companion file
`docs/analysis/2026-08-15-research-to-repo-work-map.md`; the summary here is the
reading view, the work map is the executable one.

1. agenteval-bench (largest gap, cheapest leverage): adopt Thought-Action-Result
   triples as the data model per the ASE 2025 study; hash-chain trajectory
   storage by porting `canonical` and `row_hash` from `tools/bus/bus.py` (stdlib
   only); replace key-presence checking with real jsonschema; enforce or delete
   `threshold` and `max_input_tokens`. This converts the weakest repo into the
   one that matches its README. Document D adds the natural second stage:
   step-level process scoring of trajectories (PRM-style verdicts per step, not
   only outcome grading), which is the evaluation-side form of the
   test-time-compute wave.
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
   points at them. One more citation now available: the intermittent active
   inference result (re-plan only when prediction error crosses a bound, Entropy
   2026) is a formal frame for the harness's event-driven wake and hook design.
   Worth a line in the docs, not an adoption project.
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
8. Document E items that land directly on existing code: LLM-directed mutation
   testing is `tools/audit/mutate.py` with the spec authorship automated; a
   pilot that generates candidate mutations for the modules with no mutation
   spec, keeping the named-check attribution, is a natural TODO row. Code
   property graphs are the formal version of what
   `intent-control-plane/src/intent_control_plane/symbol_graph.py` and
   `tools/map/codemap.py` approximate; if agent context ingestion becomes
   graph-shaped, those two modules are the seams. eBPF sandboxing is the
   kernel-level sibling of hookgate's userspace gate: worth tracking, not
   building.

## Part 4: forecast, what buzzes next and why

Anchors for calibration: speculative decoding became a buzzing subject in
2023-2024 because inference cost was the binding constraint and the technique
gave an order-of-magnitude lever without retraining. Long-horizon agent evals are
buzzing in 2025-2026 because agent deployment outran the ability to measure it.
Test-time compute scaling and process reward models belong to that same
already-buzzing class: document D presents them as frontier, but they are the
present, not the next; their next-step derivative is process-level verification
of agent trajectories (item 1 below). The pattern: a subject buzzes when a
binding constraint meets a technique with working code and a forcing event.
Applied to the material visited here:

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
5. Discrete diffusion language models (MDLM, trajectory-conditioned CaDDi, and
   the commercial diffusion-LM line). Mechanism: attacks the same binding
   constraint speculative decoding attacked, sequential decoding latency, and
   adds native infilling and constraint satisfaction; trajectory conditioning
   removes the error-accumulation objection to earlier discrete diffusion.
   Evidence now: MDLM and CaDDi with released code, commercial diffusion LMs
   demonstrating large token-throughput multiples. Trigger: a frontier-quality
   diffusion model at a large throughput multiple over autoregression. Refuted
   if no production diffusion LM endpoint from a major provider exists by
   2027-06.

Tier 2, strong fundamentals, 18 to 36 months:

6. Null-space constrained updates generalizing from editing to unlearning and
   continual learning. Mechanism: right-to-be-forgotten pressure plus the
   catastrophic-forgetting tax; AlphaEdit showed the projection trick is one
   line once the covariance is in hand. Refuted if null-space methods remain
   editing-benchmark-only through 2028.
7. Formal verification of the monitor, not the model: zonotope and SMT
   certificates for probes and guardrail heads. Mechanism: verifying an LLM is
   intractable, verifying a linear or shallow head is routine, and "certified
   monitor" is a sellable artifact in finance and medical deployments. Refuted
   if no vendor ships a certificate for a deployed guardrail head by 2028.
8. Persona stability as quantitative alignment engineering. Mechanism: the
   Lee-Kondor-Ngo log-pooling results turn the Waluigi effect from folklore into
   theorems with design consequences (three-outcome pooling, manifest-then-
   suppress); persona products keep having drift incidents. Refuted if no
   persona-robustness eval suite exists by 2028.
9. Filesystem-as-architecture and context engineering standardization (ICM and
   successors). Mechanism: the practice is already universal (CLAUDE.md, skills
   trees, numbered stage folders); papers now name it; standardization follows
   naming. This one is partially post-buzz: the practice preceded the theory.
   Refuted if no interop convention (shared stage-contract format) emerges by
   2028.

Tier 3, deliberate anti-calls, real theory that will not become engineering buzz
on this horizon:

10. Catalytic computing as a memory-management technique for ML systems. The
   theory line (CL captures TC1, QCL in EQP, DQC1 simulations, the CBPL equals
   CL derandomization) is real and advancing, but no operating system lends
   another process's RAM, and uncomputation requires retaining exactly the
   information the claim removes. Expect continued TCS results, zero production
   systems. This stays a complexity-theory subject.
11. Categorical deep learning and categorical cybernetics as mainstream
    practice. The unification is real and the optics formulation of RL is
    elegant, but the adoption bottleneck is tooling and the absence of a
    performance win; the buzz version will arrive diluted as "compositional AI"
    marketing. Sleeper risk: one framework with genuinely good developer
    experience could flip this. The same verdict covers topos-theoretic
    generative AI (a real but single-author theoretical program with no
    benchmark wins) and quantum-categorical semantics (DisCoCat, a fifteen-year
    program with mature tooling and a stable niche).
12. Active inference as a named production paradigm. A decade of imminent
    breakout; the LLM-as-generative-model implementations visited in the
    documents are prompt engineering under new vocabulary. The ideas will ship,
    the brand will not: the intermittent-planning result (Entropy 2026) is real
    and useful and will surface as "adaptive compute allocation" or event-driven
    agent scheduling, without the active inference name attached.
13. Expander-graph routing for MoE, TDA over embeddings, and Clifford-algebra
    equivariant networks: all real (GLGENN is an ICML 2025 result), all staying
    theory, niche diagnostics, or physics-and-geometry tooling on this horizon;
    equivariance already had its buzz cycle inside geometric deep learning. Code
    Brutalism is a cultural tailwind for exposed-telemetry design (this repo's
    dashboards already comply) rather than a technique, and needs no investment.

Document E additions, same tier logic:

14. Post-transformer sequence layers with inner-loop learning (test-time
    training layers, state space duality, the Mamba-2 line and successors).
    Tier 1. Mechanism: long-context cost is the binding constraint; TTT turns
    the hidden state into a learner, and the SSD line gives linear-time kernels
    that map onto GPU primitives. Trigger: a frontier hybrid shipping a
    non-attention backbone at context lengths attention cannot price. Refuted
    if frontier models remain pure-attention at 2027-06.
15. Graph-shaped repository context for coding agents (code property graphs
    over AST, control flow, and program dependence). Tier 1 to 2. Mechanism:
    agentic coding is bounded by context selection rather than model quality;
    file-and-grep retrieval loses dataflow; the tooling (Joern and kin) is
    mature and waiting for the agent interface. Trigger: a major coding agent
    shipping graph traversal as its retrieval layer. Refuted if agent context
    stays file-based through 2027-06.
16. Kernel-level agent sandboxing (eBPF syscall policy for autonomous code
    execution). Tier 1 to 2, paired with item 1: the audit trail and the
    enforcement boundary are the two halves of agent governance. Trigger: the
    first prominent agent-caused security incident. Refuted if agent sandboxes
    remain container-only through 2027-06.
17. Agent memory consolidation on the complementary learning systems pattern
    (fast episodic store plus slow parametric consolidation). Tier 2. The
    subject is already warming as "agent memory"; CLS is the citable
    architecture likely to survive the marketing. Refuted if no major agent
    framework ships a two-store consolidation design by 2028.
18. Already-buzzing rather than next, from document E: direct alignment
    objectives (KTO, SimPO) are the post-DPO present; MX microscaling formats
    ship in current hardware; tree speculative decoding is the mature form of
    the 2023 wave. Additional anti-calls: photonic accelerators and
    processing-in-memory are real but move on hardware timescales; univalent
    verification of GPU kernels is not a 2026-2028 subject; the arts items
    (microtonal diffusion synthesis, hyperbolic typography,
    constraint-satisfaction narrative graphs) are real niches that stay niches.

## Part 5: build order for the account

1. agenteval-bench TAR upgrade (weeks, pure Python, reuses bus.py primitives).
2. Crosscoder diff repo (one to two months, one GPU, checkable against published
   numbers). This is the portfolio's missing ML artifact and its subject sits in
   Tier 1.
3. Probe-verification extension (Z3 over a trained safety head) if the
   verification identity is the chosen differentiator.
4. Ledger-derived resume claims in new-recruit; committed benchmarks in sqltok.
5. Curriculum ingestion in daily-deep-learning.
6. LLM-directed mutation-spec pilot for the unguarded modules in this repo,
   document E's one directly actionable item.

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
- GAIA and topos theory for generative AI: https://arxiv.org/abs/2402.18732 and https://arxiv.org/abs/2508.08293
- GLGENN: https://arxiv.org/abs/2506.09625
- MDLM: https://arxiv.org/abs/2406.07524
- CaDDi, non-Markovian discrete diffusion: https://arxiv.org/abs/2502.09767
- Intermittent active inference: https://doi.org/10.3390/e28030269
- Test-time compute scaling: https://arxiv.org/abs/2408.03314
- Test-time training layers: https://arxiv.org/abs/2407.04620
- State space duality (Mamba-2): https://arxiv.org/abs/2405.21060
- SimPO: https://arxiv.org/abs/2405.14734 and KTO: https://arxiv.org/abs/2402.01306
- SETH-conditional attention lower bounds: https://arxiv.org/abs/2302.13214
- Construction grammar probing of language models: https://arxiv.org/abs/2302.02178
