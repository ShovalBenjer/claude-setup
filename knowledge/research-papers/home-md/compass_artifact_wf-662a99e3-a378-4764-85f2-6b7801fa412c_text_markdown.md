# Three pillars for an agentic coding future: visualization, learning, and autonomy

**A technically sophisticated developer preparing for TAU's MSc Statistics can build a differentiated edge by combining three systems: a real-time morphic 3D agent avatar ("Anton"), context-aware math learning woven into coding sessions, and a next-gen agentic architecture with semantic self-awareness.** Each of these projects addresses a distinct need — presence, preparation, and production — and together they form a coherent platform for autonomous coding work. What follows is a dense technical guide across all three domains, with specific libraries, papers, repos, and implementation patterns.

---

## Topic 1: Anton — the metallic sand agent that thinks in particles

The strongest visual reference for a "metallic sand being" isn't any single film — it's a composite. The **T-1000 from Terminator 2** established the liquid metal reformation language, where ILM created four distinct CGI states from amorphous blob to full chrome replica. James Cameron chose mercury specifically because "it looks like a digitally-created thing even in real life." The **nano swarm from Moonfall (2022)** is more directly relevant: Framestore built a "shapeless, ever-in-flux, strangely mechanical swarm of particles" using Maya animation finalized in Houdini — essentially what Anton needs to be. Spider-Man 3's Sandman required six months of R&D with custom SPH fluid simulation engines as Houdini plugins. For abstract/art-installation aesthetics, **Refik Anadol's "Unsupervised" at MoMA** — AI-trained continuously morphing abstract 3D forms — and **Ian Cheng's "BOB (Bag of Beliefs)"** — an AI creature that grows based on interaction — are the strongest conceptual references for a "living" AI visualization.

### WebGPU compute shaders are the rendering backbone

The technical foundation for Anton should be **WebGPU compute shaders via Three.js TSL (Three.js Shading Language)**. The performance delta is decisive: a CPU-driven WebGL particle system managing 10,000 particles at ~30ms/frame becomes **100,000 particles in under 2ms** on WebGPU compute — a 150× improvement. Maxime Heckel's 2025 "Field Guide to TSL and WebGPU" provides a comprehensive tutorial on building particle systems with compute pipelines. The Three.js Roadmap demonstrates 1 million particles with physics and interactivity using this approach. Apple's WWDC25 officially showcased WebGPU compute shaders for particle systems, confirming this as the industry-endorsed path.

The recommended rendering pipeline is a **hybrid approach**: SDF raymarching for the base blobby metallic form (using the `three-raymarcher` library, which supports smooth union/subtraction/intersection with metalness/roughness controls and R3F integration) layered with **instanced particle mesh** for the granular "sand" texture (small metallic spheres via `InstancedMesh`). Particles interpolate between a dispersed cloud state and the SDF surface based on session state. The Codrops June 2025 tutorial "Interactive Droplet-like Metaballs with Three.js and GLSL" demonstrates exactly this — SDF + smoothMin for seamless metaball blending with surface noise for organic appearance.

For fluid dynamics, **WebGPU-Ocean** by matsuoka-601 achieves ~100K particles on integrated GPUs using MLS-MPM (Material Point Method), while **jeantimex/fluid** offers SPH + PIC/FLIP simulation with volumetric raymarching rendering. Both are open-source WebGPU implementations ready for adaptation.

### Session state maps cleanly to particle physics

The state-to-visualization mapping should drive density, turbulence, color temperature, and formation tightness simultaneously:

| Claude API Event | Particle Behavior | Visual Signature |
|---|---|---|
| **Idle** | Loose orbital drift, breathing oscillation, low cohesion | Cool blue-silver, gentle turbulence, ambient glow |
| **Thinking** | Inward acceleration, internal churning, pulsing rhythm | Silver → gold hints, tighter formation, bloom pulses |
| **Tool use** | Directed tendrils streaming outward then retracting | Electric blue accents, high emission on extensions |
| **Success** | Crystalline snap — particles lock into sharp geometry | White/gold flash → warm silver, maximum density |
| **Error** | Form fractures, scatters, slowly heals with visible seams | Red/orange through cracks, roughness spike, sheen loss |

