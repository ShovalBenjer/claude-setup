# AI PR Review Prompt Best Practices
## Executive Summary
AI-powered PR review has matured significantly, but prompt quality remains the single largest determinant of output usefulness. A well-designed system prompt is the difference between noisy, generic comments and actionable, context-grounded findings. The current prompt (captured in the screenshot) is already solid — it has a persona, a knowledge base, a priority ordering, and a structured output format. This report benchmarks it against industry research and state-of-the-art practices, then identifies concrete improvements.



***
## What the Current Prompt Does Well
The existing prompt covers most of the foundations identified in recent literature:

- **Persona + knowledge-base grounding**: Assigning an expert role ("CI Code Reviewer") with reference materials (Clean Code, Code Complete, testing SOTA) is a proven technique that measurably shifts model behavior toward domain-specific expertise. Being specific about the persona — e.g., listing the exact knowledge base — is explicitly recommended over vague role labels.[^1]
- **Structured output with priority ordering**: Listing findings in Critical → High → Medium → Low order matches the output pattern used by Atlassian's production RovoDev system, which found that prioritized, actionable comments led to a 38.70% code-change rate and a 30.8% reduction in PR cycle time.[^2]
- **Diff-only scope**: Explicitly constraining review to "only the changes in the diff" reduces hallucination risk and avoids over-broad commentary on unrelated code. Research confirms that targeted context outperforms full-file dumps: "providing targeted and relevant code context is critical for maximizing LLM performance".[^3]
- **Issue anatomy (title, severity, file:line, explanation, fix)**: This structure mirrors what enterprise-grade tools like CodeRabbit use internally, and is recognized as the minimal viable information per finding.[^4][^5]
- **"Do not" section**: Negative constraints ("do not re-format entire files", "do not invent project-specific rules") are as important as positive instructions for controlling LLM drift — a technique explicitly validated in prompt engineering literature.[^6][^7]

***
## Gap Analysis: What Can Be Improved
### 1. Persona Specificity — Too Broad
**Current state:** "You are a CI Code Reviewer that inspects diffs and pull requests for all kinds of code (backend, frontend, scripts, infra, tests)."

**Problem:** Broad multi-role personas produce diluted output. Research confirms that specific personas ("backend engineer with expertise in distributed systems") produce more focused and useful analysis than generic ones ("developer"). The same model knowledge base produces materially different output depending on how narrow the role specification is.[^8][^1]

**Recommendation:** Decompose into a primary persona with an explicit scope hint per invocation. For example, inject the detected language/stack into the system prompt at review time:

```
You are a CI Code Reviewer specializing in {detected_stack} (e.g., Python Azure Functions, TypeScript, Terraform).
Your secondary lens is CI/CD pipeline correctness and test strategy.
```

This is achievable with a simple pre-processing step that detects file extensions in the diff and fills in the `{detected_stack}` variable.

***
### 2. Chain-of-Thought is Implicit, Not Explicit
**Current state:** The prompt describes what to produce but does not instruct the model to reason before producing findings.

**Problem:** For complex diff analysis, LLMs that jump straight to output frequently miss inter-file dependencies or subtle logic errors. Chain-of-thought (CoT) prompting — instructing the model to reason step-by-step before generating findings — measurably improves accuracy on complex reasoning tasks. This is especially relevant for **GPT-5.1 Codex Mini at low reasoning effort** (the current configuration), where the OpenAI prompting guide specifically recommends adding explicit reasoning scaffolding to compensate for limited internal thinking tokens.[^9][^10][^11][^12]

**Recommendation:** Add a pre-output reasoning step:

```
Before listing issues, briefly reason through:
1. What is the author trying to achieve?
2. What are the riskiest paths introduced by this diff?
3. Which changed lines interact with existing state/storage/auth?
Only then produce your structured findings list.
```

At `reasoning_effort: Low`, this explicit CoT preamble can dramatically improve output quality.[^11][^13]

