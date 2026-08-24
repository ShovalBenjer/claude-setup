# Rising mathematics and the 2026 model stack

Status: dated snapshot, 2026-08-03. Written against web sources read on that date, not
against a benchmark I ran. Every capability claim below names its source and none of them
were reproduced locally, which is the difference between staged and verified.

Answers four questions asked on 2026-08-03: which mathematics is actually rising, whether
wavelets and quantum belong on that list, which models to use per task, and whether the
SHAP plus LightGBM plus Optuna stack is still the frontier.

---

## 1. The trend question, and the part I could not measure

The ask was for topics whose conference attendance trend line is rising the way
interpretability's did. **There is no public dataset of per-topic conference attendance.**
NeurIPS publishes neither per-session attendance nor per-track headcount. So the honest
instrument is a set of proxies: workshop count per venue per year, whether a topic
graduated from workshop to main track, whether new dedicated venues appeared, and whether
a spotlight or oral landed. Those are what the table below uses. Read it as ordinal, not
cardinal.

### The two you named, assessed straight

**Wavelets and the scattering transform: mature, not rising.** Mallat's scattering
transform dates to 2012 and 2013. It is a mathematical model of a CNN that produces
provable stability to deformations, and it remains genuinely useful. But the 2025 and 2026
literature is applied and domain-specific: retinal OCT classification, rat local field
potentials, Mars seismic source separation, medical imaging. That is the signature of a
technique that has found its niches and stopped expanding, which is the opposite of the
interpretability curve.

The one live seam worth watching: the scattering transform is the only architecture family
with **provable** interpretability rather than post-hoc interpretability, because its
filters are fixed and known rather than learned. If the SAE seed-instability results
below keep landing, "build interpretable by construction" becomes a live alternative to
"interpret after the fact", and scattering is the oldest instance of it. That is a
contrarian bet, not a trend.

**Quantum machine learning: high visibility, low conversion.** Active, well funded, with
NeurIPS tutorials going back to 2021 and survey activity in 2026. What it does not have is
a result that changed anyone's default pipeline. Judge it by the same standard you would
apply to your own repo: an area that has existed for a decade and produced no oracle
anyone runs is staged, not verified. Low EV on the rising-trend axis.

### What is actually rising, and one of them you should care about

| Area | Signal | Why it rises |
|---|---|---|
| **Singular Learning Theory** | Refined LLC paper took an ICLR spotlight; dedicated seminar, dedicated site, dedicated research org (devinterp) | The mathematical foundation under mech interp. Rides that curve rather than competing with it |
| **Geometry and topology of learning spaces** | Connectivity and singularities of ReLU learning spaces (2602.00693), fractal dynamics of SGD (2503.22478) | Same driver: people want to know what the loss landscape actually is |
| **Neural operators and PDE learning** | AI4Science labs and dedicated tracks | Physical AI (your episode 154) needs it |
| **Optimal transport and flow matching** | Already crossed into production | Rising phase is over; this is now infrastructure |

**Singular Learning Theory is the answer to your question.** Watanabe's result is that
neural networks are *singular* statistical models: the map from parameters to function is
not injective, the Fisher information matrix is degenerate, and therefore classical
asymptotics (AIC, BIC, the usual Laplace approximation) simply do not apply. The geometry
in the neighbourhood of the degenerate points determines the asymptotics of learning. The
**Local Learning Coefficient** is the singularity-aware complexity measure that comes out
of it, and the refined variant has been used to show attention heads differentiating and
specialising over training.

Why this is the high-EV bet rather than a curiosity: it is to mechanistic interpretability
what measure theory is to probability. Mech interp is currently a pile of empirical
techniques with a seed-stability problem. SLT is the candidate theory underneath it. If
interpretability keeps growing, the field will go looking for foundations, and this is the
one that already has them.

**The connection to the termination idea from the previous session is not decorative.**
The LLC measures degeneracy at a point in training, and developmental interpretability uses
it to find phase transitions: moments where the model's internal structure reorganises. A
phase transition is a convergence event. Your four-layer termination schema is asking the
same question at the behavioural altitude that LLC asks at the parameter altitude: **when
has this system finished changing?** That is a real correspondence and it is worth one
afternoon of reading before you build anything.

