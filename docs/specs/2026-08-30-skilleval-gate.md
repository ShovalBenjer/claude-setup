# Skilleval Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** skilleval

## Problem

`tools/skilleval/run.py` grades skill routing quality: given a prompt from a
skill's routing fixture, does the right skill win? The tool existed with a
selftest and was listed in AGENTS.md, but nothing in the quality contract
invoked it. A broken skill description that misroutes prompts would pass the
gate silently.

## Solution

A new `cmd` domain `skilleval` in `quality-contract.json` runs
`python tools/skilleval/run.py scan`. The tool exits 0 when every graded
skill routes correctly (or has no fixture), and nonzero when any skill's
fixture routes to the wrong skill.

Skills without routing fixtures are counted as uncovered and reported but do
not fail. The domain catches regressions, not coverage gaps.

## Scope

- `quality-contract.json`: `skilleval` domain entry (cmd, timeout 120s)
- No changes to `run.py` itself

## Design decisions

- A `cmd` domain rather than a builtin, because `run.py scan` already has
  the right exit-code contract.
- Timeout set to 120s because the scan compares prompt-to-skill similarity
  across all 89 skills for each fixture.
- The uncovered count (84 of 89) is informational. Requiring fixtures for
  all skills would be a coverage mandate, not a routing quality check.

## Non-goals

- Enforcing that every skill has a routing fixture. That is a coverage
  decision, not a quality gate.
- Running the eval in strict-ties mode. Ties are reported but not fatal by
  default, matching the tool's own convention.
