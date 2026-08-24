# Testing gaps: axia-seekapa-cs-agents (this repo, $HOME worktree)

Audited 2026-07-07 in a Claude Code session, alongside the same pass across five other
repos, triggered by a mock-theater fear check ("is my testing actually worth anything").
Method: a parallel qa-lab agent read every test file under `tests/`, classified every
mock/patch/monkeypatch hit, sampled assertions, and traced the Foundry eval gate.

## Verdict

Essentially zero mock theater. A full-directory grep for `MagicMock` / `Mock(` /
`@patch` / `mocker.` / `responses.` / `respx` across every `.py` file in `tests/`
returns exactly one hit, and it is a legitimate boundary patch on deploy tooling, not
the CS-agent webhook handler. Every fake in the suite (`FakeChatwootClient`,
`FakeCallAgent`, `FakeCrmHttpClient`, `FakeSmtpClient`) sits at a genuine I/O edge.
`FakeCrmHttpClient` is driven by a recorded fixture file
(`tests/test_data/seekapa_verify_fixtures.jsonl`, real CRM response shapes), which is
the concrete instance of "use recorded fixtures" the house rule asks for.

## Top gaps (ranked)

1. The CI pipeline (cs-agents-ci, def 121) names `tests/test_sanitize_language_closer.py`
   in its Build stage. That file does not exist anywhere in the repo (confirmed by
   targeted find and by a repo-wide grep for `sanitize_language_closer`, zero hits).
   Reproduced: this exact pytest invocation exits with code 4, "no tests collected."
   The underlying sanitize logic is not actually blind, it is covered by 17 test
   classes inside `tests/test_chatwoot_webhook.py:381-590`, but the CI's own named
   pointer is broken regardless.
2. At least 12 real, well-built test files exercise distinct production modules with
   the same real-component discipline seen elsewhere (`test_channel_router.py`,
   `test_escalation_note.py`, `test_pre_classifier.py`, `test_take_message_flow.py`,
   `test_seekapa_verifier.py`, `test_v109_invariants.py`, `test_foundry_eval_gate.py`,
   and more), but the only confirmed runner is the developer-discipline-gated
   `scripts/run_sota_local.sh`, not an automated CI stage. A regression in, for
   example, the pre-classifier or escalation-note logic could pass the narrow named
   Build stage if a contributor skips the local script.
3. No property-based or mutation-testing layer exists anywhere in this repo. The
   sanitize/pre-classifier/escalation logic is regex- and keyword-heavy, exactly the
   kind of code where hand-picked example tests can look thorough while missing edge
   cases a generative test or a mutation-kill-rate score would surface.
4. The "Foundry smoke eval" (`scripts/foundry_eval_gate.py`) is a real, working
   primary-plus-audit-judge harness, not theater, but it is disabled in this repo's
   CI (moved to post-deploy) and its `--max-rows` defaults to 10 against a 25-row
   dataset, so an unattended run silently checks less than half the dataset.

## Pick up here

- [ ] Fix the CI Build stage: either create `test_sanitize_language_closer.py`
      (consolidate the existing sanitize test classes from `test_chatwoot_webhook.py`
      into it) or repoint the pipeline's named file list to what actually exists.
- [ ] Widen the CI Build stage's pytest invocation to the full `tests/` directory
      (minus deepeval, matching `run_sota_local.sh`'s own `-k "not deepeval"` pattern)
      instead of the current 6 hand-named files.
- [ ] Consider hypothesis property tests for the sanitize/pre-classifier/escalation
      regex logic.
- [ ] If the smoke eval stays post-deploy, raise `--max-rows` toward the full 25-row
      dataset, or state explicitly why 10 is the intended sample size.

## Related

- CI/CD pipeline audit (this repo is pipeline def 121):
  `~/Documents/CICD_SOTA_Pipeline_Audit_20260706/CICD-SOTA-Pipeline-Audit-2026-07-06.md`