### The counterweight you should carry into any of this

The 2026 interpretability literature is busy publishing its own limits, and this is the
most useful thing about it:

- **Seed dependence.** Two SAEs trained on identical model and data learn different
  features. The resolution is that individual features are unstable while the **subspaces
  they span are reproducible**. So a named feature is not a fact about the model.
- **Compositional failure.** Linear probes and SAEs do not generalise to novel
  combinations of features they were trained on. The paper is titled *Stop Probing, Start
  Coding*, which tells you the mood.
- **Curvature.** Concepts may live on manifolds, and SAEs assume flat directions. Open.
- **Superposition as lossy compression.** Superposition is proposed as the *mechanism* of
  adversarial vulnerability, which makes the whitebox-to-blackbox transfer in ExplAInable
  153 a mechanistic-interpretability result rather than a security curiosity.

---

## 2. Tabular: TabPFN-3 changes the default, with one hard catch

**Correction first: TabPFN is not Google's.** It is Prior Labs, the Freiburg group.
Getting the owner wrong matters here because the licence is the whole decision.

**TabPFN-3 was released 2026-05-12** and supports **up to 1M rows in context**. Precise
envelope: 1,000,000 x 200, or 100,000 x 2,000, or 1,000 x 20,000 (rows x features).
Feature count trades against row capacity.

The numbers, from the TabArena leaderboard as reported in the technical report:

| Model | Elo | Training cost |
|---|---|---|
| **TabPFN-3** | **1673** | 4.97s per 1,000 samples, no tuning |
| Tuned LightGBM | 1433 | 417s per 1,000 samples |
| Tuned + ensembled XGBoost | 1375 | comparable to LightGBM |

TabPFN-2.5 already had a **100% win rate against default XGBoost** on datasets up to
10,000 rows and 500 features, and 87% up to 100K rows.

### The catch, and it is not small

**The TabPFN-3 weights ship under `tabpfn-3-license-v1.0`, which permits research and
internal evaluation and forbids commercial or production use, including of the model's
outputs.** Commercial routes are the API (TabPFN-3-Plus) or an enterprise licence with
on-prem and VPC options on SageMaker and Azure AI Foundry.

For you this splits cleanly by lane:

- **Lane A, harness telemetry.** Internal analysis of your own ledgers. Squarely inside
  the licence. Use the weights.
- **Lane B, resume engine.** If anything about it is ever commercial or user-facing, the
  weights are out and you need the API or a licence. Do not build a product on a research
  licence and discover it at launch.

### When trees still win

Not a formality. Gradient-boosted trees keep the advantage on **large tables, CPU-only
serving, and operational simplicity.** A LightGBM model is a file you can score anywhere,
in any language, with no GPU and no licence question. TabPFN-3 is a foundation model with
a forward pass and a legal envelope.

The pragmatic pattern: **TabPFN-3 to find the ceiling, LightGBM to ship it.** Run TabPFN-3
first, in minutes, to learn what performance is achievable on the data at all. That number
tells you whether the feature engineering is the problem or the data is. Then decide
whether a tuned tree gets close enough to deploy.

Also worth naming since it appeared in the same search: **TabPrep** argues that current
tabular benchmarks have a feature-engineering gap, and **LimiX-2M** targets low-rank
collapse and attention bottlenecks in tabular foundation models. The field has a critique
literature now, which is a sign it is real.

---

## 3. Is SHAP plus LightGBM plus Optuna still the latest?

**It is still correct and it is no longer the frontier.** Three separate answers, because
it is three separate tools.

**LightGBM: no longer the accuracy frontier, still the deployment frontier.** See above.
1433 Elo against 1673 is not a rounding error.

**Optuna: still current, no successor.** The alternatives are lateral rather than newer:
DEHB, DEAP and Nevergrad on the evolutionary side; Orion and RayTune covering both
Bayesian and evolutionary. AutoGluon (1.5.x is current) automates selection, tuning and
ensembling end to end and is the thing to reach for when you want a strong baseline rather
than a tuned model. The real change is not that Optuna aged, it is that **TabPFN-3 needs
no tuning at all**, so on small and medium tables the entire HPO step can disappear.

