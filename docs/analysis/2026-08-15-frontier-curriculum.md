# 2026-08-15: frontier curriculum, from foundations to the audited frontier

Curriculum source for the daily-deep-learning platform, distilled from the five
operator-supplied research documents after the audit in
`2026-08-15-research-context-audit-and-forecast.md`. Only material that survived
the audit appears; items ruled invented carry no unit, items ruled overclaimed
appear with the honest version. Ordering is strictly prerequisite-first: every
unit lists what it depends on, and no unit uses a concept a prior unit has not
built.

Format contract, matching the platform's house style: each unit ships with a
hook, a "know by end" sentence, one intuition anchor, precise definitions, one
drill, and SRS card candidates. This file specifies slug, titles, dependencies,
know-by-end, drill, cards, and sources; Hebrew bodies are authored in-repo per
unit. Register units in `tools/build_curriculum.py` in the order given, tracks
R0 and R4 first, respecting the curriculum budget check (add incrementally).

Track map. R0 foundations, R1 the serving stack of today, R2 post-training,
R3 interpretability, R4 agents and verification (the account's lane, deepest
track), R5 formal methods, R6 the generation frontier, R7 theory culture
(elective, anti-hype flagged). Capstones tie tracks to the work map:
R3 ends in the crossdiff repo, R4 ends in the agenteval-bench upgrade,
R5 ends in probe-verify.

## Track R0: foundations

r0-entropy-kl | Entropy and KL divergence | אנטרופיה ומרחק KL
depends: none. Know by end: read H(p) as average surprise and KL(p||q) as the
cost of believing q when p is true. Drill: compute both by hand for two
three-outcome distributions. Cards: entropy formula; KL asymmetry; why KL zero
means identical distributions. Sources: any information theory text; used by
r2-diversity-collapse, r3-crosscoders.

r0-projections-nullspace | Projections, SVD, null space | הטלות, SVD ומרחב האפס
depends: none. Know by end: decompose a matrix with SVD and state what the null
space of a covariance matrix contains. Drill: project a vector onto the null
space of a rank-1 covariance in numpy. Cards: SVD shapes; projector formula
P = I minus VV^T on kept directions; why singular covariances need
pseudo-inverses. Sources: used by r2-nullspace-editing.

r0-bayes-updating | Bayesian updating | עדכון בייסיאני
depends: r0-entropy-kl. Know by end: turn prior plus likelihood into posterior
and name the evidence term. Drill: two-hypothesis medical-test update by hand.
Cards: Bayes rule; posterior proportional to prior times likelihood; what
"conjugate" buys. Sources: used by r4-metareasoning, r7-active-inference.

r0-graphs-laplacian | Graphs and the Laplacian | גרפים והלפלסיאן
depends: none. Know by end: build L = D minus A and explain why its quadratic
form measures neighbor disagreement. Drill: compute Lx for a 4-node path graph.
Cards: Laplacian definition; smoothness as x^T L x; connected components in the
spectrum. Sources: used by r7-sheaf-laplacians, r4-code-property-graphs.

r0-complexity-space | Time, space, and reductions | זמן, מקום ורדוקציות
depends: none. Know by end: place P, NP, PSPACE, logspace, and state what a
conditional lower bound is. Drill: explain why SETH-conditional means "unless
SAT gets faster". Cards: class containments; reduction direction; conditional
versus unconditional. Sources: used by r1-attention-cost, r7-catalytic-space.

r0-lm-as-distribution | A language model is a distribution | מודל שפה כהתפלגות
depends: r0-entropy-kl. Know by end: read p(x) as a product of next-token
conditionals and connect temperature to entropy. Drill: compute the probability
of a 3-token sequence from given conditionals at two temperatures. Cards: chain
rule of LMs; temperature effect; perplexity as exponentiated cross-entropy.
Sources: used by everything in R1 and R2.

## Track R1: the serving stack of today