***
### 3. Reasoning Effort Setting vs. Model Type
**Current state:** `Model: GPT 5.1 Codex Mini`, `Reasoning effort: Low`, `Max output tokens: 4096`.

**Problem:** GPT-5.1 Codex Mini at `Low` reasoning is optimized for speed and cost, but GitHub issue reports and community testing confirm it "ends up spending little reasoning time on things that are actually subtle and hard issues" and that "inconsistency kills the UX". The 4096 token output cap can also truncate the verdict section on large PRs.[^13]

**Recommendation:**
- For security-critical or large PRs, escalate to `Medium` reasoning effort — most production workflows find "many workflows can be accomplished with consistent results at medium or even low reasoning_effort" but code security review is specifically cited as a case that benefits from additional reasoning.[^11]
- Increase `Max output tokens` to 6144–8192 to avoid truncated verdicts.
- Alternatively, add to the prompt: *"Think harder about security-related changes involving authentication, authorization, serialization, or external API calls."* This nudge mirrors the "think harder" prompt pattern documented by the community as a routing signal on Codex Mini.[^13]

***
### 4. Missing: Security-Explicit Checklist Anchor
**Current state:** "Critical bugs / logic errors / security risks" is listed but without grounding.

**Problem:** LLMs produce more precise security findings when anchored to a concrete standard rather than asked to self-generate vulnerability categories. The anti-pattern avoidance technique — explicitly naming CWE categories or OWASP risks — has been shown to refocus the model on known weakness patterns.[^7][^14]

**Recommendation:** Add a security anchor to the prompt:

```
For security issues, cross-check against: OWASP Top 10, CWE-20 (improper input validation),
CWE-89 (SQL injection), CWE-798 (hardcoded credentials), CWE-611 (XXE),
insecure deserialization, missing authZ checks, and secrets in env/config.
Flag prompt-injection risks in any LLM-facing code paths.
```

This focused anchoring reduces both false positives and false negatives in security findings.[^15][^7]

***
### 5. No Actionability Quality Gate
**Current state:** The prompt asks for "a specific fix suggestion or code sketch" but provides no quality standard for that suggestion.

**Problem:** Actionability is the primary driver of whether AI review comments lead to actual code changes. Atlassian's RovoDev team added an explicit "actionability check" — a second LLM pass to ensure each comment would likely lead to code resolution — and this was key to achieving 38.70% code-change rate. Comments that don't specify exactly what to change get ignored.[^16][^2]

**Recommendation:** Add an output quality constraint:

```
For each issue: your fix suggestion MUST include either
(a) a corrected code snippet of ≤15 lines, OR
(b) a specific named pattern, function, or library to use instead.
Do not suggest "consider refactoring X" without showing what the refactoring looks like.
```

***
### 6. Missing: Hallucination Guard / Uncertainty Disclosure
**Current state:** The prompt implicitly trusts the model's output; there is no instruction to flag uncertainty.

**Problem:** AI PR review is particularly susceptible to hallucination about file paths, function signatures, and library APIs not present in the diff. Research shows that explicitly asking the model to cite evidence from the diff — or to disclose uncertainty — reduces confident-sounding false positives.[^17][^18][^19][^20]

**Recommendation:** Add:

```
Ground every finding in a specific line or pattern visible in the diff.
If you are uncertain whether an issue applies (e.g., you cannot see the called function's implementation),
say so explicitly: "Possible issue — verify at [location]."
Do not invent function signatures, variable names, or behavior not visible in the provided diff.
```

***
### 7. Output Token Budget: No Tiering by Severity
**Current state:** All findings are reported at equal depth.

**Problem:** Critical and High issues deserve detailed explanation + code; Low findings shouldn't consume the same token budget. Smaller PRs give AI "dramatically better results" because of reduced scope, and token budgeting keeps the output scannable.[^21]

**Recommendation:** Add output tiering to the prompt:

