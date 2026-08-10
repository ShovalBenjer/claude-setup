# Futuristic Learning Stack for an AI Engineer — April 2026 Edition

## The Frame: You Have Three Parallel Learning Projects

This is not one learning path — it is three running simultaneously, feeding each other:

1. **Scrape + curate Claude skills** → learn by reading real production-grade prompts, tools, and workflows
2. **Build your measurement stack** → TF-IDF / UMAP / t-SNE / GPT-judge as concrete engineering primitives, not theory
3. **Level up your math/ML foundations** → understand where Markov chains end and the 2026 frontier begins

Each section below is calibrated to where the April 2026 research frontier actually sits, not where textbooks left off.

***

## Part I: Claude Skills — The Strategy for Scraping, Curating, Non-Overlapping Coverage

### How Skills Actually Work (First Principles)

A Claude Code skill is a markdown file in `.claude/skills/` with a metadata header (name + description, ~100 tokens) and a body (full instructions loaded on-demand). At startup, Claude scans all skills, reads only the metadata, and loads the full body only when a task triggers the skill — meaning you can install dozens of skills without blowing context. The architecture is:[^1][^2]

```
Metadata (~100 tokens, always loaded)
└── SKILL.md body (loaded when triggered)
    └── Bundled resources: scripts/, references/, assets/ (loaded on demand)
```

The Anthropic official skills repository had **87,000+ GitHub stars** as of March 2026. This is the primary corpus for scraping.[^2]

### What to Scrape and Where

**Primary sources**:
- `github.com/anthropics/skills` — the canonical official repo (87K stars)[^2]
- `composio.dev/content/top-claude-skills` — curated community skills breakdown[^3]
- `firecrawl.dev/blog/best-claude-code-skills` — production-tested skills with benchmarks[^1]
- `towardsdatascience.com/how-to-build-a-production-ready-claude-code-skill` — architectural guide[^2]
- `lobeHub` — community skills marketplace with ratings and usage counts[^4]

**Scraping protocol**: Use the Firecrawl MCP skill itself to crawl the anthropics/skills repo recursively, extract every `SKILL.md`, and dump to a structured JSON. The Firecrawl skill has **>80% content recall on benchmark evaluations** and handles JavaScript-rendered pages. The output: a dataset of (name, description, body, tools_used, triggers) tuples.[^1]

### Deduplication and Non-Overlap — The Correct Method

Don't eyeball overlap. The right pipeline:

1. **Embed all skill descriptions** using `text-embedding-3-small` (1536-dim, cheap, fast)
2. **Cluster with UMAP → HDBSCAN** (not k-means; k-means requires choosing k, HDBSCAN finds structure). UMAP for dimensionality reduction first, HDBSCAN for cluster detection
3. **Visualize**: Skills in the same HDBSCAN cluster are semantically redundant — keep one per cluster, prefer the most-starred/most-used
4. **Domain filtering**: After deduplication, tag each remaining skill against your domain vocabulary (TF-IDF over the skill body against a domain glossary) to select only domain-relevant skills
5. **Coverage gap detection**: Embed your own task backlog, project to the same UMAP space, find tasks with no nearby skill cluster — those are your skills-to-build

This is not theoretical — it is the exact same pipeline as the semantic coverage gap detection from Part I of the earlier research, applied to skills as the "document corpus."

### Building Your Personal Skill Taxonomy

After scraping and deduplicating, the Claude skills landscape clusters into roughly these domains:

| Cluster | Example Skills | Keep if Domain Overlap |
|---|---|---|
| Code quality | TDD enforcer, linter, formatter | Almost always |
| Documentation | README generator, changelog, docstring writer | Usually |
| Research / web | Firecrawl agent, web search, paper summarizer | Yes if research-heavy |
| Memory management | Session consolidation, Playbook updater | **Always — this is the learning layer** |
| Evaluation / metrics | DeepEval scorer, LLM judge, golden generator | **Always — this is the feedback layer** |
| Security | Pre-commit audit, dependency scanner | Yes for production |
| Multi-agent orchestration | Spawn-team, planner, subagent router | Yes for complex work |
| Domain-specific | Biology tools, math prover, data pipeline | Yes only if your domain |

The memory management and evaluation clusters should never be removed — they are the infrastructure that makes every other skill get better over time.

***

