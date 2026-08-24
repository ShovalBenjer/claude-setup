# Model and harness failure modes

Use this reference to diagnose behavior without inventing a closed model's
architecture.

## What is known

- Claude's internal architecture is not disclosed in enough detail to attribute
  a coding failure to a particular attention, routing, or decoder mechanism.
- Fable 5's system card reports residual scope creep, destructive behavior,
  reward hacking, grader exploitation, and imperfect coding-summary honesty in
  targeted evaluations. Those targeted rates are not production prevalence.
- Kimi K3 and DeepSeek V4 disclose more architecture detail, but their benchmark
  harnesses, serving stacks, prompts, and tool contracts differ from Claude Code.
  Architecture labels do not predict behavior in this repository.

Refresh current claims from primary sources:

- Anthropic Fable/Mythos 5 system card:
  https://www-cdn.anthropic.com/2f9323abbcc4abe219577539efe19a623c9ca2bd/Claude%20Fable%205%20%26%20Claude%20Mythos%205%20System%20Card.pdf
- Anthropic long-running-agent harness:
  https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic context engineering:
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Kimi K3 official technical blog:
  https://www.kimi.com/blog/kimi-k3
- DeepSeek V4 official release:
  https://api-docs.deepseek.com/news/news260424/

## Observable failure classes

| Failure | Typical symptom | Mechanical countermeasure |
|---|---|---|
| Frequency/default bias | Familiar loop/library chosen without comparison | Require alternatives and explicit constraints |
| Premature convergence | First plausible patch is treated as final | Best-of-N plus executable selector |
| Lost-in-the-middle/context rot | Earlier requirements disappear | Small context packs, root contract, durable evidence ledger |
| Compaction loss | Session continues with missing decisions | Structured handoff and re-read authoritative files |
| Specification compression | Edge cases vanish during implementation | Acceptance-to-test traceability |
| Self-confirmation | Author writes tests that mirror its own bug | Holdout, differential, mutation, or fresh reviewer |
| Reward/grader hacking | Tests changed or reference answer copied | Protect tests, inspect diff/history access, hidden cases |
| False completion | Prose says done while state is unobserved | Verify final environment state |
| Tool truncation | Partial output treated as complete | Persist full output or state explicit bounds |
| Scope creep | Unrequested files or systems changed | Write scope, permissions, changed-file audit |
| Overeager optimization | Complex novelty replaces simple correct code | Benchmark and operational-cost comparison |
| Lazy optimization | Obvious N+1 or quadratic loop remains | Loop audit and representative benchmark |

## Decoder and search claims

Likelihood-based generation can favor common, generic continuations. Sampling
multiple candidates can increase the chance of finding a correct program, but it
also creates more plausible wrong programs. An oracle is the deciding asset.

Do not claim:

- beam search or a specific decoder caused a Claude failure;
- a one-million-token limit means reliable reasoning over one million tokens;
- a mixture-of-experts model is automatically more agentic;
- a higher vendor benchmark means a better choice for this repository.

Evaluate models with the same snapshot, tools, permissions, prompt, effort/token
budget, hardware, and multiple trials. Grade the final environment state.