**SHAP: still the default, with a known axiom violation you should be able to state.**
TreeSHAP is exact, fast, and the only method giving consistent local and global
explanations from one framework, which is why it stays. But **TreeSHAP samples from the
conditional distribution rather than the marginal**, which violates the Shapley axiom that
a non-contributing feature gets zero attribution. So a TreeSHAP value can credit a feature
the model never used, if that feature is correlated with one it did.

For your harness-telemetry build that caveat is load-bearing, not academic. Your features
are heavily correlated by construction: effort level, model, token count and time-of-day
all move together. **TreeSHAP will spread credit across the correlated block and you will
read it as four findings when it is one.** Mitigation: cluster correlated features first
and attribute at the cluster level, and report the correlation structure alongside the
attribution rather than under it.

---

## 4. Time series: Chronos-2

**Chronos-2 is the current leader and the recommendation.** It beats TimesFM-2.5 and TiRex
on **GIFT-Eval** on win rate and skill score under both WQL and MASE, and beats existing
time-series foundation models by a large margin on **fev-bench**, with the largest gains on
**covariate-informed** tasks.

That last clause is the one that matters for you. Univariate forecasting is a solved
demo. The real problem always has covariates, and that is exactly where Chronos-2's margin
is largest. An Alibaba comparison against a production retail forecasting system found
Chronos-2 crossed the line where the others did not: better monthly demand, stronger daily
dynamics, and **a much smaller feature surface than the incumbent stack**.

Alternatives, for the record: **MOIRAI** was designed multivariate from the start where
Chronos-2 added it in late 2025, and **TiRex-2** generalises TiRex to multivariate and
streaming. If you need streaming, look at TiRex-2 before assuming Chronos-2.

Worth knowing before betting a pipeline on any of them: there is a 2026 paper specifically
on **catastrophic forgetting in continual time series forecasting** for foundation versus
specialised models. Zero-shot excellence and continual adaptation are not the same
property.

---

## 5. Embeddings

Two boards, two answers, and conflating them is the usual mistake. **MTEB v2 scores are
not comparable to MTEB v1.**

| Need | Model | Note |
|---|---|---|
| Open-weight, general | **Qwen3-Embedding-8B** | Top of MTEB v2 among open weights, roughly 75 average; 70.6 on the multilingual cut |
| Multilingual, highest | **KaLM-Embedding-Gemma3-12B** (Tencent) | #1 on MMTEB at 72.32 as of July 2026, Gemma 3 backbone, 3840 dims |
| English, licence permitting | **NV-Embed-v2** | Leads MTEB English |
| Hosted | Cohere embed-v4 (65.2), OpenAI text-embedding-3-large (64.6) | Below open weights now |

**For your work specifically, the multilingual board is the only one that counts.** Your
corpora are Hebrew and English code-switched inside single messages. An English-leading
model is the wrong instrument no matter what its headline number says, so the choice is
between Qwen3-Embedding-8B and KaLM-Embedding-Gemma3-12B, and the tiebreak is whether
3840 dimensions is affordable in your vector store.

Note the dimension count against the SAE idea from the previous session: an overcomplete
sparse autoencoder over 3840-dimensional embeddings is a bigger training job than over
Qwen3's. Start with the smaller one.

---

## 6. NVIDIA and open weights

**Nemotron 3** is the current family: Nano, Super, Ultra. The Nano uses a **hybrid
Mamba-Transformer MoE architecture with a 1M-token context window**, and the Super is
**120B total with 12B active** (`NVIDIA-Nemotron-3-Super-120B-A12B`, FP8 and BF16 on the
Hub). Pretraining added 3 trillion new tokens weighted toward code, maths and reasoning,
and NVIDIA releases a large portion of the pretraining data openly, which is unusual and
is the actual reason to care.

**The honest positioning, which NVIDIA's own coverage concedes: DeepSeek V3.2 and Qwen3.5
outperform Nemotron on absolute capability. Nemotron wins on inference efficiency on
NVIDIA hardware.** So the decision rule is not "which is smartest", it is "am I serving on
NVIDIA silicon and does throughput per dollar decide this". If you are calling a hosted
API, this whole row is irrelevant to you.