r1-attention-cost | Attention and its quadratic wall | קשב והקיר הריבועי
depends: r0-lm-as-distribution, r0-complexity-space. Know by end: derive the
N squared cost and state the SETH-conditional result that exact subquadratic
attention is unlikely in general. Drill: count multiplies for N=4, d=2 by hand.
Cards: QKV shapes; why softmax rows couple all pairs; "conditional" in the
lower bound. Sources: arXiv 2302.13214.

r1-kv-cache | The KV cache | מטמון ה-KV
depends: r1-attention-cost. Know by end: explain why generation is memory-bound
and what cache size scales with. Drill: compute cache bytes for a given model
config. Cards: what is cached and why; prefill versus decode; bandwidth as the
bottleneck. Sources: any serving-systems writeup; grounds r1-speculative and
r6 units.

r1-sampling-entropy | Sampling controls | בקרות דגימה
depends: r0-lm-as-distribution. Know by end: relate temperature, top-p, and
entropy targets, and predict their failure modes. Drill: given a toy
distribution, apply top-p 0.9 and renormalize. Cards: temperature versus
truncation; when greedy repeats; entropy-aware decoding as the diversity lever.
Sources: grounds r2-diversity-collapse.

r1-speculative-decoding | Speculative decoding, then trees | פענוח ספקולטיבי
depends: r1-kv-cache. Know by end: explain draft-verify acceptance and why tree
variants raise accepted tokens per step. Drill: hand-simulate acceptance of a
3-token draft. Cards: why verification is exact; acceptance rate economics;
tree speculation in one line. Sources: the 2023 wave papers; classified in the
audit as today's buzz, taught as the anchor analogy for the forecast.

r1-quantization-mx | Quantization and MX formats | קוונטיזציה ופורמטי MX
depends: r1-kv-cache. Know by end: explain block-shared scales (E8M0 over
32-element blocks) and what actually breaks at FP4. Drill: quantize 8 values to
a shared-scale int grid and measure error. Cards: per-tensor versus per-block
scales; why outliers hurt; "zero loss" claims and how to check them. Sources:
OCP MX spec; audit note on the overclaim.

r1-long-context-limits | Long context, honest limits | הקשר ארוך, גבולות כנים
depends: r1-attention-cost, r1-kv-cache. Know by end: name what long context
costs, what retrieval solves cheaper, and why "context window as memory" is a
metaphor. Drill: estimate cost of 1M-token prefill versus a retrieval call.
Cards: context versus retrieval tradeoff; the catalytic-context analogy and why
the audit ruled it a metaphor. Sources: audit part 2.

r1-token-budget-selection | Selection under a token budget | בחירה תחת תקציב
depends: r1-long-context-limits. Know by end: pose schema or context selection
as budgeted maximum coverage and explain the greedy guarantee and the CELF
speedup. Drill: run the greedy by hand on 4 tables with weights and costs.
Cards: submodularity in one sentence; 1 minus 1/e; lazy evaluation invariant.
Sources: the account's own sqltok `select/coverage.py`; this unit teaches from
owned code.

## Track R2: post-training

r2-rlhf-to-dpo | From RLHF to direct alignment | מ-RLHF ליישור ישיר
depends: r0-bayes-updating, r1-sampling-entropy. Know by end: trace reward
model plus PPO to the DPO family and read the SimPO margin loss. Drill: walk
one preference pair through the SimPO loss with beta and gamma given. Cards:
what the reference model does; length normalization; why direct losses won.
Sources: arXiv 2405.14734, arXiv 2402.01306.

r2-diversity-collapse | Diversity collapse | קריסת גיוון
depends: r2-rlhf-to-dpo, r0-entropy-kl. Know by end: state the Artificial
Hivemind finding (intra and inter-model homogenization) and its mechanism
(alignment optimizing toward one consensus of quality). Drill: measure
self-similarity of 5 sampled answers to one open prompt. Cards: what
Infinity-Chat measured; why judges punish valid diversity; the
synthetic-data-loop risk. Sources: NeurIPS 2025 best paper.

