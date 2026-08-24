# 2026 Mathematics & Statistics Frontier — What Hasn't Reached AI Yet and Why

## The Honest Taxonomy

The question being asked is precisely the right one. There is a meaningful and useful distinction between three categories of mathematical work:

1. **Already in LLMs/ML** — gradient descent, backprop, attention, MDP/Q-learning, basic measure theory, Rademacher complexity, basic topology
2. **Being absorbed right now** — optimal transport, PAC-Bayes, TDA/persistent homology, rough path theory, reward machines / LTL-RL
3. **Pure frontier, still theoretical, not yet turned into ML material** — Kakeya / geometric measure theory, geometric Langlands, non-Abelian Hodge theory, p-adic analysis, cohomology of ordinals, quantum interactive oracle proofs

This report covers categories 2 and 3 with scientific precision, why the gap exists, and what a first-time AI engineer with mathematical curiosity should actually study.

***

## Part I: The Math That's Being Absorbed Right Now (Category 2)

These areas have crossed from pure math into research prototypes and will be in production tooling within 2–4 years. They are learnable today and provide real leverage.

### 1. Optimal Transport and Wasserstein Geometry

Optimal Transport (OT) is the theory of how to move one probability distribution into another at minimum cost. The Wasserstein-\(p\) distance between distributions \(\mu\) and \(\nu\) is:

\[
W_p(\mu, \nu) = \left( \inf_{\gamma \in \Pi(\mu,\nu)} \int \|x - y\|^p \, d\gamma(x,y) \right)^{1/p}
\]

where \(\Pi(\mu,\nu)\) is the set of all joint distributions (couplings) with marginals \(\mu\) and \(\nu\).[^1]

**Why it matters for agents**: Wasserstein distance is the *geometrically correct* way to compare two distributions of embeddings — UMAP projections, session trace distributions, golden dataset vs. production distribution. Unlike KL divergence, \(W_p\) is defined even when the two distributions have non-overlapping support (which is the common case when comparing sparse coverage maps).[^1]

**2026 frontier**: Computing exact \(W_2\) is \(O(n^3)\) — unusable at scale. The 2025–2026 research frontier is efficient approximation:[^2]
- **Sliced Wasserstein (SW)**: Project both distributions to random 1D lines, compute 1D OT (which has an analytic solution), average. \(O(n \log n)\) per slice, \(O(Ln \log n)\) total for \(L\) slices.
- **Max-SW**: Choose the worst-case projection direction via Riemannian gradient ascent — tighter bound, more informative.
- **Regression-based estimation** (arXiv 2509.20508, 2026): Train a regression model from \(K\) SW distances (lower + upper bounds as predictors) to the true Wasserstein distance. Reuses computation across repeated distribution comparisons from the same meta-distribution.[^2]
- **Wasserstein Barycenters**: The Fréchet mean in Wasserstein space — the "average" of a set of distributions. Used for multi-agent consensus, averaging multiple session embedding distributions, federated learning over agent fleets.[^3]

**What's not yet AI material**: The full Brenier theorem (polar factorization of maps), the Monge-Ampère PDE connection, the entropic regularization convergence theory (Sinkhorn's algorithm convergence rate under non-Euclidean costs), and the whole program connecting OT to Ricci curvature on discrete graphs (Ollivier-Ricci curvature). All of these have published proofs but no production ML implementations.

### 2. Rough Path Theory and Path Signatures

A **path signature** is a sequence of iterated integrals of a time-series path \(X: [0,T] \to \mathbb{R}^d\). The signature \(S(X)_{s,t}\) at level \(k\) captures all \(k\)-th order interactions between coordinates:

\[
S(X)^{i_1, \ldots, i_k}_{s,t} = \int_{s < t_1 < \cdots < t_k < t} dX^{i_1}_{t_1} \cdots dX^{i_k}_{t_k}
\]