```
- Critical/High: Full explanation + root cause + code fix (≤15 lines)
- Medium: 2-sentence explanation + fix direction
- Low: One-line note only; group multiple Low issues under a "Minor nits" list
```

***
### 8. PR Context Utilization (Title & Description)
**Current state:** The Azure DevOps task already has "Use PR title & description as context" checked ✓. This is good.

**Recommendation:** Reinforce this in the prompt text itself so the model actively uses it:

```
Use the PR title and description as the primary signal for INTENT.
If the code diff does not match the declared intent, flag this as a High issue.
If the description is empty, note this in your summary as a process gap.
```

Research from CodeRabbit shows that PR summaries generated from description context save reviewers ~3 minutes per PR on large diffs.[^22]

***
## Proposed Refined Prompt Structure
The following structure incorporates all improvements above while preserving the existing prompt's strengths:

```
## Identity
You are a CI Code Reviewer specializing in {detected_stack}.
Your expertise spans: Clean Code, Code Complete, modern CI testing strategy,
LLM application patterns, infrastructure-as-code, and security (OWASP Top 10, CWE top categories).

## Pre-Review Reasoning (do this silently before listing findings)
1. Summarize what the author is trying to achieve (from PR title, description, and diff).
2. Identify the 3 riskiest paths introduced by this diff (auth, storage, external calls, concurrency).
3. Check whether the diff's scope matches the PR description.

## Review Scope
Review ONLY the lines in the diff and their directly referenced context.
Do not audit unrelated existing code unless it is called by changed lines.

## Security Anchor
For every security-related finding, reference the specific weakness category:
OWASP Top 10 | CWE-20 | CWE-89 | CWE-798 | CWE-611 | prompt injection risk.
Flag any hardcoded secrets, missing input validation, missing authZ, or insecure deserialization.

## Hallucination Guard
Ground every finding in a specific visible line/pattern from the diff.
If you cannot see the called function, write: "Possible issue — verify at [location]."
Do not invent signatures, APIs, or behavior not visible in the diff.

## Output Format
**Summary** (2–3 sentences: intent, scope, overall impression)

**Findings** (priority order):
| # | Severity | Title | File:Line | Explanation | Fix |
|---|----------|-------|-----------|-------------|-----|

Fix depth by severity:
- Critical/High → corrected code snippet (≤15 lines) + root cause
- Medium → 2-sentence explanation + fix direction
- Low → one-line note; group into "Minor nits"

Severity categories:
1. Critical bugs / logic errors / security risks
2. Test gaps (unit/integration/E2E/property)
3. Design problems (SRP violations, coupling, boundary leaks)
4. Readability, naming, comments

**Overall Verdict**: Block | Approve with comments | Approve
(If Block: list the minimum changes needed to unblock.)

## Constraints
- Do not reformat entire files or bikeshed style.
- Do not invent project rules not implied by the codebase.
- Do not flag issues you cannot ground in the diff.
- Always call out data-loss, security, and reliability risks.
- If PR description is missing, flag it in the summary.
```

***
## Model & Configuration Recommendations
| Setting | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| Model | GPT 5.1 Codex Mini | GPT 5.1 Codex Mini (keep) | Appropriate for CI cost/speed[^23] |
| Reasoning Effort | Low | **Medium** for PRs touching auth/security/infra; Low for style-only | Low effort misses subtle issues on Codex Mini[^13] |
| Max Output Tokens | 4096 | **6144–8192** | Prevents verdict truncation on large PRs[^11] |
| File Extensions Ignore | .png,.jpg,...,.csv,.json | Add: `.lock`, `.min.js`, `.generated.*` | Lock files and generated files produce noisy irrelevant findings[^24] |
| Custom Prompt | Current | Apply refined prompt above | — |