## Part II: Your Measurement Stack — TF-IDF, UMAP, t-SNE, GPT-Judge as Engineering Primitives

These are not abstract metrics. This section describes exactly what each tool does and where it sits in a real pipeline.

### TF-IDF — The Sparse Baseline That Grounds Everything

TF-IDF (Term Frequency-Inverse Document Frequency) assigns weight to a term in a document as:

\[
\text{tfidf}(t, d) = \text{tf}(t, d) \times \log\frac{N}{df(t)}
\]

where \(\text{tf}(t, d)\) is frequency of term \(t\) in document \(d\), \(N\) is corpus size, and \(df(t)\) is the number of documents containing \(t\).

**Why keep TF-IDF in 2026 when you have embeddings**: TF-IDF is interpretable — when it flags high overlap between two skills, you can read exactly which terms drove the match. Embeddings are powerful but opaque. The 2026 SOTA search architecture is **hybrid retrieval**: BM25 (the production-grade TF-IDF successor) for sparse exact-match recall + dense embedding retrieval for semantic recall, fused via Reciprocal Rank Fusion (RRF). Use TF-IDF/BM25 as the *first filter* (cheap, fast, interpretable), embeddings as the *semantic reranker*.[^5]

**Your concrete use case**: When you add a new skill to your library, run TF-IDF similarity against all existing skills. If similarity >0.7 on key operational terms → explicit redundancy check before adding. This prevents the most common failure mode: two skills with different names but identical function clogging the skill scan.

### Embeddings — The Semantic Layer

Embeddings map text to a continuous geometric space where cosine similarity measures semantic relatedness. The practical 2026 stack:[^6]

| Use Case | Recommended Model | Why |
|---|---|---|
| Skill deduplication | `text-embedding-3-small` | Fast, cheap, 1536-dim, OpenAI |
| Code semantic search | `voyage-code-2` or `nomic-embed-code` | Trained specifically on code tokens |
| Session trace coverage | `text-embedding-3-large` | Higher accuracy for coverage topology |
| Local/offline | `nomic-embed-text` (GGUF, Ollama) | Zero API cost, 768-dim, production-ready |

**Cosine distance** \(d(u,v) = 1 - \frac{u \cdot v}{\|u\|\|v\|}\) is the standard similarity metric in embedding space. For coverage gap detection, maintain a centroid per skill/task cluster and compute the distance from any new task to its nearest centroid. Distance > threshold → task is in an unknown region → confidence gate fires.

### UMAP vs t-SNE — When to Use Which

Both reduce high-dimensional embeddings to 2D/3D for visualization. The choice in 2026 is unambiguous for most engineering uses:[^7][^8]

| Property | t-SNE | UMAP |
|---|---|---|
| What it preserves | Local neighborhood structure | Local + global structure |
| Scalability | Slow (\(O(N^2)\) naive, \(O(N \log N)\) with BH approximation) | Fast (\(O(N)\) via NN-Descent) |
| Stability | Non-deterministic (different runs ≠ same layout) | Deterministic with fixed seed |
| Incremental update | No — full recompute on new data | Yes — `transform()` maps new points into existing layout |
| Inter-cluster distances | Meaningless (explicitly distorted by normalization) | Approximately meaningful |
| Best for | Dense cluster visualization, small corpora (<10K) | Coverage topology, streaming session data, large corpora |

**Critical 2026 warning**: A major arXiv survey confirmed that both are routinely *misused* — particularly treating inter-cluster distances in t-SNE as meaningful, and over-interpreting UMAP's global topology without validating against downstream metrics. The correct practice: use UMAP for navigation (what regions exist?), not measurement (how far apart are they?). All quantitative coverage scoring should use the full embedding-space cosine distances, not 2D projected distances.[^9]

**Your concrete pipeline**:
```python
# Weekly coverage topology update
embeddings = embed_all_sessions(session_store)  # LanceDB retrieval
reducer = umap.UMAP(n_components=2, metric='cosine', random_state=42)
coords_2d = reducer.fit_transform(embeddings)

# Gap detection: find sparse regions
from sklearn.neighbors import KernelDensity
kde = KernelDensity(bandwidth=0.5).fit(coords_2d)
density = np.exp(kde.score_samples(coords_2d))
low_density_sessions = sessions[density < np.percentile(density, 10)]
# These are your coverage gaps → candidates for golden dataset expansion
```