**The universal property** (Chen's theorem): the truncated signature of a path characterizes it up to tree-like equivalence — it is a *complete* invariant of the path's behavior. No Markov assumption is needed. This is the mathematically rigorous generalization of the Markov assumption to arbitrary path-dependent processes.[^4][^5][^6]

**Why this is exactly what you need**: Signatures are the right mathematical framework for any agent whose rewards, states, or actions depend on history — which is every real coding agent. Where reward machines encode history as finite automata, path signatures encode history as a continuous algebraic structure, enabling:
- **Non-Markovian RL**: Signatures as history-dependent state features, replacing augmented state spaces[^7]
- **Kernel methods on paths**: The signature kernel \(k(X,Y) = \langle S(X), S(Y) \rangle\) defines a positive-definite kernel over sequential data — enabling SVMs, GPs, and kernel ridge regression on agent trajectories[^5][^6]
- **Stochastic control with memory** (arXiv 2406.01585): Optimal control policies that are functions of path signatures rather than current state — provably dense in the space of all progressively measurable controls[^7]

**2026 production**: ICML 2025 has a dedicated "Expected Signatures" track. The Edinburgh Futures Institute hosted "Signatures and rough paths: from stochastics, geometry and algebra to machine learning" (May 2025). Terry Lyons' group continues producing scalable implementation tools.[^6][^5]

**What's not yet AI material**: The full convergence theory for multi-parameter signatures (2D time, multiple agents acting simultaneously), the algebraic geometry of signature tensors (rank and border rank), the full rough path approach to stochastic optimal control under model uncertainty.

### 3. Topological Data Analysis and Persistent Homology

**Persistent homology** tracks the birth and death of topological features (connected components, loops, voids) across spatial scales in data. Given a filtered simplicial complex \(K_0 \subset K_1 \subset \cdots \subset K_n\), the persistence diagram records \((b_i, d_i)\) pairs — birth scale and death scale — for each topological feature. Features that persist long (large \(d_i - b_i\)) are "signal"; those that die quickly are "noise".[^8][^9]

**2026 applications in ML**:
- **Agent trace analysis**: Build a Vietoris-Rips complex on the UMAP embedding of session traces. Persistent loops in the H1 homology group indicate "circular" failure modes — agents cycling through the same incorrect pattern without escaping[^8]
- **Skill coverage topology**: Persistent H0 components = disconnected coverage regions. Large H0 persistence = skills that cover fundamentally different domains with no semantic bridge[^10]
- **Neural network training dynamics**: TDA can detect phase transitions in loss landscapes (topology of sublevel sets changes sharply at grokking)[^11]
- **TopoTS for time series** (94% accuracy on ECG arrhythmia classification vs. LSTM, outperforms on low SNR)[^8]
- **Topological deep learning** (Guowei Wei, MPI): TDA generalized beyond persistent homology to combinatorial spectral theory and geometric topology on graphs — handling higher-order interactions that GNNs miss[^12]

**Frontier not yet applied**: Asymmetrically weighted Dowker persistence for directed graphs (arXiv 2601.04559, Jan 2026) — TDA for asymmetric distance spaces, directly applicable to directed agent communication graphs. Cohomological approaches to ordinals (Winter School 2026) — still pure mathematics. Spectral diagnostics for sheaves on cell complexes (arXiv 2601.19056) — too abstract for current application.[^13][^14]

### 4. PAC-Bayes and the 2026 Statistical Learning Theory Frontier

The standard PAC bound says that for a hypothesis class \(\mathcal{H}\), with probability \(1-\delta\), all \(h \in \mathcal{H}\) satisfy:

\[
R[h] \leq \hat{R}_S[h] + \sqrt{\frac{\ln|\mathcal{H}| + \ln(1/\delta)}{2n}}
\]

This scales with \(\ln|\mathcal{H}|\) — unusable for infinite hypothesis classes like neural networks. **PAC-Bayes** replaces the worst-case bound with a posterior-averaged bound[^15]:

\[
\mathbb{E}_{h \sim Q}[R(h)] \leq \mathbb{E}_{h \sim Q}[\hat{R}_S(h)] + \sqrt{\frac{D_{KL}(Q \| P) + \ln(2\sqrt{n}/\delta)}{2n}}
\]

The complexity term is now the KL divergence between prior \(P\) (pre-training knowledge) and posterior \(Q\) (after training) — not the hypothesis class size. This is why LLMs generalize despite having billions of parameters.

**The 2025–2026 frontier**:
- **Disintegrated PAC-Bayes** (arXiv 2209.02525v4, Feb 2025): Continuous-time PAC-Bayes bounds for gradient descent flows — not just endpoints, but the entire optimization trajectory. Unifies the theory of gradient descent generalization[^16]
- **Reconciling grokking with PAC-Bayes** (ScienceDirect, 2026): Using PAC-Bayes lens to explain why models grokked — late-stage generalization corresponds to a phase transition in the KL term[^11]
- **Disintegration bounds**: PAC-Bayes for individual samples (per-example bounds), not just expectations over the data distribution — enables pointwise confidence guarantees[^17]

**Directly applicable to your stack**: PAC-Bayes bounds give theoretical grounding for your confidence tier thresholds (0.90/0.70 cutoffs). Instead of empirically chosen thresholds, you can derive them from finite-sample PAC-Bayes bounds over your golden dataset — giving guarantees like "with probability 0.95, the agent's error rate on held-out tasks is below \(\epsilon\)."

**What's not yet applied**: The full disintegrated trajectory bounds for transformer training dynamics, PAC-Bayes for multi-agent systems with correlated training, and the connection between PAC-Bayes and information-theoretic generalization (mutual information bounds).

***

## Part II: The Pure Frontier — Too General/Theoretical for AI Yet (Category 3)

These are results from 2024–2026 that are mathematically significant but have no current ML application. Understanding *why* they don't yet connect is as important as knowing they exist — because some of them eventually will.

### 5. The Kakeya Conjecture — Geometric Measure Theory

**The result**: Hong Wang and Joshua Zahl proved the 3-dimensional Kakeya conjecture on February 24, 2025. Proof posted arXiv: "Volume estimates for unions of convex sets, and the Kakeya set conjecture in three dimensions."[^18][^19][^20]

**What it says**: A Kakeya set is a compact subset of \(\mathbb{R}^3\) containing a unit line segment in every direction. The conjecture, open since Besicovitch (1919), states that every Kakeya set in \(\mathbb{R}^3\) must have Hausdorff dimension 3 — i.e., full dimension. Wang and Zahl proved this.[^18]

**Why it matters mathematically**: The Kakeya conjecture is deeply connected to fundamental open problems in harmonic analysis, including the Bochner-Riesz conjecture, restriction estimates for the Fourier transform, Strichartz estimates in PDE, and bounds on oscillatory integrals. These results have downstream implications for signal processing, analysis of wave equations, and the theoretical foundations of sampling theory (Nyquist-Shannon sampling theorem generalizations).[^21]

**Why it's not yet AI material**: The proof technique uses polynomial methods from algebraic geometry combined with polynomial ham-sandwich theorems and iterative geometric inequalities. The gap to any ML application runs through harmonic analysis → sampling theory → signal processing → feature extraction. That pipeline exists conceptually but requires significant mathematical engineering to become a concrete ML tool. The Epoch AI analyst's comment is apt: "about at the level of a mid-tier IMO problem" is where AI can contribute today — Kakeya is still far above that.[^22]

**What could eventually matter**: Better theoretical understanding of why neural networks can approximate functions in high dimensions (the curse of dimensionality, sparse sampling, Nyquist-style bounds for function approximation). The Kakeya result tightens these fundamental limits in ways that might eventually sharpen our understanding of when neural network approximation is and isn't possible.

### 6. The Geometric Langlands Program — Grand Unified Theory of Mathematics

**The result**: Dennis Gaitsgory and collaborators published a proof of the geometric Langlands conjecture in 2024, a ~1000-page work released in five coordinated papers. This is considered the most significant mathematical achievement of the decade.[^23][^24]

**What it says** (as simply as possible): The Langlands program predicts a deep equivalence between two apparently unrelated mathematical worlds:
- **Automorphic forms**: functions with enormous hidden symmetries (Hecke symmetries), studied in analytic number theory
- **Galois representations**: abstract symmetries of solutions to polynomial equations

The geometric Langlands conjecture is the "function field" analogue, replacing number fields with algebraic curves and connecting automorphic sheaves to local systems via a derived equivalence of categories. The proof deploys:
- Non-abelian Hodge theory
- Perverse sheaves and D-modules
- Infinity-categories (homotopy-coherent algebra)
- Quantum group theory
- Gauge theory (inspired by physics)[^25][^24][^23]

**Why it's not AI material**: The mathematical language required — derived categories, infinity-groupoids, perverse sheaves — has no current computational implementation suitable for ML. The closest connection is to the *Langlands-inspired neural architecture* speculation (some researchers have noted that transformer attention heads may be computing something analogous to Hecke operators), but this is pure speculation with no rigorous development. The Fields Medal implications (Jacob Tsimerman: André-Oort conjecture; Jack Thorne: arithmetic Langlands) operate at a level of abstraction that has no near-term applied consequence.[^26][^27]

**The 5–10 year window for partial application**: The geometric Langlands program heavily uses the theory of perverse sheaves, which has an algorithmic implementation in certain special cases. If someone builds a formal verification bridge (Lean 4 + Mathlib) to some of the more constructive parts of the Langlands correspondence, and if symbolic AI improves enough to handle the combinatorial searches, there could be automated conjectural generation in arithmetic geometry within a decade. The Clay Mathematics Institute Langlands symposium (Sheffield, July 2026) is monitoring this.[^23]

### 7. Rough Paths and Non-Markovian Stochastic Control (The Bridge Zone)

**Why this is the single most important Category 3 topic for an AI engineer**: Path signatures (Category 2 above) are the engineering tool. Rough path theory is the *mathematics underneath* them, and it contains results that haven't made it into ML yet:

- **Stochastic invariance in infinite dimensions** (Abi Jaber + Tappe): conditions for stochastic processes to stay in convex domains with non-Lipschitz coefficients — important for constrained agent action spaces[^28]
- **Volterra processes and signature methods** (Abi Jaber et al.): Affine Volterra processes (generalization of Heston model) are efficiently simulatable. Their signatures provide finite-dimensional approximations to infinite-dimensional path-dependent state spaces[^28]
- **Rough differential equations under measure uncertainty**: Extension of rough path theory to situations where the driving noise itself has uncertainty — the analogue of robust RL but with full path-dependent memory

**The key insight**: Rough path theory provides the mathematical foundation for replacing Markov state spaces with path-dependent state spaces *without losing the compactness and tractability properties* that make MDPs useful. This is the deep reason why signatures work — the rough path lift gives you a compact, algebraically structured representation of infinite-dimensional history.

### 8. Quantum Information Theory — The Long Game

**Thomas Vidick's group** (now at Weizmann) is producing results in quantum interactive oracle proofs (qIOPs) — quantum analogues of classical IOP protocols. The construction shows QMA-complete problems can be verified by quantum verifiers reading only a constant number of qubits, conditional on shared EPR pairs.[^29]

**Why it's not AI material now but you should track it**: Quantum advantage for AI inference is contested — current quantum hardware cannot run useful AI workloads. But as quantum hardware matures (2028–2032), the intersection of quantum speedups for combinatorial search (relevant for formal verification, SAT solving) and quantum advantage for linear algebra (HHL algorithm for solving linear systems) will directly affect the mathematics of LLM inference. The foundations being built now by Vidick, Mahadev, and the quantum PCP program are what that eventual application will be built on.

***

## Part III: The Principled Study Order — From Markov Chains to the Frontier

Given your background (MDPs, Markov chains, W-learning), here is the mathematically motivated study order that connects your existing knowledge to the 2026 frontier with minimal gaps:

### Phase 1 — Closing the Stochastic Processes Gap (2–3 months)

**The critical missing piece**: You understand discrete-time MDPs. The frontier assumes familiarity with continuous-time stochastic processes, Itô calculus, and measure-theoretic probability.

**What to study**:
1. **Measure-theoretic probability** (Billingsley's *Probability and Measure*, first 5 chapters, or Durrett's *Probability: Theory and Examples*) — the rigorous language underlying all modern statistics and ML theory
2. **Stochastic calculus basics** (Øksendal's *Stochastic Differential Equations*, Chapters 1–5) — Itô integral, SDEs, Brownian motion as the canonical continuous-time Markov process
3. **The Kolmogorov equations** — the PDE characterization of SDEs; the bridge between probability theory and PDEs

**Why now**: Rough path signatures, Wasserstein distances, and diffusion models (score-based generative models) all assume this foundation. Without it, you can use these tools but cannot understand, debug, or extend them.

### Phase 2 — Optimal Transport and PAC-Bayes (2–3 months)

1. **Villani's *Optimal Transport: Old and New*** (Part I + Chapter 7 on Wasserstein spaces) — mathematically rigorous, beautifully written
2. **Computational OT** (Peyré and Cuturi, *Computational Optimal Transport*, free PDF) — bridges theory to algorithms; Python implementations throughout
3. **PAC-Bayes tutorial** (Guedj 2019, "A primer on PAC-Bayesian Learning") — direct bridge from what you know (generalization bounds) to the 2026 frontier

**Immediate practical output**: Replace your UMAP + cosine-distance coverage scoring with Sliced Wasserstein distances. This gives you a theoretically grounded, geometrically correct measure of how far your production distribution has drifted from your golden dataset distribution — with formal generalization guarantees via PAC-Bayes bounds.

### Phase 3 — Path Signatures (2–3 months)

1. **Terry Lyons + Ni Hao, "A Primer on the Signature Method in Machine Learning"** (2016, arXiv:1603.03788) — accessible, computationally oriented
2. **`signatory` Python library** (Kidger) — PyTorch-compatible, GPU-accelerated signature computation
3. **Rough path theory** (Friz and Victoir, *Multidimensional Stochastic Processes as Rough Paths*, Chapters 1–4) — for the mathematically rigorous version

**Immediate practical output**: Replace flat session embedding vectors with signature-based session representations. Signatures encode the *order* and *interaction* between events in a session, not just their presence — making them fundamentally better features for detecting temporal coding patterns (e.g., "linted before commit" vs. "committed before lint").

### Phase 4 — Topological Data Analysis (3–4 months)

1. **Edelsbrunner and Harer, *Computational Topology*** (Chapters 1–7) — the standard reference, mathematically accessible
2. **`giotto-tda` Python library** — sklearn-compatible TDA pipeline; persistent homology in 5 lines of code
3. **Carlsson's "Topology and Data" (Bulletin of AMS, 2009)** — the conceptual founding document; still the best intuition-builder
4. **TopoOpt paper** — 30% training time reduction via persistence-guided topology adjustment; directly applicable to agent subgraph optimization[^8]

**Immediate practical output**: Build a TDA layer on top of your UMAP coverage map. Persistent H1 features (loops) in the session trace topology indicate systematic circular failure modes; H0 features (connected components) measure coverage fragmentation between skill domains.

***

## Part IV: The Honest Gap Assessment for an AI Engineer

The mathematician's question — "which 2026 mathematical results are genuinely too theoretical for AI yet?" — has a precise answer:

| Result | Domain | Distance to ML Application | Why Not Yet |
|---|---|---|---|
| Kakeya conjecture proof (Wang-Zahl 2025) | Geometric measure theory | 5–10 years | Requires harmonic analysis → sampling theory → ML pipeline |
| Geometric Langlands (Gaitsgory et al. 2024) | Number theory / algebraic geometry | 10–20 years | Mathematical language (infinity-categories, derived sheaves) has no computational realization |
| p-adic Langlands (Emerton 2026) | Number theory | 15–30 years | p-adic analysis has no current ML foothold |
| Cohomology of ordinals (Bergfalk 2026) | Set theory / algebraic topology | Unknown | Operates in transfinite combinatorics with no data analogue |
| Quantum IOPs (Vidick 2026) | Quantum information theory | 5–10 years (conditional on hardware) | Quantum hardware bottleneck; theory is ready |
| Non-abelian Hodge theory | Differential geometry | 5–10 years | Used in Langlands; could inform geometric deep learning eventually |
| Universally measurable sets (Larson 2026) | Descriptive set theory | Unknown | Theoretical foundations of measure theory; no direct algorithmic consequence yet identified |

**The deep reason for the gap**: Most pure mathematics in 2026 operates in the language of *category theory*, *derived algebraic geometry*, and *infinity-categories* — mathematical structures that describe relationships between structures, relationships between those relationships, etc. Machine learning currently operates mostly in the language of *numerical optimization over function spaces*. The translation layer between these languages is the main bottleneck. Lean 4 and formalized mathematics are building that bridge — but it is a 10-year project.[^30]

**The actionable framing**: The math in Category 2 (optimal transport, rough paths, TDA, PAC-Bayes) is learnable from good textbooks, has Python implementations, and will give you genuine theoretical leverage in the next 2–3 years. The Category 3 results are for *reading and tracking* — they tell you where the deep foundations are being laid, and occasionally one of them will suddenly connect in a way that creates a 10-year opportunity for whoever was paying attention.

Daniel Litt's bet (75% probability AI cannot produce a publishable *Annals of Mathematics* paper by 2030) captures exactly this gap: AI is very capable in the areas where mathematical structure is *already* computationally realized. In the areas where the deepest 2026 mathematics lives — Langlands, Kakeya, set theory, quantum IOPs — the gap is not one of model capability but of *representational infrastructure*. That infrastructure is what Lean 4, proof assistants, and neurosymbolic AI are slowly building.[^22]

---

## References

1. [Optimal Transport: Statistics, Numerics, and Partial Differential ...](https://www.wias-berlin.de/research/rts/OptimTrans/index.jsp?lang=1) - Motivated by recent advances with computational optimal transport for estimating Wasserstein distanc...

2. [Fast Estimation of Wasserstein Distances via Regression on Sliced ...](https://arxiv.org/html/2509.20508v2) - Fundamentally, the Wasserstein distance measures the minimum cost required to "transport" mass from ...

3. [Track: Optimal Transport - ICML 2026](https://icml.cc/virtual/2021/session/11970) - In this work, we present a novel scalable algorithm to approximate the Wasserstein Barycenters aimin...

4. [Scalable Machine Learning Algorithms using Path Signatures - arXiv](https://arxiv.org/abs/2506.17634) - Rooted in rough path theory, path signatures are invariant to reparameterization and well-suited for...

5. [Signatures and rough paths: from stochastics, geometry and algebra ...](https://icms.ac.uk/activities/workshop/sgatoml/) - The aim of this workshop was to discuss stochastic, geometric, and algebraic approaches to signature...

6. [Learning with Expected Signatures: Theory and Applications](https://icml.cc/virtual/2025/poster/43548) - In any case, for a wide range of stochastic processes there exist canonical lifts that satisfy our d...

7. [[PDF] Stochastic Control with Signatures - arXiv](https://arxiv.org/pdf/2406.01585.pdf) - We rigorously prove that these controls are dense in the class of progressively measurable controls ...

8. [TDA in Machine Learning: Methods, Applications and Future ...](https://www.ijert.org/tda-in-machine-learning-methods-applications-and-future-directions) - A key component of topological data analysis (TDA) is persistent homology, which offers a multiscale...

9. [[PDF] Persistent homology applications in data analysis * - Unipd](https://www.math.unipd.it/~demarchi/papers/Smart2025.pdf) - Homology, and in particular persistent homology, is a tool in Topological Data. Analysis (TDA) for e...

10. [TopAI: Topological Data Analysis for Machine Learning and AI - ANR](https://anr.fr/Project-ANR-19-CHIA-0001) - TopAI is a project that aims at developing a world-leading research activity on topological and geom...

11. [Reconciling grokking with statistical learning theory through the lens ...](https://www.sciencedirect.com/science/article/pii/S0925231226002237) - When dealing with randomized models, PAC-Bayes theory offers a powerful analytical tool [103]. In sc...

12. [Topological data analysis and topological deep learning beyond ...](https://www.mis.mpg.de/events/event/topological-data-analysis-and-topological-deep-learning-beyond-persistent-homology) - TDL utilizes topological data analysis (TDA), which is originally rooted in persistent homology, an ...

13. [Algebraic Topology Mar 2026 - arXiv](https://arxiv.org/list/math.AT/current) - Algebraic Topology. Authors and titles for March 2026. Total of 113 entries : 1-50 51-100 101-113. S...

14. [List of announced lectures, WS 2026](https://www.winterschool.eu/2026/program) - Interactions between Ramsey Theory, functional analysis, algebra and topology have a long history. T...

15. [[PDF] IFT 6085 - Lecture 8 Statistical learning theory: PAC-Bayes bounds](http://mitliagkas.github.io/ift6085-2020/ift-6085-lecture-8-notes.pdf) - In this lecture we continue our crash course on Statistical Learning Theory by introducing new conce...

16. [[PDF] arXiv:2209.02525v4 [stat.ML] 11 Feb 2025](https://arxiv.org/pdf/2209.02525.pdf) - We establish disintegrated PAC-Bayesian generalisation bounds for models trained with gradient desce...

17. [[PDF] Generalization bounds 1 Setup 2 PAC-Bayes - CS - Huji](https://www.cs.huji.ac.il/~shais/Lecture8.pdf) - In the next lecture we will discuss the “General Learning. Setting” (introduced by Vapnik), which in...

18. [Understanding the Kakeya Conjecture: A 2025 Breakthrough](https://vinculum223466653.wordpress.com/2025/05/23/understanding-the-kakeya-conjecture-a-2025-breakthrough/) - In early 2025, mathematicians Hong Wang and Joshua Zahl proved the Kakeya conjecture in 3D, solving ...

19. [Introduction to the proof of the Kakeya conjecture - Semantic Scholar](https://www.semanticscholar.org/paper/Introduction-to-the-proof-of-the-Kakeya-conjecture-Guth/98db965ea0544daeee82b9fc17d904a71279ee2c) - Recently, Hong Wang and Joshua Zahl announced a proof of the 3-dimensional Kakeya conjecture. This i...

20. [the three-dimensional Kakeya set conjecture has been proved](https://aperiodical.com/activitypub/account/mathnews/notes/2c7b5ccc-0c0c-474b-b868-90bf2cfb7eff) - Aperiodical Maths News @mathnews@aperiodical.com March 4, 2025, 7:35 a.m.. 4 likes. 2 boosts. the th...

21. [A Survey of the Kakeya conjecture, 2000-2025 - Semantic Scholar](https://www.semanticscholar.org/paper/A-Survey-of-the-Kakeya-conjecture,-2000-2025-Zahl/bd070dc00005fc31be67707702a99e85147bc7e8) - 2025. Recently, Hong Wang and Joshua Zahl announced a proof of the 3-dimensional Kakeya conjecture. ...

22. [AI math capabilities could be jagged for a long time – Daniel Litt](https://epochai.substack.com/p/ai-math-capabilities-could-be-jagged) - Topics we cover: the hardest problems models can solve today, whether there is convincing evidence t...

23. [The Langlands Programme: Recent Trends, New Developments ...](https://www.claymath.org/events/the-langlands-programme-recent-trends-new-developments-and-applications/) - The Langlands programme has become a cornerstone of modern number theory, and predicts the existence...

24. [The Breakthrough Proof Bringing Mathematics Closer to a Grand ...](https://www.ias.edu/news/breakthrough-proof-bringing-mathematics-closer-grand-unified-theory) - The Langlands program remains a nexus of ideas, promising to shape mathematics—and its connections t...

25. [Developments in the p-Adic Langlands Program (March 5, 2026)](https://www.youtube.com/watch?v=1yELaO2NSBc) - Matthew Emerton will give an overview of some recent developments in the p-adic Langlands program. A...

26. [Top Candidates for Fields Medal (2026) : r/math - Reddit](https://www.reddit.com/r/math/comments/1m2v188/top_candidates_for_fields_medal_2026/) - Top Candidates for Fields Medal (2026) ; Top Candidates ; Hong Wang - proved Kakeya set Conjecture. ...

27. [Who will win the Fields Medal in 2026? | Live Odds Comparison](https://www.predictionhunt.com/odds/who-will-win-the-fields-medal-in-2026) - Hong Wang leads the “Who will win the Fields Medal in 2026” event at 79.3% implied probability. Othe...

28. [Eduardo Abi Jaber](https://sites.google.com/view/abijabereduardo/) - Rough Path Interest Group, Online, February 5, 2025. Some path-dependent processes from signatures. ...

29. [Publications | Thomas Vidick - Weizmann Institute of Science](https://www.weizmann.ac.il/math/vidick/publications) - This page includes a list of publications for the research carried out in Prof. Thomas Vidick.

30. [When AI Writes the World's Software, Who Verifies It?](https://leodemoura.github.io/blog/2026-2-28-when-ai-writes-the-worlds-software-who-verifies-it/) - Microsoft's CTO predicts that 95% of all code will be AI-generated by 2030. ... Lean that combines m...

