# Corpus License Gate

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/license_gate.py

## Problem

The research corpus spec identified 13 external seed sources with
varying license terms. 1 was legally blocked (developer-roadmap, all
rights reserved), 2 were copyleft (GPL, NC), and the rest ranged from
MIT to CC-BY-SA. ADR-0005 requires enforcement over prose: a source
that must not be ingested should be refused by a mechanical gate, not
by a sentence in a document. Step 6 of the spec called for a stage 1
license gate that refuses blocked sources by canonical hostname.

## Solution

A new tool `tools/corpus/license_gate.py` with four subcommands:

- `check --uri URI --license SPDX [--verdict VERDICT] [--mtime TIME]`:
  checks a single source against the license gate and returns its
  verdict, liveness, reason, and admit/refuse decision.
- `batch --manifest PATH`: screens a JSON manifest of candidate sources
  and reports admitted vs refused counts with reasons.
- `blocked`: lists all blocked hostnames.
- `selftest`: exercises 9 checks covering hostname blocking, license
  classification, liveness detection, and batch screening.

### License classification

Each source gets a verdict derived from its SPDX license identifier:

- `vendor`: MIT, Apache-2.0, CC-BY-4.0, and other permissive licenses.
  Permits copying with attribution.
- `index_only`: CC-BY-SA (ShareAlike). May store locally for retrieval
  but must not redistribute in repo output.
- `link_only`: GPL, CC-BY-NC (copyleft or NonCommercial). Store URL
  and notes only, never the source text.
- `blocked`: all rights reserved, NOASSERTION, or hostname in the
  blocklist. Refused entirely.

### Hostname blocklist

`nilbuild/developer-roadmap` and its old alias
`kamranahmedse/developer-roadmap` are blocked by canonical hostname.
The pipeline refuses them before reading any content, per the spec
requirement that the block is by hostname, not by policy prose.

### Liveness

Sources whose `upstream_mtime` is older than 18 months are marked
`liveness='stale'`. A stale source may never win a contradiction
against a live source (enforced by the contradiction detector).

### Batch screening of spec sources

The 14 spec sources (13 named seeds plus the old alias) gate as:
- 11 admitted (8 vendor + 2 index_only + 1 vendor-stale)
- 3 refused (1 blocked hostname + 1 GPL copyleft + 1 NC clause)

The ml-design-patterns repo (Apache-2.0, 2021, archived) is admitted
by the license gate but marked stale. The spec recommends dropping it
on relevance grounds; that is an operator decision, not a license
enforcement.

## Results

- developer-roadmap: refused by hostname (exit code 1)
- All 9 selftest checks pass
- Batch screening matches spec section 3.3 verdicts

## Design decisions

- Hostname matching over URI parsing: simple substring match on the
  canonical URI is sufficient since all URIs follow the
  `github://owner/repo` pattern.
- Override mechanism: `override_verdict` allows the operator to force
  a verdict for edge cases (e.g. CC-BY-4.0 30-seconds-of-code demoted
  to index_only for size reasons).
- NOASSERTION blocked: GitHub's NOASSERTION label hides the actual
  license. The gate refuses it and requires reading the LICENSE file.
- Admitted = vendor or index_only: link_only and blocked are refused.
  link_only sources can still have their URLs stored manually but
  cannot enter the ingestion pipeline.

## Scope

- `tools/corpus/license_gate.py`: new tool
- `docs/specs/2026-08-30-corpus-license-gate.md`: this spec

## Non-goals

- Fetching or cloning external repositories (separate from gating).
- Automatic LICENSE file reading (the gate takes pre-resolved SPDX).
- Ingestion pipeline orchestration (the gate is one stage, not the
  pipeline).