***
## Key Principles Validated by Research
| Principle | Evidence |
|-----------|----------|
| Specific persona > generic role | Focused personas produce domain-specific, less generic output[^1] |
| Explicit CoT boosts complex reasoning | Step-by-step reasoning before output improves accuracy, especially at low reasoning effort[^9][^11] |
| Targeted diff context > full-file dumps | "Left Flow" (targeted context) outperforms "Full Flow" for LLM code review tasks[^3] |
| Actionability is the adoption metric | 38.70% code-change rate achieved via actionability quality gate[^2] |
| LLM + static analysis hybrid beats either alone | Hybrid LLM+static analysis eliminates 94–98% of false positives[^15] |
| Negative constraints reduce hallucination | "Do not invent" instructions are as important as positive instructions[^7][^6] |
| Security anchoring to specific CWEs improves precision | Anti-pattern avoidance pattern refocuses models on known weakness categories[^7][^14] |
| PR scope size matters | Smaller PRs yield dramatically better AI review results[^21] |

***
## Implementation Checklist
- [ ] Add `{detected_stack}` variable injection from diff file extensions
- [ ] Add explicit pre-review reasoning section to system prompt
- [ ] Add security anchor (OWASP/CWE categories)
- [ ] Add hallucination guard instruction
- [ ] Add output tiering by severity (code snippet for Critical/High; one-liner for Low)
- [ ] Increase Max Output Tokens to 6144+
- [ ] Switch to Medium reasoning effort for PRs with auth/security/infra changes (consider a separate pipeline trigger)
- [ ] Add `.lock` and `.generated.*` to ignored file extensions
- [ ] Add PR description presence check to prompt
- [ ] Consider a secondary LLM-as-Judge pass for actionability validation on Critical findings[^2][^25]

---

## References