The closest existing implementation is the **ElevenLabs Orb Component** — an open-source R3F component with `AgentState` type (`null | "thinking" | "listening" | "talking"`) that uses simplex noise for organic morphing. It's a smooth orb, not a particle being, but its state-management architecture is directly reusable. The **Vapi Orb** (vapiblocks.com) similarly morphs based on session state and audio volume.

### The recommended tech stack

The full stack: **React Three Fiber v9** with `WebGPURenderer`, **WebGPU compute shaders via TSL** for 50K–200K metallic particles, `@react-three/postprocessing` with Bloom and ChromaticAberration, `wawa-vfx` or `three.quarks` for VFX particle emission, and `simplex-noise` for organic displacement. Target **60fps on RTX 3060 / M1 Mac** with WebGL fallback. Key repos to study: `danielesteban/three-raymarcher` for SDF operations, `Alchemist0823/three.quarks` for high-performance particle VFX, `sampstrong/r3f-particle-system` for declarative R3F particles with force systems, and the Codrops liquid raymarching TSL tutorial for the blobby metallic surface layer.

---

## Topic 2: Math learning that surfaces where your code lives

### What TAU actually requires — and what developers typically lack

TAU's Department of Statistics and Operations Research (School of Mathematical Sciences, Sackler Faculty of Exact Sciences) offers four MSc tracks: **Statistics and Data Science**, **Statistics and Probability**, **Biostatistics**, and **Operations Research**. Each requires 30 hours of coursework plus a thesis. Applications typically run February through May, requiring a Psychometric Entrance Exam (Israel's GRE equivalent) and English/Hebrew proficiency. Detailed prerequisites are primarily available in Hebrew at exact-sciences.tau.ac.il — contacting the Student Secretariat (03-6409177, 307 Kaplun Bldg) is essential for specifics.

The core prerequisite stack spans **linear algebra** (abstract vector spaces, not just computation), **multivariable calculus**, **probability theory** (measure-theoretic for the Probability track), **mathematical statistics** (MLEs, hypothesis testing, sufficient statistics), and **real analysis** (epsilon-delta proofs, convergence, compactness). The Statistics & Probability track demands significantly more theoretical depth than Data Science. Developers applying to statistics MSc programs consistently face five gaps: **formal proof-writing**, **real analysis**, **measure-theoretic probability** (sigma-algebras, Lebesgue integration), **rigorous linear algebra** beyond matrix operations, and **mathematical statistics theory** (Rao-Blackwell, Neyman-Pearson lemma).

### Context-aware math: matching code patterns to theory

The most promising implementation approach uses pattern-matching on code constructs to surface the underlying mathematics. When Claude writes `gradient_descent()`, the system surfaces optimization theory → convex analysis → KKT conditions. When it calls `sklearn.decomposition.PCA`, it triggers eigenvalue decomposition → spectral theory → SVD. This maps cleanly to the "Just-in-Time Learning" paradigm, which originated in Toyota's lean manufacturing and was adapted to education by Gloria Gery's Electronic Performance Support Systems in the 1990s. ATD research confirms JIT improves retention by delivering knowledge "inside the workflow."

No existing commercial system surfaces math learning during coding sessions — this would be a novel implementation. The closest analogues are **Cloverleaf** (context-aware coaching synced to calendar and activity), **Udemy Business AI Connectors** (MCP-based learning surfaced within workflow tools), and Anthropic's **Model Context Protocol** enabling AI systems to connect to tools in real-time. The technical architecture should use three delivery modes:

- **Mode 1 — Micro-lessons (2–5 min)**: Triggered by code-pattern detection. Brief explanation, connection to statistics, one worked example. Source: 3Blue1Brown clips → custom Claude explanations → Brilliant-style interactive problems.
- **Mode 2 — Concept of the Day**: At session start. Selected by FSRS (Free Spaced Repetition Scheduler, now in Anki v23.10+, using ML for scheduling). Format: definition → intuition → code connection → practice problem.
- **Mode 3 — Problem Sets**: End-of-session or scheduled review. 3–5 problems mixing new concepts with spaced repetition review from textbook exercises.

### The resource stack, prioritized for speed

The study plan should follow this priority order, with estimated timelines:

1. **Linear Algebra** (4–6 weeks): MIT 18.06 (Gilbert Strang) + 3Blue1Brown's Essence of Linear Algebra (16 videos with new interactive exercises). Strang's course is universally cited as the single best resource for ML-relevant linear algebra.
2. **Calculus review** (2–3 weeks): Paul's Math Notes (tutorial.math.lamar.edu) for gap-filling + 3Blue1Brown's Essence of Calculus.
3. **Probability Theory** (6–8 weeks): MIT 6.041 (Tsitsiklis) + Casella-Berger chapters 1–4.
4. **Real Analysis** (8–12 weeks): Rudin's "Principles of Mathematical Analysis" chapters 1–7 or MIT 18.100. Essential for theoretical tracks.
5. **Statistical Inference** (8–10 weeks): Casella-Berger full text — the standard graduate reference.
6. **Measure-Theoretic Probability** (8–12 weeks, if targeting Statistics & Probability): Billingsley's "Probability and Measure."

For deep learning math gaps specifically, the most common deficits are **matrix calculus** (Jacobians, Hessians, derivatives of matrix expressions), the **multivariate chain rule at depth** (for backpropagation), **information theory** (KL divergence, entropy, cross-entropy — ubiquitous in VAEs and knowledge distillation), and **measure-theoretic probability** for rigorous understanding of convergence. Coursera's **Mathematics for Machine Learning** (Imperial College London) and DeepLearning.AI's **Mathematics for ML and Data Science** (Luis Serrano) are the best structured online paths for these gaps.

### LLMs as Socratic tutors — the research is promising but not magic

The **SocraticLLM** paper (CIKM 2024) trained on 8,935 math problems with structured conversations using knowledge graphs for logical progression. It achieved an effectiveness score of **7.19** versus ChatGPT's 6.40 and GPT-4's 6.83. The **MathTutorBench** benchmark (ETH Zurich, 2025) evaluates seven tutoring tasks including Socratic questioning and mistake location. However, the **GuideEval** benchmark found that existing LLMs "frequently fail to provide effective adaptive scaffolding when learners exhibit confusion" — meaning Claude works well for guided discovery but shouldn't be the sole assessment tool. For MSc preparation, LLM tutoring should be supplemented with rigorous textbook problems. Microsoft Learn paths exist for applied ML but lack dedicated statistics, linear algebra, or real analysis courses — they're best used as application-layer supplements showing where math meets production systems.

---

## Topic 3: Agentic architecture where agents know what they don't know

### The 2026 autonomous coding landscape has a trust problem

**Claude Code** became the most-used AI coding tool by early 2026, running an agentic loop of plan → code → test → debug → iterate with full filesystem access and a 1M token context window. A March 2026 leak of its 512K-line TypeScript codebase revealed **KAIROS** — an unreleased autonomous daemon mode with persistent background monitoring via periodic `<tick>` prompts, append-only daily logs, and GitHub webhook subscriptions — and **ULTRAPLAN**, which offloads complex planning to a cloud container running Opus 4.6 for up to 30 minutes of deep reasoning. These 44 unreleased features behind compile-time flags hint at where full autonomy is headed.

**Devin 2.0** added Interactive Planning and auto-generated architecture documentation (Devin Wiki), with pricing dropping from $500/month to $20 + $2.25 per compute unit. It reports a **67% PR merge rate** on defined tasks but self-describes as "senior-level at codebase understanding but junior at execution." **SWE-bench Verified** top scores now exceed 80%, but the more realistic **SWE-bench-Live** (continuously updated with fresh issues) caps at approximately **19.25% resolve rate** — revealing pervasive benchmark overfitting. The LIVE-SWE-AGENT paper (arXiv:2511.13646) introduced self-evolving agents that create custom tools on-the-fly, achieving 77.4% on Verified and 45.8% on Pro. A key finding from Codegen's February 2026 test: scaffolding matters as much as the model — three different frameworks running the same model scored 17 issues apart on 731 problems.

