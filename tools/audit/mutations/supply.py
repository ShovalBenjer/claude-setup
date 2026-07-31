"""Mutations for tools/supply/verify.py.

verify.py is the file in this estate with the most to lose from an unfalsified
check. It GATES ADOPTION of third-party software: every other tool here reports
on the repository, and this one decides whether foreign bytes are allowed to be
called adopted. It arrived on 2026-07-30 with a selftest and no mutation spec,
so by this repo's own four-layer standard (contract, oracle, selftest, mutation
that turns the selftest red) the only layer missing was the one that proves the
selftest can go red at all. A refusal that has never been observed refusing and
a refusal that quietly stopped refusing are indistinguishable from outside.

The guarantees re-broken here are the four sentences the module docstring makes
in its own voice, in the order it makes them.

  "an artifact cannot be marked adopted without a recorded sha256 of the exact
   bytes that were installed" -- and it is the one property with no waiver, so
   both the removal of the check and the invention of an escape hatch for it are
   mutated separately. They fail differently and only one of them looks like a
   feature request.

  "a property counts as satisfied when a command exited zero or a named value
   exists, and anything else is UNCOVERED, and UNCOVERED refuses" -- so
   `unavailable`, which is the literal state of this machine (no scanner
   installed, cosign absent), must never start counting as a pass. That is the
   single most likely regression here, because making it pass would make the
   tool stop complaining, and a tool that stops complaining looks fixed.

  "An expired waiver is a refusal, not a skip" -- inherited verbatim from
  gate.py, and re-broken the same three ways: the date comparison itself, the
  liveness test at the call site, and a waiver with no expiry at all.

  "It makes an EDIT visible, which is the realistic failure: a row quietly
   changed after the fact so an artifact reads as adopted on evidence it never
   had." A chain that no longer notices an edited row still prints "ledger
   intact", which is worse than having no chain, because the sentence is now a
   false one rather than an absent one.

The last mutation is about ordering rather than about a rule: a re-scan that
found something must beat an earlier clean result. First-hit-wins is the
plausible-looking implementation, it passes any test written with one scan row
in it, and it lets a fixed-then-broken artifact be adopted on the evidence of
the run before last.
"""

TARGET = "tools/supply/verify.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- the one refusal with no escape hatch ---------------------------
    ("the recorded-hash requirement stops being checked at all",
     "the single rule this file exists to enforce. Without it the ledger records "
     "signatures and scan verdicts about no particular bytes, and `adopted` "
     "becomes a note that somebody once felt good about a download",
     '    if not state["sha256"] or not HEX64.match(str(state["sha256"])):',
     '    if False:'),

    ("the hash requirement becomes waivable like the other two",
     "the docstring calls this the one property with no waiver. A waiver here is "
     "not a relaxed rule, it is the deletion of the rule: `--property sha256 "
     "--until 2099-01-01` would adopt an artifact nobody hashed, with a full "
     "audit trail saying it was fine",
     '    if not state["sha256"] or not HEX64.match(str(state["sha256"])):',
     '    if any(r.get("event") == "waiver" and r.get("property") == "sha256"\n'
     '           and not expired(r.get("until", "")) for r in rows):\n'
     '        pass\n'
     '    elif not state["sha256"] or not HEX64.match(str(state["sha256"])):'),

    # ---- UNCOVERED is not a pass ----------------------------------------
    ("`unavailable` starts counting as a verified signature",
     "cosign is not installed on this machine, so `unavailable` is the ACTUAL "
     "state of most artifacts here. Accepting it converts 'no verifier could run' "
     "into 'the signature checked out', which is the exact substitution the "
     "UNCOVERED rule was written to forbid",
     '    check("signature", ("verified",),',
     '    check("signature", ("verified", "unavailable", "unchecked"),'),

    ("`unavailable` starts counting as a clean scan",
     "none of the five known scanners is installed here. This mutation makes "
     "'nothing measured these bytes' report as 'these bytes were measured and are "
     "clean', which is the one sentence the scan machinery exists to keep apart",
     '    check("scan", ("clean", "findings-accepted"),',
     '    check("scan", ("clean", "findings-accepted", "unavailable"),'),

    ("scanner findings are accepted without anyone accepting them",
     "`findings` and `findings-accepted` differ only in that a human typed the "
     "second one. Collapsing them removes the human from a supply-chain decision "
     "while leaving the word `accepted` in the ledger",
     '    check("scan", ("clean", "findings-accepted"),',
     '    check("scan", ("clean", "findings-accepted", "findings"),'),

    # ---- waivers expire -------------------------------------------------
    ("no waiver ever expires",
     "gate.py's 'a permanent waiver is just a disabled check with better manners', "
     "applied to third-party code. The waiver written to unblock one install on a "
     "Thursday silently covers every artifact after it, forever",
     '        return datetime.date.fromisoformat(until) < datetime.date.today()',
     '        return False'),

    ("an expired waiver is honoured at the call site",
     "leaves expired() correct and stops asking it, which is the version that "
     "survives review: the expiry logic is still there, still tested in isolation, "
     "and no longer consulted by the only caller that matters",
     '        if w and w.get("until") and not expired(w["until"]):',
     '        if w and w.get("until"):'),

    ("a waiver with no expiry date is honoured",
     "an undated waiver is the same permanent disablement as an unexpiring one, "
     "reached by omission rather than by a far-future date, so it is the one a "
     "reviewer does not see in the diff",
     '        if w and w.get("until") and not expired(w["until"]):',
     '        if w and (not w.get("until") or not expired(w["until"])):'),

    # ---- the chain ------------------------------------------------------
    ("an edited row no longer breaks the chain",
     "the only thing the hash chain is for. A row changed after the fact so an "
     "artifact reads as adopted on evidence it never had is the realistic attack "
     "on an append-only evidence file, and verify-ledger would keep printing "
     "'ledger intact: chain unbroken from genesis' over it",
     '        if r.get("hash") != want:',
     '        if False:'),

    # ---- ordering -------------------------------------------------------
    ("the most FAVOURABLE scan verdict wins instead of the most recent",
     "an artifact scanned clean, then rescanned after an advisory landed, would "
     "adopt on the older result. First-hit-wins passes every test written with a "
     "single scan row and is wrong precisely when the ledger has history, which is "
     "the only time anyone reads it",
     '        if r.get("event") == "scan":\n            state["scan"] = r.get("status", "unscanned")',
     '        if r.get("event") == "scan" and state["scan"] == "unscanned":\n'
     '            state["scan"] = r.get("status", "unscanned")'),
]
