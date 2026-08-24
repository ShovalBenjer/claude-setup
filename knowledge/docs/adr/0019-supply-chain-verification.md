# ADR-0019: third-party tools are adopted on recorded evidence, not refused on principle

Date: 2026-07-30
Status: accepted
Lane: A (harness)

## Context

Two third-party tools arrived on 2026-07-30 and got opposite answers from the
same session for no principled reason.

RTK was installed by downloading a GitHub release zip and checking its SHA256
against the vendor's published checksums file. Allowed.

Oak documents its install as `curl -fsSL https://oak.space/install | sh`. Refused.

The refusal was not wrong about the risk. It was wrong about the remedy, and the
operator said so: a harness that answers no to every install it cannot verify
does not become safe, it becomes stale, and in a field that moves this fast a
stale harness is a slower failure than a compromised one. Refusing is also not a
policy, because nothing in the repo wrote down what would have made the answer
yes. The next tool gets whatever answer the next session happens to feel like.

The gap is structural. `quality-contract.json` has twelve domains and the closest
one to this is `security`, which is `builtin: secret_scan`: it greps tracked files
for credential-shaped strings. It says nothing about where a binary on this machine
came from, whether anyone hashed it, or whether any advisory database has ever seen
it. `docs/QUALITY-CONTRACT.md` line 26 describes that domain's scope as value-shaped
patterns plus one name-shaped rule, which is accurate and is not supply chain.

## Decision

Add `tools/supply/verify.py`, an append-only provenance ledger at
`state/supply-chain.jsonl`, and a `supply_chain` gate domain. Adoption of a
third-party artifact is a recorded decision with named evidence, on the same rule
`tools/gate/gate.py` already runs on: a property counts as satisfied when a
command exited zero or a named value exists, and anything else is UNCOVERED, and
UNCOVERED refuses.

Four properties, and only the first is not waivable:

1. **sha256 of the installed bytes.** No hash, no adoption, ever. Without it
   nothing else in the record is about any particular file, and a verified
   signature over bytes nobody hashed tells you about some artifact, not about
   the one on your disk. `evaluate()` refuses a waiver aimed at this property,
   and the selftest plants that exact attempt.
2. **A recorded source.** The bytes have a stated origin, or they have none.
3. **Signature: verified, or waived with an expiry.** Unsigned is a known state.
   Unchecked is an unknown one. The ledger records which, because collapsing the
   two is how "the vendor does not sign" becomes indistinguishable from "nobody
   looked".
4. **Scan: clean, or findings explicitly accepted, or waived with an expiry.**
   `unavailable`, meaning no scanner is installed, is UNCOVERED and refuses.

Waivers carry a reason and an expiry, and an expired one is a refusal rather than
a skip, verbatim from the gate's own waiver rule. The ledger is hash-chained the
way `state/bus.jsonl` is, with `verify-ledger` to check it. The chain does not
defend against someone rewriting the whole file and recomputing it, and it does
not claim to; it makes a single row edited after the fact visible, which is the
realistic failure.

### On `curl | sh`

**Rule: refused, for one mechanical reason, and never on principle.** The bytes
that execute are never written to disk, so no hash of them exists, so property 1
above can never be satisfied and no later audit can answer what ran. It is not
refused because piping is spooky. It is refused because it destroys the evidence.

**When it is acceptable: never, because the substitute costs one extra command.**
This is deliberately not a judgement call about vendor reputation. A rule with a
"trusted vendor" exception is a rule that gets argued rather than followed, and
the two documented compromises of this pattern in the wild were both trusted
vendors serving different bytes to the pipe than to a browser.

**The substitute**, which reaches the same server over the same TLS and trusts
the same vendor exactly as much:

```bash
python tools/supply/verify.py fetch-script https://oak.space/install \
    --out vendor/oak-install.sh
# read it; it is on disk now, and its sha256 is in the ledger
sh vendor/oak-install.sh
python tools/supply/verify.py record "$(command -v oak)" --source https://oak.space/install
python tools/supply/verify.py adopt --sha256 <hash> --reason "..."
```

`fetch-script` downloads, hashes, records and refuses to execute. Nothing about
the network changed. What changed is that afterwards somebody can answer what
ran, and if the vendor's server is later found to have served a different script
on that date, the hash on record either matches the clean one or it does not.

The stronger form, when the vendor supports it: fetch the versioned release
artifact instead of the redirecting installer, with `--expect-sha256` taken from
the vendor's published checksums file. That is what was done for RTK, and it is
the pattern this ADR generalises rather than the exception it grandfathers.

## Alternatives rejected

Every tool below was checked against its own repository on 2026-07-30 rather than
recalled. None of them is rejected as bad; they are rejected as **not a
substitute for the ledger**, and four of them are named as the scanners
`verify.py scan` will drive when installed.