### Semantic self-awareness through embedding-space coverage maps

The `aashirpersonal/semantic-coverage` GitHub repo is the closest existing implementation to the golden-dataset coverage vision. It projects both documents and queries into a shared latent space using UMAP, applies HDBSCAN clustering to find distinct topics, and identifies **"Red Zones"** — areas of high query density but low document density — as knowledge gaps. The stack uses Sentence-Transformers (all-MiniLM-L6-v2, 384 dimensions), UMAP, HDBSCAN, and scikit-learn. For an agent system, replace "documents" with "agent capability demonstrations" and "queries" with "incoming tasks."

Three papers define the frontier of agent self-awareness through embeddings. **"Latent Space Chain-of-Embedding"** (Wang et al., ICLR 2025, arXiv:2410.13640) discovers that correct and incorrect responses have geometrically distinct hidden-state trajectories — enabling label-free, training-free, millisecond-level self-evaluation. **"Towards Fully Exploiting LLM Internal States for Knowledge Boundary Perception"** (Ni et al., ACL 2025, arXiv:2502.11677) introduces C³ (Consistency-based Confidence Calibration) via question reformulation, improving unknown-detection by 5.6%. And **LOCUS** (arXiv:2601.21082) produces low-dimensional vector embeddings of model capabilities using attention-based encoders, needing **4.8× fewer query evaluations** than baselines for routing — directly applicable to routing tasks to the most capable agent in a multi-agent system.

### DeepEval scoring without burning LLM calls on every output

**DeepEval** (github.com/confident-ai/deepeval, MIT license) offers 50+ research-backed metrics including G-Eval (LLM-as-judge with CoT), DAG Metric (deterministic decision trees — lower overhead than open-ended G-Eval), QAG (question-answer-generation using confined yes/no answers), and non-LLM metrics like BERTScore, BLEU, and ROUGE. For agent evaluation specifically, it assesses both the reasoning layer (plan quality, intent parsing) and the action layer (tool selection, argument generation, call ordering).

The score extrapolation via Lipschitz bounds approach is theoretically grounded. Tang, Yang, and Song's paper **"Understanding LLM Embeddings for Regression"** (arXiv:2411.14708) demonstrates that LLM embeddings inherently preserve **Lipschitz continuity** over the feature space. They introduce the Normalized Lipschitz Factor Distribution (NLFD) — lower skewness correlates with better regression. The practical pattern: embed each test case → find nearest evaluated neighbors in embedding space → interpolate scores weighted by distance. The Lipschitz continuity guarantee bounds interpolation error by the Lipschitz constant × distance. This means you can evaluate a golden subset with full G-Eval, then extrapolate scores to new inputs at near-zero cost.

### Local session storage: LanceDB vs. sqlite-vec

**LanceDB** (github.com/lancedb/lancedb, Apache 2.0) is an embedded AI-native lakehouse built on the Lance columnar format — like SQLite but for vectors, running in-process with zero servers. It handles billions of vectors with IVF/PQ indexing, supports GPU-accelerated index building (CUDA, Apple MPS), and combines full-text search, vector search, and SQL in one system. SDKs exist for Python, TypeScript, and Rust. The LanceDB blog demonstrates agent memory storage showing "significant accuracy gain over SQLite-based memory," with brute-force search over Lance format fast enough for moderate scales without indexing.