r2-personas-log-pooling | Personas and log pooling | פרסונות ואיגום לוגריתמי
depends: r0-bayes-updating. Know by end: model subagents as pooled
distributions and state why strict unanimity fails under linear pooling and in
binary outcome spaces but holds with three-plus outcomes. Drill: pool two
three-outcome distributions with log weights and compare to linear pooling.
Cards: Waluigi effect in one sentence; manifest-then-suppress; why this is now
theorems, not folklore. Sources: arXiv 2509.06701, ICML 2026.

r2-shallow-alignment | Alignment a few tokens deep | יישור בעומק אסימונים
depends: r2-rlhf-to-dpo. Know by end: explain the finding that safety behavior
concentrates in early response tokens and what deep alignment demands. Drill:
design one probe prompt pair that tests depth versus prefix masking. Cards:
the shallow-prefix result; why deep representation shifts bypass it. Sources:
ICLR 2025 outstanding paper (Qi et al.).

r2-nullspace-editing | Null-space model editing | עריכת מודל במרחב האפס
depends: r0-projections-nullspace. Know by end: state AlphaEdit's move
(project the update into the null space of preserved-knowledge activations)
and why the printed one-line formulas in surveys garble the SVD-thresholded
projector. Drill: perform a null-space-constrained rank-1 update on a toy
2-layer map. Cards: what the covariance C encodes; why orthogonal updates
cannot disturb preserved keys; unlearning as the next application. Sources:
arXiv 2410.02355; audit garble note.

## Track R3: interpretability

r3-probes | Linear probes | בדיקות ליניאריות
depends: r0-projections-nullspace, r1-attention-cost. Know by end: train a
linear probe on hidden states and say what probe accuracy does and does not
prove. Drill: probe a small model's final hidden state for sentiment. Cards:
probe versus causal claim; selectivity controls. Sources: standard probing
literature; grounds r5-probe-verify.

r3-sae-basics | Sparse autoencoders | מקודדים דלילים
depends: r3-probes, r0-entropy-kl. Know by end: explain dictionary learning on
activations and the L1-versus-TopK sparsity choice. Drill: read an SAE feature
dashboard and judge one feature's interpretability. Cards: overcomplete
dictionary; reconstruction versus sparsity tradeoff; why L1 distorts
magnitudes. Sources: SAE literature; sets up BatchTopK.

r3-steering | Activation steering | היגוי אקטיבציות
depends: r3-probes. Know by end: add a direction to a residual stream and
predict the behavioral change and the side effects. Drill: steer a small model
with a published refusal direction. Cards: h minus alpha v; when clamping beats
adding; runtime guardrail framing. Sources: representation engineering line;
forecast item 4.

r3-crosscoders | Crosscoders and model diffing | קרוס-קודרים והשוואת מודלים
depends: r3-sae-basics. Know by end: explain the shared dictionary over base
and chat activations and why diffing beats interpreting one model when the
question is "what changed". Drill: read a base-only, chat-only, shared latent
split and interpret three latents. Sources: crosscoder line; forecast item 2.

r3-latent-decoupling | Sparsity artifacts | ארטיפקטים של דלילות
depends: r3-crosscoders. Know by end: define complete shrinkage and latent
decoupling, and explain how BatchTopK plus latent scaling removes them. Drill:
given latent norms per side, classify a latent as decoupled or genuinely
chat-specific. Cards: why L1 makes fake chat-only latents mathematically
cheap; the KL-recovery metric honestly stated. Sources: arXiv 2504.02922.

r3-capstone-crossdiff | Capstone: crossdiff | פרויקט: crossdiff
depends: all R3. Deliverable: the crossdiff repository from the work map,
reproducing latent-decoupling findings on a small pair with every metric
checkable against the paper. Definition of done is the work map falsifier.

