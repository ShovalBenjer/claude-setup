---
name: codex-call
description: Run independent, bounded external code-review judges through Codex CLI and, only for explicitly public non-confidential input, the Gemini Developer API. Use automatically after executable checks for high-risk implementations, architecture or performance choices, non-trivial loops, security-sensitive changes, and before claims such as best, optimized, complete, or production-ready. Also use when asked to review, ask Codex, compare Claude with another model family, or obtain an external judge.
---

# External review judges

Treat external models as fallible reviewers, not executable oracles. Run tests
first. Never auto-apply a finding or convert reviewer agreement into proof.

## Default workflow

1. Finish the implementation's executable checks.
2. Run the status probe:

```powershell
$judge = "$HOME\.claude\bin\external-review-judge.py"
python $judge status
```

3. For any high-risk change or strong quality claim, run Codex automatically:

```powershell
python $judge review --repo . --provider codex `
  --output .claude\reviews\codex-latest.json
```

Use `--scope base --base origin/main` for a committed branch. Add
`--criteria <file>` when acceptance criteria are available.

4. Inspect each finding against the repository and executable evidence.
   - Fix a supported material issue and rerun the relevant test and judge.
   - Record a rejected finding with concrete counter-evidence.
   - Treat timeout, invalid JSON, concurrent repository changes, or partial
     provider failure as unavailable, never approval.
   - If reviewers disagree, surface the disagreement instead of averaging it
     away.

## Enforced Codex boundary

The wrapper invokes the installed npm Codex through its absolute Node entrypoint
and requires `Logged in using ChatGPT`. It strips API-key variables and runs:

- `--ask-for-approval never`
- `--sandbox read-only`
- `--ephemeral`
- `--ignore-user-config`
- hooks and web search disabled
- a temporary Git repository containing only the sealed review bundle
- a strict structured-output schema

This prevents the external judge from inheriting the user's global
`danger-full-access` Codex setting. Do not bypass the wrapper with bare
`codex exec` for automatic review.

## Gemini Free Tier boundary

Gemini CLI is installed for explicit future use, but Google stopped serving
free consumer Gemini CLI requests on June 18, 2026. The free judge therefore
uses one direct, tool-free Developer API request pinned to
`gemini-3.6-flash`; it never falls back to Gemini CLI, Vertex AI, another
model, another key, or a paid route.

Google states that Free Tier content may be used to improve its products.
Therefore:

- Never send employer/proprietary code, customer data, resumes, recruiting
  data, credentials, personal resources, or private repositories to Gemini
  Free Tier.
- Use Gemini only when the operator explicitly classifies the exact bundle as
  public and non-confidential.
- Require `GEMINI_API_KEY` in the process environment. Never place it in this
  skill, a prompt, command argument, repository, log, or review artifact.
- Require a current attestation matching the key. After the operator verifies
  AI Studio shows `Billing Tier: Free` / `Set up billing` and no billing
  account is linked, run:

```powershell
python $judge attest-gemini-free --confirm-free-project
```

Then an explicitly public comparison may run:

```powershell
python $judge review --repo . --provider both --public `
  --output .claude\reviews\panel-latest.json
```

No per-request API switch can guarantee a project is unbilled. The attestation
expires after 30 days so the operator must periodically recheck AI Studio.

## Interpretation

- Tests and runtime observations remain the primary oracle.
- Codex provides an independent OpenAI-family review under ChatGPT auth.
- Gemini provides stronger model-family decorrelation but only within the
  public-data/free-tier boundary.
- Agreement raises confidence; it does not establish optimality.
- A strong claim remains "best among tested candidates under these
  constraints," with residual risk stated.