**sqlite-vec** (github.com/asg017/sqlite-vec, 6.6K stars) takes the opposite approach — an extremely small, pure C vector search SQLite extension that runs anywhere SQLite runs, including WASM. It supports `float[N]`, `int8[N]` (quantized), and `bit[N]` vector types, with companion extensions for remote embeddings (`sqlite-rembed`) and local GGUF model embeddings (`sqlite-lembed`). Notably, **Claude Code's built-in memory system already uses sqlite-vec** (vec0 virtual table) for embedding similarity over OpenAI text-embedding-3-small vectors (1536 dimensions) combined with FTS5 for keyword matching — this is the production baseline for agent session storage.

For a personal multi-agent system: use **LanceDB** if you need multimodal storage (images, point clouds alongside embeddings), automatic versioning, and rich query capabilities. Use **sqlite-vec** if you want minimal dependencies, WASM compatibility, and seamless integration with existing SQLite infrastructure.

### Confidence-gated autonomy: agents that know when to stop

The **Agentic Uncertainty Quantification (AUQ)** framework (Zhang et al., arXiv:2601.15703, January 2026) is the most complete implementation. Inspired by dual-process cognitive science, it uses a **System 1** fast path (Uncertainty-Aware Memory propagating verbalized confidence through context) and a **System 2** deliberation path (Uncertainty-Aware Reflection triggered when confidence drops below threshold). It addresses the "Spiral of Hallucination" — early epistemic errors propagating irreversibly — and outperforms both ReAct and Reflexion on ALFWorld, WebShop, and DeepResearch benchmarks.

A sobering finding: **"Agentic Uncertainty Reveals Agentic Overconfidence"** (arXiv:2602.06948) shows that GPT-5.2-Codex post-execution agents predict **73% success against a true rate of 35%** on SWE-Bench-Pro. Systematic overconfidence is pervasive. The most effective mitigation is adversarial framing — prompting agents to "find bugs" rather than "verify correctness" reduces overconfidence by up to **15 percentage points**. The **Confidence Before Answering (CoCA)** paper (arXiv:2603.05881, March 2026) proposes outputting confidence *before* the answer using GRPO reinforcement learning, enabling downstream systems to calibrate, abstain, or request human intervention.

The practical three-stage pattern from earezki.com (March 2026): (1) LLM generates answer + structured JSON confidence score + reasoning; (2) if confidence falls below threshold, trigger automated web research; (3) re-answer with augmented context. For a coding agent, add a fourth stage: compare task embedding to the coverage map's "competent zones" — if the task falls in a Red Zone, escalate to human review before executing.

### Building the platform-wide coverage view

The full implementation combines all components. Store session embeddings in LanceDB or sqlite-vec with metadata (agent_id, score, confidence, timestamp). Define a golden dataset of representative tasks as competence zone anchors. Evaluate a golden subset with DeepEval G-Eval, then extrapolate via Lipschitz-bounded interpolation. Project everything with UMAP into 2D/3D space, cluster with HDBSCAN, and color-code by agent identity, score, and confidence. Gaps appear as regions with no high-confidence, high-scoring sessions. For the operational dashboard layer, **Mission Control** (mc.builderz.dev) provides an open-source, SQLite-powered monitoring system with 31 panels and 98 API routes, while **Langfuse** adds open-source LLM observability with structured execution traces.

## Conclusion: where these three systems converge

These three projects aren't decorative — they're structural. Anton provides real-time visual feedback on agent cognition, making invisible state transitions legible and building intuition about when agents are confident versus struggling. The math learning system closes the gap between engineering skill and statistical theory, using the coding sessions themselves as the delivery vehicle — turning every Claude Code run into a preparation session for TAU. And the agentic architecture makes the whole system self-aware: agents that map their own competence boundaries, extrapolate scores without burning LLM calls, and gate their autonomy on calibrated confidence.

The key technical insight connecting all three is **embeddings as a universal substrate**. Anton maps session state to particle physics in a visual embedding. The math system maps code patterns to concept embeddings for contextual learning. The agentic architecture maps sessions, tasks, and capabilities into a shared embedding space for coverage analysis. Build the embedding infrastructure once — LanceDB for storage, UMAP for projection, HDBSCAN for clustering — and all three systems can share it.