1. [How to Prompt LLMs for Better, Faster Security Reviews](https://crashoverride.com/blog/prompting-llm-security-reviews) - Learn how to write effective LLM prompts that improve code security reviews, reduce false positives,...

2. [RovoDev Code Reviewer: A Large-Scale Online Evaluation of LLM ...](https://arxiv.org/html/2601.01129v2) - In this paper, we present RovoDev Code Reviewer, a Review-Guided, Quality-Checked Code Review Automa...

3. [Towards Practical Defect-Focused Automated Code Review - arXiv](https://arxiv.org/html/2505.17928v2) - The results reveal that using only the diff or parent function is less effective, while more detaile...

4. [How we built our AI code review tool for IDEs - CodeRabbit](https://www.coderabbit.ai/blog/how-we-built-our-ai-code-review-tool-for-ides) - Learn how we redesigned our pipeline to create an AI code review tool for instant IDE reviews, cutti...

5. [How to evaluate AI code review tools: A practical framework](https://www.coderabbit.ai/blog/framework-for-evaluating-ai-code-review-tools) - A vendor-neutral framework to evaluate AI code review tools using your own PRs, severity labels, met...

6. [The Ultimate Guide to AI Prompt Engineering [2025] - V7 Labs](https://www.v7labs.com/blog/prompt-engineering-guide) - Prompt engineering guide for beginners and advanced AI users. Explore techniques, tools, and best pr...

7. [A Simple Prompt Pattern for Safer AI-Generated Code - Endor Labs](https://www.endorlabs.com/learn/anti-pattern-avoidance-a-simple-prompt-pattern-for-safer-ai-generated-code) - The anti-pattern avoidance prompt pattern is a zero-shot technique that instructs the model to gener...

8. [Prompt Engineering: Part 2 – Best Practices for Software Developers ...](https://blogs.sw.siemens.com/thought-leadership/prompt-engineering-part-2-best-practices-for-software-developers-in-digital-industries/) - Prompt engineering can significantly streamline software development processes, improving code compr...

9. [8 Chain-of-Thought Techniques To Fix Your AI Reasoning | Galileo](https://galileo.ai/blog/chain-of-thought-prompting-techniques) - Hand-curating a few-shot exemplars works well until you face hundreds of problem types. At that scal...

10. [Chain of Thought Prompting Explained (with examples) - Codecademy](https://www.codecademy.com/article/chain-of-thought-cot-prompting) - Chain of Thought prompting enables LLM models to perform complex reasoning tasks by forcing the mode...

11. [GPT-5 prompting guide - OpenAI Developers](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide/) - As our most steerable model yet, GPT-5 is extraordinarily receptive to prompt instructions surroundi...

12. [GPT-5.1 Prompting Guide - OpenAI Developers](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5-1_prompting_guide/) - GPT-5.1 introduces a new reasoning mode: none . Unlike GPT-5's prior minimal setting, none forces th...

13. [gpt-5-codex high is far worse than gpt-5 high on complex problems](https://github.com/openai/codex/issues/3826) - The Codex models definitely "feel" more tuned to be used in agentic tools, but not in a good way. Th...

14. [4 Best Practices for AI Code Security: A Developer's Guide](https://www.stackhawk.com/blog/4-best-practices-for-ai-code-security-a-developers-guide/) - By implementing rules, you make specific requirements automatic, rather than relying on developers t...

15. [Reducing False Positives in Static Bug Detection with LLMs - arXiv](https://arxiv.org/html/2601.18844v1) - Our experimental results show the strong potential of LLM-based techniques in reducing false positiv...

16. [5 Ways to Measure the Impact of AI Code Review - Baz](https://baz.co/resources/5-ways-to-measure-the-impact-of-ai-code-review) - 1. Start With Developer Outcomes, Not Comment Counts · 2. Sentiment Is the Missing Signal · 3. Close...

17. [Exploring Hallucinations in LLM-Generated Code - arXiv](https://arxiv.org/html/2404.00971v3) - Hallucination mitigation exploration: We evaluated three widely-used prompt enhancing strategies to ...

18. [The importance of prompt engineering in preventing AI hallucinations](https://alfapeople.com/uk/importance-of-prompt-engineering-preventing-ai-hallucinations/) - Prompt engineering prevents AI hallucinations by crafting clear, structured instructions to enhance ...

19. [How to keep AI hallucinations out of your code - Azalio](https://www.azalio.io/how-to-keep-ai-hallucinations-out-of-your-code/) - “You should tell the LLM to maintain a certain pattern, or remind it to use a consistent method so i...

20. [Stop AI Agent Hallucinations: 4 Essential Techniques](https://dev.to/aws/stop-ai-agent-hallucinations-4-essential-techniques-2i94) - AI agents can hallucinate when executing tasks—fabricating statistics, choosing wrong tools, ignorin...

21. [The 6 Best AI Code Review Tools for Pull Requests in 2025](https://dev.to/heraldofsolace/the-6-best-ai-code-review-tools-for-pull-requests-in-2025-4n43) - A comprehensive comparison of platforms, bots, and agents to speed up your code review cycle. Introd...

22. [AI Code Review on GitHub: Copilot vs CodeRabbit vs an Agent That ...](https://cotera.co/articles/ai-code-review-github) - We tested three approaches to AI code review on GitHub: Copilot, CodeRabbit, and a custom agent with...

23. [GPT-5.2 (Non-reasoning) vs GPT-5.1 Codex mini (high)](https://artificialanalysis.ai/models/comparisons/gpt-5-2-non-reasoning-vs-gpt-5-1-codex-mini) - Comparison between GPT-5.2 (Non-reasoning) and GPT-5.1 Codex mini (high) across intelligence, price,...

24. [AI Code Review in Your CI/CD Pipeline - DEV Community](https://dev.to/pockit_tools/ai-code-review-in-your-cicd-pipeline-automating-pr-reviews-test-generation-and-bug-detection-56j4) - A generic "review this code" prompt produces generic results. You need to be extremely specific abou...

25. [LLM-as-a-judge: a complete guide to using LLMs for evaluations](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) - LLM-as-a-judge is a common technique to evaluate LLM-powered products. It grew popular for a reason:...