### GPT-Judge / LLM-as-Judge — The 2026 Calibration Science

LLM-as-judge is the dominant evaluation paradigm for outputs that are too complex for deterministic scoring. The April 2026 science has moved significantly beyond "just ask GPT to rate it".[^10][^11][^12]

**The known biases** (EACL 2026, arXiv 2511.21140):[^12][^10]
- **Position bias**: LLMs rate the first response higher regardless of quality — documented across all tested LLM judges and all five programming languages tested
- **Verbosity bias**: Longer responses rated higher independent of correctness
- **Self-enhancement bias**: A model judges its own outputs as better
- **Code-specific bias**: Syntactic formatting (indentation, variable name style) influences code quality scores even for functionally identical code[^12]

**Bias correction (arXiv 2511.21140v3)**: The calibrated estimator uses sensitivity (\(q_1\)) and specificity (\(q_0\)) estimated from a small human-labeled calibration set of ~50 examples. The corrected score:

\[
\hat{\theta} = \frac{\hat{p} - (1 - q_0)}{q_1 - (1 - q_0)}
\]

where \(\hat{p}\) is the raw LLM judge score. This is unbiased even under distribution shift between calibration and test sets.[^10]

**G-Eval (DeepEval's implementation)**: Solves the granularity problem by using log-probability weighting — instead of asking the judge for a single score, it collects token-level probabilities over the score range and computes a probability-weighted mean, dramatically reducing the discretization bias. Use G-Eval (via `deepeval.metrics.GEval`) as your default LLM judge metric for any task where you want fine-grained score separation.[^13]

**The 5% sampling rule**: Running LLM-as-judge on every session is cost-prohibitive and adds latency. The production standard is ~5% random sampling for deep judge evaluation, with deterministic checks (format, PII, constraint) running on every session. When a deterministic check fails, it auto-escalates to full judge evaluation regardless of sampling rate.[^14]

**Your judge stack in order**:
1. **Deterministic** (every session): regex, schema validation, PII check, constraint verification
2. **Heuristic** (every session, fast): BERTScore cosine against golden reference, syntactic correctness
3. **G-Eval / LLM judge** (5% sample + all failures): GPT-4o or Claude Sonnet as judge with calibrated bias correction
4. **Human** (failures + weekly calibration): 20–50 examples per week to update \(q_1, q_0\) estimates

***

## Part III: The Statistics and Math Frontier — Where Markov Chains End

### Where You Are: Markov Decision Processes

A Markov Decision Process (MDP) is defined by \((S, A, P, R, \gamma)\) — state space, action space, transition function, reward function, discount factor. The Markov property states:[^15]

\[
P(s_{t+1} \mid s_t, a_t, s_{t-1}, a_{t-1}, \ldots) = P(s_{t+1} \mid s_t, a_t)
\]

The next state depends only on the current state and action, not on history. This is a *massive* simplification that makes Q-learning, policy gradient, and PPO tractable — but it breaks down for almost every interesting real-world task.

The fact that you know MDPs and W-learning (multi-objective RL via weighted-sum scalarization) puts you at approximately the 2018–2020 frontier. Here is the full map from there to 2026.

### Beyond Markov: The Non-Markovian and Temporal Logic Frontier

The moment a task's reward depends on *history* — what happened three steps ago, whether a condition held for five consecutive steps — the Markov property fails. This is the rule, not the exception, for coding agents: "the test suite passed *only after* the refactor was complete" is a temporally-extended non-Markovian reward.

**Linear Temporal Logic (LTL) for RL objectives**: LTL allows expressing objectives like "eventually reach state A" (\(\Diamond A\)), "always maintain property B" (\(\square B\)), or "A holds until B is achieved" (\(A \mathcal{U} B\)). These are called \(\omega\)-regular specifications — they describe properties of *infinite* sequences of states.[^16][^17]

**The 2024 breakthrough** (NeurIPS 2024, arXiv 2410.12175): The open problem of learning optimal policies for LTL and \(\omega\)-regular objectives was **resolved**. Every RL problem with \(\omega\)-regular objectives can be reduced to a *limit-average reward* problem via finite-memory reward machines, and optimal policies can be learned asymptotically by solving a sequence of discounted problems. This means you can now specify coding agent objectives in formal temporal logic and learn them with standard RL infrastructure.[^18][^19]

**Reward Machines**: The practical mechanism. A Reward Machine (RM) is a finite automaton that tracks the current "memory state" — which temporal conditions have been satisfied, which are pending, which have been violated. The RM's state augments the agent's state, converting a non-Markovian problem back into a Markovian one (over the augmented state space).[^20][^21]

```
Example: "Run linter (L) before every write (W), and test suite (T) must pass after every write"
LTL: □(W → (L came before W ∧ ◇T))
Reward Machine: 
  State 0 (initial) → on L → State 1 (linter ran)
  State 1 → on W → State 2 (write happened after lint, waiting for test)
  State 2 → on T pass → State 0, reward +1
  State 2 → on W (without T) → State 3 (violation), reward -10
```

**Average Reward RL for Omega-Regular (2025, JAIR)**: Extends reward machine RL to continuing (non-episodic) tasks — the natural setting for coding agents that run indefinitely, not in episodes. First model-free RL framework that translates absolute liveness specifications (\(\omega\)-regular) to average-reward objectives with convergence guarantees in unknown communicating MDPs.[^17][^22]

**PlatoLTL (arXiv 2601.22891, Jan 2026)**: LTL-guided multi-task RL that generalizes across unseen *vocabularies* of propositions — meaning a policy trained on one codebase can transfer to another with different function names, because it operates over abstract temporal patterns, not specific tokens.[^23]

**The Non-Markovian Reward Modeling Gap (arXiv 2410.20176)**: Introduces CoDeTr — a Transformer-based non-Markovian reward model that explicitly captures which steps in a sequence are "critical moments" using in-sequence attention. Human feedback naturally emphasizes certain interaction steps (the commit that broke tests, the refactor that finally worked); CoDeTr learns to do the same.[^24][^25]

### Multi-Objective RL Beyond W-Learning

W-learning scalarizes multiple objectives into a weighted sum \(R = \sum_i w_i R_i\). This produces a single point on the Pareto frontier. The 2026 frontier:

**Preference-Controllable RL (ICML 2025)**: A meta-policy \(\pi(s, \mathbf{w})\) conditioned on preference vector \(\mathbf{w}\) that generates the entire Pareto frontier at once. At inference time, you specify your current preference (speed vs. correctness vs. cost) and the policy instantly generates a Pareto-optimal response. Compatible with advanced MOO algorithms (MOEA/D, NSGA-III) previously unseen in MORL. Memory-efficient design for large models.[^26]

**Hypervolume-based MORL**: The correct metric for multi-objective RL is hypervolume of the Pareto front approximation, not any scalarization. Hypervolume measures the volume of the objective space *dominated* by the agent's solutions — a single number capturing the quality of the entire Pareto front. The 2026 multi-objective supply chain paper showed **75% higher hypervolume** and **11× denser Pareto sets** vs. MOEA-based methods using RL with shared experience buffers.[^27]

**The lexicographic objective** (average reward + omega-regular, 2025): Maximize an external average-reward objective *among only those policies that satisfy a given omega-regular specification*. Safety constraints first, performance second — the natural ordering for coding agents where "don't break production" is a hard constraint and "maximize throughput" is the optimization objective.[^17]

### The RL Training Algorithm Landscape in 2026

This is what's actually being used, in order of current production prevalence:[^28][^29][^30]

| Algorithm | What It Does | When to Use | Memory Cost |
|---|---|---|---|
| **GRPO** (DeepSeek, 2024) | Samples \(G\) outputs per prompt; advantage = per-output reward minus group mean; no critic model | RL on verifiable tasks (code execution, math, tool use) | 1× model |
| **DAPO** (2025) | GRPO + clip-higher + dynamic sampling + token-level loss | Long chain-of-thought tasks; avoids entropy collapse | 1× model |
| **RLVR** (DeepSeek-R1) | RL with verifiable rewards — code execution / math checker as reward signal | Emergent reasoning; code correctness | 1× model |
| **DPO** | Direct optimization from preference pairs; no reward model, no RL loop | Alignment from human preferences; style tuning | 1× model, no ref needed |
| **PPO** | Policy gradient with critic model and clipped surrogate loss | Complex nuanced alignment; best on challenging code[^28] | 2× model (policy + critic) |
| **ORPO** (2025) | Merges SFT + preference optimization in one loss using odds ratios | Single-stage fine-tuning pipeline | 1× model, no separate SFT |
| **Training-Free GRPO** (arXiv 2510.08191) | GRPO without parameter updates — uses group-relative semantic advantage as learned token prior | When you cannot fine-tune (API-only models, no GPU) | 0 (inference only) |

**For a solo developer with limited compute**: Training-Free GRPO is the key insight. You can apply GRPO-style learning *without any parameter updates* — the group-relative advantage is distilled into a "learned token prior" injected at inference time. With just a few dozen training samples, it outperforms fine-tuned small models. This means you can implement RL-style improvement on your Claude Code agent without touching model weights.[^31][^32]

**DeepSWE** (42.2% SWE-bench pass@1, 71.0% pass@16) was trained with pure RL (no SFT warmup) on Qwen3-32B using RLVR — demonstrating that verifiable code execution rewards alone are sufficient for state-of-the-art coding capabilities, without human preference labels.[^33]

### Continual Learning in Token Space — The 2026 Frontier That Unifies Everything

This is where your Markov/W-learning foundation directly connects to the cutting edge.

**Letta's formal framing**: The continual learning problem for LLM agents is a sequential task problem over \((C, \theta)\) — context *and* weights. Formally:[^34]

\[
L = \frac{1}{N} \sum_{i=1}^{N} \ell\left((C_i, \theta_i), T_i\right)
\]

where \(C_i\) is the learned context at task \(i\) and \(\theta_i\) are the model weights. The key insight: minimizing \(L\) by updating \(C\) (token-space learning) is orthogonal to and complementary with minimizing by updating \(\theta\) (weight-space learning). In 2026, updating \(\theta\) is expensive and locked in most deployed systems — updating \(C\) is free, interpretable, and model-agnostic.

**Panini (arXiv 2602.15156, Feb 2026)**: The most rigorous 2026 implementation. Instead of storing raw document chunks (standard RAG), Panini structures each new experience into a **Generative Semantic Workspace (GSW)** — a graph \(G = (E, V, Q)\) of entity nodes, verb-phrase/event nodes, and bidirectional QA pairs. At query time, Panini traverses the GSW (not raw chunks), finds reasoning-grounded inference chains, and returns only those chains — **2–30× fewer tokens per answer, 5–7% accuracy improvement over RAG baselines** on six QA benchmarks. The GSW is the operationalization of what the human memory research (SYNAPSE, TSM) describes: structured semantic memory, not flat retrieval.[^35][^36][^37]

**ALMA (arXiv 2602.07755)**: Meta-learning for memory design — learns the *architecture* of memory for each task distribution, not just what to store. This is meta-learning (learning to learn) applied specifically to agent memory structure.[^38]

**Letta Skill Learning**: When agents learn from past trajectories, terminal benchmark performance improves by **+36.8% relative, +15.7% absolute** — the first demonstration that token-space continual learning produces measurable durable improvement on real benchmarks.[^39]

***

## Part IV: The Unified Learning Stack — How It All Fits Together

The following is the complete picture of what to build, what to study, and how the pieces connect:

```
YOUR MEASUREMENT LAYER
────────────────────────────────────────────────────────────────
Session outputs → Embed (voyage-code-2 or nomic-embed-text)
       ↓
Store in LanceDB (with session metadata, reward signals)
       ↓
TF-IDF / BM25 (fast sparse dedup + domain filtering)
Cosine distance (quantitative coverage scoring, confidence tiers)
UMAP → KDE (coverage topology visualization, gap detection)
GPT-judge / G-Eval with bias correction (qualitative scoring, 5% sample)
       ↓
Golden dataset expansion from gaps and failures


YOUR LEARNING LAYER (where Markov chains end)
────────────────────────────────────────────────────────────────
Reward Machines (encode temporal coding constraints as LTL → automaton)
Omega-regular RL (agents that learn multi-step procedural objectives)
Training-Free GRPO (RL-style improvement without parameter updates)
Token-space continual learning (Panini GSW + Letta Skill Learning)
MORL / Pareto frontier (multi-objective: correctness × speed × cost)


YOUR SKILL LAYER
────────────────────────────────────────────────────────────────
Scraped Claude skills (anthropics/skills repo, 87K stars)
Deduplicated by UMAP + HDBSCAN (no redundant skills loading)
Domain-filtered by TF-IDF against domain glossary
Coverage-gap skills (built for uncovered task regions)
Memory consolidation + evaluation skills (always included)
```

### The Study Order — What to Learn First

**Immediately (fills gaps from MDPs and W-learning)**:
- Reward Machines: read Icarte et al. 2018 "Using Reward Machines for High-Level Task Specification and Decomposition in RL" — this is the foundational bridge from MDPs to non-Markovian objectives
- Omega-regular objectives: read Hahn et al. 2019 (University of Twente) — first model-free solution; short and buildable[^16]
- LTL fundamentals: 10-page primer (Stanford CS357) — the logical language above Markov; needed for reward machine specification

**Within 1–2 months**:
- GRPO algorithm (DeepSeek-Math paper, 2024) — the most important new RL algorithm since PPO; directly applicable to coding agent training[^40][^29]
- Panini architecture (arXiv 2602.15156) — the most principled 2026 implementation of token-space learning[^36]
- G-Eval + bias correction (arXiv 2511.21140) — principled LLM judge construction[^10]
- Training-Free GRPO (arXiv 2510.08191) — RL improvement without GPU[^31]

**Within 6 months**:
- Average Reward RL for Omega-Regular (JAIR 2025) — extending to non-episodic agents[^17]
- Preference-Controllable RL (ICML 2025) — multi-objective with meta-policy[^26]
- ALMA meta-learning of memory (arXiv 2602.07755)[^38]
- Oxford CS course "Foundations of Self-Programming Agents 2025–2026" (free online syllabus)[^41]

**Ongoing**:
- Continual Learning in Token Space (Letta blog, updated regularly)[^34]
- WhiteMech group courses on temporal RL, neurosymbolic AI, LTL[^42]
- arXiv cs.AI, cs.LG daily digest — filter for: "reward machine," "omega-regular," "token-space," "non-Markovian," "continual learning"

***

## The Single Most Actionable Insight

The skill-scraping + TF-IDF dedup + UMAP coverage + GPT-judge pipeline you are describing is **not a future project**. It is the exact system that already exists in production at Cursor (12.5% QA improvement), CodeRabbit (millions of daily interactions at ms-scale), and in the published DeepEval + LanceDB architecture. You can build a working version this week.[^43][^44]

The mathematical deepening — reward machines → omega-regular RL → token-space continual learning — is the 6-month track that turns the measurement system into a *learning* system: one that accumulates temporal procedural knowledge across sessions, improves its own memory architecture, and optimizes multi-objective coding tradeoffs without being retrained.

The gap between "I have measurement infrastructure" and "I have a learning system" is precisely the frontier where the most important 2026 research lives.

---

## References

1. [Best Claude Code Skills to Try in 2026 - Firecrawl](https://www.firecrawl.dev/blog/best-claude-code-skills) - Discover the best Claude Code skills that extend what Claude can do without heavy setup. From web sc...

2. [How to Build a Production-Ready Claude Code Skill](https://towardsdatascience.com/how-to-build-a-production-ready-claude-code-skill/) - Before building a Skill, let me walk you through how Skills, MCP, and Subagents are different, so yo...

3. [Top 10 Claude Code Skills Every Builder Should Know in 2026](https://composio.dev/content/top-claude-skills) - Claude Code Skills extends Claude with modular execution capabilities such as tool access, sandboxed...

4. [sqlite-vec-skilld | Skills Marketplace - LobeHub](https://lobehub.com/it/skills/harlan-zw-skilld-sqlite-vec-skilld) - sqlite-vec is a lightweight SQLite extension and developer library that implements SQL-first vector ...

5. [Hybrid Search: RAG for Real-Life Production-Grade Applications](https://www.lancedb.com/blog/hybrid-search-rag-for-real-life-production-grade-applications-e1e727b3965a) - Get about hybrid search: rag for real-life production-grade applications. Get practical steps, examp...

6. [TF-IDF vs. Embeddings: From Keywords to Semantic Search](https://pyimagesearch.com/2026/02/09/tf-idf-vs-embeddings-from-keywords-to-semantic-search/) - Semantic Ranking — TF-IDF ranks documents by keyword overlap, while embedding-based semantic search ...

7. [t-SNE vs UMAP: A Comprehensive Guide for Visualizing High ...](https://www.metwarebio.com/tsne-vs-umap-omics-visualization/) - Compare t-SNE vs UMAP for high-dimensional omics—when to use each, key parameters, pros/cons, and ti...

8. [T-SNE vs UMAP vs SNE: Dimensionality Reduction Essentials](https://arize.com/blog-course/reduction-of-dimensionality-top-techniques/) - There are several prominent ways to visualize the embedding representation of a dataset using dimens...

9. [Stop Misusing t-SNE and UMAP for Visual Analytics - arXiv](https://arxiv.org/html/2506.08725v2) - We identify literature from the visualization, machine learning, and bioinformatics domains that con...

10. [How to Correctly Report LLM-as-a-Judge Evaluations - arXiv](https://arxiv.org/html/2511.21140v3) - Overall, our method provides a simple and practical bias-correction procedure for LLM-as-a-judge eva...

11. [LLM as Judge Guide March 2026 - Openlayer](https://www.openlayer.com/blog/post/llm-as-judge-evaluation-guide) - LLM as judge best practices: reduce bias, improve reliability, validate against human baselines for ...

12. [[PDF] Exploring Biases in LLM Judges for Code Evaluation - ACL Anthology](https://aclanthology.org/2026.findings-eacl.70.pdf) - Our experiments reveal that all tested LLM judges are highly susceptible to these biases across all ...

13. [G-Eval Simply Explained: LLM-as-a-Judge for LLM Evaluation](https://www.confident-ai.com/blog/g-eval-the-definitive-guide) - G-Eval is a framework that uses LLM-as-a-judge with chain-of-thoughts (CoT) to evaluate LLM outputs ...

14. [LLM Evaluation and Testing: How to Build an Eval Pipeline That ...](https://dev.to/pockit_tools/llm-evaluation-and-testing-how-to-build-an-eval-pipeline-that-actually-catches-failures-before-5e3n) - The complete guide to evaluating LLM applications before they break in production. Automated eval fr...

15. [Multi-objective optimization for dynamic logistics scheduling based ...](https://www.nature.com/articles/s41598-025-18309-y) - This paper proposes a novel hierarchical deep reinforcement learning framework for multi-objective o...

16. [[PDF] Omega-Regular Objectives in Model-Free Reinforcement Learning](https://ris.utwente.nl/ws/files/247405321/Hahn2019omega_regular.pdf) - Abstract. We provide the first solution for model-free reinforcement learning of ω-regular objective...

17. [Average Reward Reinforcement Learning for Omega-Regular and ...](https://arxiv.org/html/2505.15693v1) - We present the first model-free RL framework that translates absolute liveness specifications to ave...

18. [Reinforcement Learning with LTL and $ω$-Regular Objectives via ...](https://arxiv.org/abs/2410.12175) - Our main result is that each RL problem for \omega-regular objectives can be reduced to a limit-aver...

19. [Reinforcement Learning with LTL and - ω - -Regular Objectives via ...](https://neurips.cc/virtual/2024/poster/93983) - Linear temporal logic (LTL) and, more generally, ω -regular objectives are alternatives to the tradi...

20. [[PDF] Detecting Hidden Triggers: Mapping Non-Markov Reward ...](https://www.semanticscholar.org/paper/d04e549f3013fc3c84efd6054a9da76959363300) - This paper proposes a framework for mapping non-Markov reward functions into equivalent Markov ones ...

21. [A study in partially observable reinforcement learning - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0004370223001352) - Reward machines (RMs) provide a structured, automata-based representation of a reward function that ...

22. [[PDF] Average Reward Reinforcement Learning for Omega-Regular and ...](https://www.jair.org/index.php/jair/article/download/19233/27280/53416) - We present the first model-free RL framework that translates absolute liveness specifications to ave...

23. [PlatoLTL: Learning to Generalize Across Symbols in LTL ... - arXiv](https://arxiv.org/html/2601.22891v1) - The “hierarchical” approach first converts the LTL formula into an automaton, which is treated as a ...

24. [Non-Markovian Reward Modeling for Reinforcement Learning - arXiv](https://arxiv.org/html/2410.20176v1) - In this paper, we introduce the problem of RL from Composite Delayed Reward (RLCoDe), which generali...

25. [Non-Markovian Reward Modeling for Reinforcement Learning - arXiv](https://arxiv.org/abs/2410.20176) - We present a framework for modeling composite delayed rewards, using a weighted sum of non-Markovian...

26. [Preference Controllable Reinforcement Learning with Advanced ...](https://icml.cc/virtual/2025/poster/46501) - Practical reinforcement learning (RL) usually requires agents to be optimized for multiple potential...

27. [Reinforcement Learning for Multi-Objective Multi-Echelon Supply ...](https://arxiv.org/abs/2507.19788) - This study develops a generalised multi-objective, multi-echelon supply chain optimisation model wit...

28. [DPO vs PPO for LLMs: Key Differences & Use Cases - Clarifai](https://www.clarifai.com/blog/dpo-vs-ppo) - Effectiveness on code tasks: A comprehensive study found that PPO outperformed DPO on challenging co...

29. [Post-Training in 2026: GRPO, DAPO, RLVR & Beyond - LLM Stats](https://llm-stats.com/blog/research/post-training-techniques-2026) - GRPO (Group Relative Policy Optimization) is an RL algorithm that samples multiple responses per pro...

30. [PPO for LLMs: A Guide for Normal People - Deep (Learning) Focus](https://cameronrwolfe.substack.com/p/ppo-llm) - Nearly all RL optimizers used for LLM training (e.g., PPO [1], GRPO, and REINFORCE) are policy gradi...

31. [Training-Free Group Relative Policy Optimization - GoatStack.AI](https://goatstack.ai/articles/2510.08191) - To this end, we propose Training-Free Group Relative Policy Optimization (Training-Free GRPO), a cos...

32. [Training-Free GRPO for LLM Agents | PDF - Scribd](https://www.scribd.com/document/932801339/Cai-%E7%AD%89-2025-Training-Free-Group-Relative-Policy-Optimization) - The document introduces Training-Free Group Relative Policy Optimization (Training-Free GRPO), a nov...

33. [DeepSWE: Training a Fully Open-sourced, State-of-the-Art Coding ...](https://www.together.ai/blog/deepswe) - It achieves an impressive 59% on SWE-Bench-Verified with test-time scaling, reaching SOTA for open-w...

34. [Continual Learning in Token Space - Letta](https://www.letta.com/blog/continual-learning) - The continual learning problem in LLM agents is best viewed through the lens of learning in token sp...

35. [Panini: Continual Learning in Token Space via Structured Memory](https://huggingface.co/papers/2602.15156) - The results show that efficient and accurate structuring of experiences at write time -- as achieved...

36. [Panini: Continual Learning in Token Space via Structured Memory](https://arxiv.org/abs/2602.15156) - Abstract page for arXiv paper 2602.15156: Panini: Continual Learning in Token Space via Structured M...

37. [Continual Learning in Token Space via Structured Memory - Moonlight](https://www.themoonlight.io/en/review/panini-continual-learning-in-token-space-via-structured-memory) - This page provides the most accurate and concise summary worldwide for the paper titled Panini: Cont...

38. [Learning to Continually Learn via Meta-learning Agentic Memory ...](https://arxiv.org/abs/2602.07755) - In this paper, we introduce ALMA (Automated meta-Learning of Memory designs for Agentic systems), a ...

39. [Skill Learning: Bringing Continual Learning to CLI Agents | Letta](https://www.letta.com/blog/skill-learning) - At Letta, we believe that learning in token space is the key to building AI agents that truly improv...

40. [[PDF] GRPO & Deepseek-R1 - Nikolai Rozanov](https://nikolairozanov.com/files/reading_group_03_06_2025.pdf) - NLP Reading Group. June 3rd 2025. “GRPO & Deepseek-R1”. Page 2. Group Relative Policy Optimisation (...

41. [Foundations of Self-Programming Agents: 2025-2026](https://www.cs.ox.ac.uk/teaching/courses/2025-2026/foundagent/) - Overview. This course studies the foundations of how to build autonomous agents that have the abilit...

42. [Courses - WhiteMech](https://whitemech.github.io/courses) - Topics covered will include Deep RL, temporal RL, Restraining Bolts and Reward Machines, deep learni...

43. [How CodeRabbit Leverages LanceDB for AI-Powered Code Reviews](https://www.lancedb.com/blog/case-study-coderabbit) - At the core of CodeRabbit's tech stack lies LanceDB, the vector database that transforms chaotic con...

44. [LLMOps in Production: Another 419 Case Studies of What Actually ...](https://www.zenml.io/blog/llmops-in-production-another-419-case-studies-of-what-actually-works) - Cursor - Cursor enhanced their AI coding agent by developing a custom semantic search system to impr...