## Track R4: agents and verification, the home track

r4-trajectories-tar | Thought, action, result | מחשבה, פעולה, תוצאה
depends: r0-lm-as-distribution. Know by end: define TAR trajectories, why
outcome-only evaluation misses misaligned steps, and what the ASE 2025 study
labeled between components. Drill: hand-label thought-action alignment for a
5-step trajectory from a real session. Cards: the triple; within-step versus
across-step relations; trajectory publication as reproducibility. Sources:
arXiv 2506.18824, arXiv 2604.01437; forecast item 1.

r4-replay-determinism | Deterministic replay | שחזור דטרמיניסטי
depends: r4-trajectories-tar. Know by end: name what breaks replay
(timestamps, randomness, external state) and the design moves that restore it.
Drill: find the two nondeterminism sources in a given script and fix them.
Cards: record versus replay mode; why the harness bans wall-clock in
workflows. Sources: this repo's own workflow constraints as the worked
example.

r4-ledgers-hashchains | Append-only ledgers and hash chains | יומנים וטבעות גיבוב
depends: none in-track. Know by end: build a hash-chained JSONL ledger and
explain self-describing coverage (hashing the list of hashed fields). Drill:
tamper a middle row of a copy of `state/bus.jsonl` and watch verification
fail. Cards: prev-hash linking; canonical JSON; why narrowing coverage must be
visible. Sources: this repo `tools/bus/bus.py`; taught from owned code.

r4-mutation-testing | Mutation testing | בדיקות מוטציה
depends: none in-track. Know by end: explain why a test suite's real oracle is
whether planted bugs turn it red, and the green-baseline precondition. Drill:
write one semantic mutation for a function you wrote this month and run the
suite. Cards: mutant versus syntax error; caught-by-named-check versus
caught-by-crash; LLM-directed spec generation as the pilot. Sources: this repo
`tools/audit/mutate.py`; document E's one directly actionable item.

r4-process-scoring | Step-level process scoring | ניקוד ברמת הצעד
depends: r4-trajectories-tar, r2-rlhf-to-dpo. Know by end: distinguish outcome
reward from process reward and apply per-step verdicts to agent trajectories.
Drill: score a trajectory whose answer is right but whose middle step
contradicts its own thought. Cards: PRM in one line; why process scoring is
the eval-side form of test-time compute. Sources: Lightman et al.; forecast
reclassification note.

r4-sandboxing-ebpf | Sandboxing agents | ארגז חול לסוכנים
depends: r4-replay-determinism. Know by end: layer the enforcement story:
process, container, syscall policy (eBPF), and what each catches. Drill: write
the invariant list (files, network, processes) for one of the account's
agents. Cards: audit trail plus enforcement as the two halves of governance;
why container-only is not the end state. Sources: forecast item 16.

r4-code-property-graphs | Code property graphs | גרפי תכונות קוד
depends: r0-graphs-laplacian. Know by end: combine AST, control flow, and
dependence into one queryable graph and say what file-and-grep retrieval loses.
Drill: trace one dataflow query by hand on a 20-line function. Cards: the
three layers; why agent context selection is the bottleneck; Joern as mature
tooling. Sources: forecast item 15; `symbol_graph.py` as the local seam.

r4-context-engineering-icm | Filesystem as architecture | מערכת קבצים כארכיטקטורה
depends: r4-ledgers-hashchains. Know by end: state the ICM pattern (numbered
stages, per-stage contracts, plain text interfaces) and map it onto this
account's harness. Drill: diagram claude-setup as an ICM instance and mark
what it adds (gate, refuter, mutations). Cards: practice preceded the paper;
what a stage contract declares. Sources: arXiv 2603.16021.