| Tool | Verified at | Why it is not the decision |
| --- | --- | --- |
| Trivy (Aqua) | github.com/aquasecurity/trivy | Real, Apache-2.0, scans images, filesystems, repos, VM images and clusters for CVEs, IaC issues, secrets and licences. A scanner, not a provenance record: it tells you what is wrong with bytes you already have and nothing about where they came from or who decided to keep them. Wired in as a `scan` backend. |
| Grype + Syft (Anchore) | github.com/anchore/grype | Real, Apache-2.0, vulnerability matching over container images, filesystems and Syft SBOMs. Same limitation as Trivy, plus it wants an SBOM to be at its best, and a downloaded release binary does not come with one. Wired in as a `scan` backend. |
| OSV-Scanner (Google) | github.com/google/osv-scanner | Real, Apache-2.0, Go, matches dependencies against the OSV database with call analysis to cut false positives. Best of the three for source trees and lockfiles, which is why it is tried first. Still advisory matching, still not provenance. Wired in as a `scan` backend. |
| cargo-audit (RustSec) | github.com/rustsec/rustsec | Real, one of six crates in the RustSec repo, audits `Cargo.lock` against the RustSec advisory database. Operator is Rust-first so this matters, but it reads a lockfile in a project; it has nothing to say about a downloaded binary. Wired in as a `scan` backend. |
| cargo-deny (Embark) | github.com/EmbarkStudios/cargo-deny | Real, 0.19.9, dual MIT/Apache-2.0, four checks: advisories, bans, licences, and **sources**, which is the closest thing in this list to what this ADR wants. Rejected as the decision because it governs crates inside a Cargo project only. It cannot express "this zip came from this release and someone accepted it". Recommended separately for any Rust crate this repo builds. |
| cargo-vet (Mozilla) | github.com/mozilla/cargo-vet | Real, records that third-party Rust dependencies were audited by a trusted entity, with importable audits. Philosophically the nearest neighbour to this ADR and the model for the ledger's shape. Rejected for the same scope reason: crates.io dependencies, not arbitrary artifacts. |
| pip-audit (PyPA + Trail of Bits) | github.com/pypa/pip-audit | Real, Apache-2.0, PyPA-maintained, audits environments and requirements files against the Python Packaging Advisory Database. Wired in as a `scan` backend. Irrelevant to this repo's own code, which is stdlib-only by design. |
| sigstore/cosign | github.com/sigstore/cosign | Real, Apache-2.0, 2.x stable; `cosign verify-blob` is exactly the artifact check wanted. Not rejected: it is the preferred signature backend. It is not the decision because it answers one of four properties and records nothing. |
| SLSA provenance | slsa.dev/spec/v1.0/levels | Real. Build L1 provenance exists and may be unsigned, L2 adds a hosted platform and signed provenance, L3 adds hardened isolation and inaccessible signing keys. Rejected as a gate requirement because it is a producer-side standard: this repo consumes artifacts and cannot make a vendor reach L2. It is used the other way round, as the vocabulary for what a recorded signature status means. |
| `gh attestation verify` | docs.github.com, artifact attestations | Real, verifies a downloaded binary against a Sigstore bundle, with an offline mode using `gh attestation download` plus `gh attestation trusted-root`. **This is the one cryptographic verifier already present on this machine**, measured below, so it is tried before cosign. |
| JFrog Artifactory + Xray | commercial | The thing being replaced. Rejected: a hosted binary repository with a per-seat licence, for a single-operator harness with no artifact publishing story. |
| Do nothing, keep refusing case by case | the status quo of 2026-07-30 | Rejected on the operator's argument, which is the whole reason this file exists. |

### What is actually installed here, measured 2026-07-30

```
gh present   cargo present   uv present   python present
cosign ABSENT   trivy ABSENT   syft ABSENT   grype ABSENT
osv-scanner ABSENT   pip-audit ABSENT
```

This is why the design refuses to depend on any of them. Every scanner is
optional and absence is recorded as `not-installed`, which aggregates to
`unavailable`, which is UNCOVERED and blocks adoption until somebody either
installs one or waives with an expiry. A design that assumed Trivy was present
would report clean on a machine where nothing ran.

It is also why `gh attestation` is the first signature path rather than cosign:
today it is the only one that works with no new install, which is a stronger
starting position than a better tool nobody has.

## Proposed `supply_chain` domain for quality-contract.json

Not applied by this ADR. `quality-contract.json` is deliberately untouched here
so the domain lands with the operator's decision on the waiver window rather than
this session's. Add under `domains`:

```json
"supply_chain": {
  "required": true,
  "cmd": "python tools/supply/verify.py verify-ledger && python tools/supply/verify.py selftest",
  "timeout": 300,
  "_note": "the provenance ledger for third-party artifacts is intact and its oracle passes. Rationale and the curl-pipe rule: docs/adr/0019-supply-chain-verification.md",
  "waived": {
    "until": "2026-08-30",
    "reason": "The ledger starts empty, so verify-ledger passes over nothing. It cannot yet answer the question that matters, which is whether every third-party binary already on this machine has a recorded hash: RTK and Oak are the two known ones and neither is in the ledger. Backfill those, then revoke this rather than renew it. The domain is declared now rather than later on purpose, because an undeclared domain reads as a solved problem."
  }
}
```

`gate.py` reads domains outside its fixed `DOMAINS` list (see the `extra` handling
in `cmd_run`), and an extra domain can add failures and never remove one, so
declaring this costs nothing structurally.

The `cmd` is deliberately weak in its first version. It proves the ledger is
unbroken and the oracle catches its planted defects. It does not prove every
installed third-party tool is recorded, because nothing on this machine currently
enumerates them, and a domain that claims a coverage it does not have is worse
than one that says what it checks.

## Consequences

Adoption becomes possible where it was refused, and every adoption leaves a row
naming the hash, the source, who decided, and what evidence they had. The cost is
two commands where an install guide prints one, and a `state/supply-chain.jsonl`
that starts out honestly empty and therefore proves nothing until it is
backfilled. The residual risk is unchanged for the case that matters most: a
vendor whose own build is compromised signs the bad bytes, and every check here
passes. This gate records provenance. It does not confer trust.