For distilled reasoning specifically, **OpenReasoning-Nemotron** ships at 7B, 14B and 32B
with strong maths, science and code numbers, and 32B is the size that fits a single
workstation card.

---

## 7. What I would actually put in the stack

Ordered by what unblocks what, not by interest.

1. **TabPFN-3 weights on harness telemetry.** Internal analysis, so the research licence
   covers it. This is the fastest path to the question the model-selection rules have been
   arguing about without measurement since 29 July.
2. **LightGBM plus TreeSHAP alongside it, with correlated features clustered before
   attribution.** TabPFN-3 gives the ceiling; the tree gives the explanation and the
   artifact you can ship. Running both is not redundancy, it is the ceiling-versus-shippable
   split.
3. **Qwen3-Embedding-8B** for anything touching the Hebrew corpora, and as the substrate
   if the sparse-autoencoder-over-voice idea gets built.
4. **Chronos-2** only if a real forecasting question appears. Nothing in the four lanes
   needs it today, and adopting a foundation model with no question to answer is the
   connector mistake in a different costume.
5. **Nothing quantum. Nothing wavelet**, unless the interpret-by-construction bet in
   section 1 is one you specifically want to take.

## Coverage and what is not established here

Sources were read on 2026-08-03 through web search and are listed below. **No benchmark in
this document was reproduced locally.** The Elo figures, win rates and MTEB scores are
vendor-reported or leaderboard-reported and inherit whatever selection effects those
carry, which for TabPFN's numbers means they come from the authors of TabPFN.

Conference trend claims rest on the proxies named in section 1, not on attendance data,
because attendance data is not published. Treat the ordering as an argument, not a
measurement.

The TabPFN-3 licence summary is read from the model card and the changelog. **Before
anything commercial touches it, read the licence text itself rather than this paragraph.**

## Sources

Tabular: [TabPFN-3 Technical Report](https://arxiv.org/abs/2605.13986) ·
[Prior-Labs/tabpfn_3 model card](https://huggingface.co/Prior-Labs/tabpfn_3) ·
[TabPFN-2.5 report](https://arxiv.org/html/2511.08667v1) ·
[TabPrep](https://arxiv.org/pdf/2606.02384) · [LimiX-2M](https://arxiv.org/pdf/2606.04485)

Time series: [Chronos-2](https://arxiv.org/html/2510.15821v1) ·
[Amazon Science announcement](https://www.amazon.science/blog/introducing-chronos-2-from-univariate-to-universal-forecasting) ·
[TiRex-2](https://arxiv.org/html/2607.01204v1) ·
[Catastrophic forgetting in continual TS forecasting](https://arxiv.org/pdf/2510.00809)

Singular learning theory: [The Local Learning Coefficient](https://arxiv.org/pdf/2308.12108) ·
[Refined LLC and attention head specialisation](https://openreview.net/forum?id=SUc1UOWndp) ·
[devinterp](https://devinterp.com/) ·
[Topology and geometry of ReLU learning spaces](https://arxiv.org/pdf/2602.00693) ·
[Almost Bayesian: fractal dynamics of SGD](https://arxiv.org/pdf/2503.22478)

Interpretability limits: [Unstable Features, Reproducible Subspaces](https://arxiv.org/pdf/2606.12138) ·
[Stop Probing, Start Coding](https://arxiv.org/html/2603.28744) ·
[Do SAEs Capture Concept Manifolds?](https://arxiv.org/html/2604.28119v1) ·
[Superposition as Lossy Compression](https://arxiv.org/html/2512.13568)

Models: [Nemotron 3 Nano](https://huggingface.co/blog/nvidia/nemotron-3-nano-efficient-open-intelligent-models) ·
[Nemotron-3-Super-120B-A12B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8) ·
[OpenReasoning-Nemotron](https://huggingface.co/blog/nvidia/openreasoning-nemotron) ·
[MTEB rankings March 2026](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/) ·
[Embedding models 2026 comparison](https://milvus.io/blog/choose-embedding-model-rag-2026.md)