r4-agent-memory-cls | Two-store agent memory | זיכרון סוכן בשני מחסנים
depends: r4-context-engineering-icm. Know by end: explain complementary
learning systems (fast episodic store, slow consolidation) and map it to agent
memory designs. Drill: classify five memory features of a known agent product
into the two stores. Cards: hippocampus-neocortex analogy honestly bounded;
why consolidation prevents catastrophic forgetting. Sources: CLS literature;
forecast item 17.

r4-metareasoning | Bounded rationality as a budget | רציונליות חסומה כתקציב
depends: r0-bayes-updating. Know by end: apply the value-of-computation rule
(stop searching when marginal value drops below delay cost) and connect it to
threshold-triggered replanning. Drill: decide compute allocation for three
queries of different stakes. Cards: Simon satisficing; Russell-Wefald rule;
intermittent replanning (Entropy 2026) as the modern form. Sources: doi
10.3390/e28030269.

r4-capstone-agenteval | Capstone: agenteval-bench upgrade | פרויקט: שדרוג agenteval
depends: all R4. Deliverable: work map items 1 to 6 for agenteval-bench.
Definition of done is each item's falsifier.

## Track R5: formal methods

r5-smt-basics | SAT, SMT, and Z3 | SAT, SMT ו-Z3
depends: r0-complexity-space. Know by end: distinguish SAT from SMT (the
audit's recurring garble), write a small Z3 query, read a model and an unsat
core. Drill: encode "this linear function stays below tau on this box" in Z3.
Cards: theories in SMT; sat means counterexample here; unsat means proof.
Sources: Z3 docs.

r5-constrained-decoding | Grammar-constrained decoding | פענוח מאולץ דקדוק
depends: r5-smt-basics, r1-sampling-entropy. Know by end: constrain generation
with a grammar and state what is and is not guaranteed (syntax yes, semantics
no, "no memory leaks" was the audit's overclaim). Drill: constrain a model to
emit valid JSON for a schema. Cards: logit masking; guarantee boundary.
Sources: constrained decoding literature; audit part 2.

r5-nn-verification | Verifying small networks | אימות רשתות קטנות
depends: r5-smt-basics, r3-probes. Know by end: explain reachability with
zonotopes and why the tractable target is the monitor, not the model. Drill:
propagate a 2D box through one ReLU layer by hand. Cards: zonotope as
projection shadow; branch and bound; verify-the-monitor economics. Sources:
NN verification literature; forecast item 10.

r5-differential-testing | Differential and fuzz oracles | אורקלים דיפרנציאליים
depends: r4-mutation-testing. Know by end: use a second implementation as the
oracle and seeded fuzzing as the witness generator; connect to quantization
divergence hunting. Drill: run this repo's regex differential oracle and read
one disagreement report. Sources: `tools/hookgate/diff_oracle.py`; document E
quantization fuzzing item.

r5-capstone-probe-verify | Capstone: probe-verify | פרויקט: probe-verify
depends: all R5. Deliverable: the probe-verify module from the work map, an
SMT certificate for a trained safety probe. Definition of done is the work map
falsifier.

## Track R6: the generation frontier

r6-ssm-mamba | State space models and SSD | מודלי מרחב מצב
depends: r1-attention-cost. Know by end: explain linear-time sequence mixing
via structured state spaces and what the state space duality result unified.
Drill: run a 1D linear recurrence by hand and name what the state carries.
Cards: recurrence versus attention memory; semiseparable structure in one
line; hybrid models as the shipping form. Sources: arXiv 2405.21060.

r6-ttt-layers | Test-time training layers | שכבות אימון בזמן ריצה
depends: r6-ssm-mamba. Know by end: describe the hidden state as a small model
updated by gradient steps during inference. Drill: one inner-loop update by
hand on a linear model. Cards: hidden state as learner; what unbounded context
extrapolation claims and its checks. Sources: arXiv 2407.04620.

r6-discrete-diffusion | Masked diffusion LMs | דיפוזיה בדידה לטקסט
depends: r1-sampling-entropy. Know by end: explain absorbing-mask corruption
and iterative denoising, and why this attacks decoding latency plus infilling.
Drill: simulate 3 denoising steps on a 5-token masked sequence with given
confidences. Cards: parallel proposal versus sequential commitment; where
error accumulation bites. Sources: arXiv 2406.07524; forecast item 5.

r6-trajectory-conditioning | Non-Markovian denoising | דה-נואיזינג לא מרקובי
depends: r6-discrete-diffusion. Know by end: state CaDDi's move (condition on
the whole denoising trajectory, subsume causal LMs as a special case). Drill:
explain which failure of r6-discrete-diffusion this removes and at what cost.
Sources: arXiv 2502.09767, NeurIPS 2025.

r6-jepa | Predicting in latent space | חיזוי במרחב סמוי
depends: r3-sae-basics. Know by end: contrast generative token prediction with
latent prediction and say what task-irrelevant entropy means. Drill: name two
tasks where pixel-level generation wastes capacity. Cards: energy-based
objective in one line; world-model framing honestly bounded. Sources: JEPA
line.

## Track R7: theory culture, elective, anti-hype flagged

r7-tropical-relu | Tropical geometry of ReLU nets | גאומטריה טרופית
depends: r0-projections-nullspace. Know by end: read max-plus algebra and why
ReLU networks are tropical rational maps, enabling linear-region counting.
Anti-hype note: expressivity theory, not an engineering tool. Drill: count
linear regions of a tiny 2-layer ReLU net.

r7-sheaf-laplacians | Sheaves on graphs | אלומות על גרפים
depends: r0-graphs-laplacian. Know by end: explain restriction maps and how
sheaf Laplacians mitigate (not solve) oversmoothing in heterophilic graphs.
Anti-hype note: niche GNN tooling. Sources: sheaf NN line, DSHN arXiv
2510.04727.

r7-information-geometry | Fisher information and natural gradient | גאומטריית מידע
depends: r0-bayes-updating, r0-projections-nullspace. Know by end: read the
Fisher metric as local curvature of the likelihood and natural gradient as
reparameterization-invariant descent. Anti-hype note: K-FAC-style
approximations are where practice lives.

r7-catalytic-space | Catalytic computing | חישוב קטליטי
depends: r0-complexity-space. Know by end: state the full-tape restoration
model, the CL and QCL results, and exactly why the KV-cache application in
four of the five surveyed documents is a metaphor. Drill: articulate the
uncomputation objection in three sentences. Sources: arXiv 2506.16324; audit
part 2. This unit exists to teach hype immunology on a real case.

r7-category-optics | Lenses for learning | עדשות ללמידה
depends: r0-bayes-updating. Know by end: read a lens (forward map, backward
update) and see backprop, value iteration, and Bayes updates as one shape.
Anti-hype note: design language, no performance win; AlgebraicJulia as the
tooling niche. Sources: categorical cybernetics line.

r7-active-inference | Expected free energy | אנרגיה חופשית צפויה
depends: r0-bayes-updating, r4-metareasoning. Know by end: decompose G into
epistemic and pragmatic value and state the intermittent-trigger result.
Anti-hype note: the ideas ship as adaptive compute; the brand does not.
Sources: doi 10.3390/e28030269.

r7-pragmatics-rsa | Rational speech acts | פרגמטיקה חישובית
depends: r0-bayes-updating. Know by end: run one speaker-listener recursion
and explain an implicature it captures. Elective bridge to the linguistics
material in documents C and E. Sources: RSA literature.

## Sequencing summary

Minimum spine for the account's goals, in order: R0 complete, R1-01 to R1-04,
R4 complete with capstone, R3 complete with capstone, R5 complete with
capstone, R2 as reading support for R3, R6 and R7 as scheduled electives. The
three capstones are the same three artifacts the work map and the forecast
name as the portfolio: agenteval upgrade, crossdiff, probe-verify.
