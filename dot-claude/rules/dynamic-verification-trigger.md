# When a message earns a search before a reply earns trust

Global rule. Applies to every project and session. Companion to
`out-of-distribution.md` (anchor to real references), `calibrated-claims.md`
(evidence class on every claim), and `output-channel-routing.md` (which
channel carries the reply, a distinct question from whether to verify
first). Connector selection once verification is needed still routes
through the Connector routing section of `gastown-company-registry.md`
(Exa for technical search, Context7 for library docs, alphaXiv for papers,
Wolfram for math). This file is the missing layer above that: WHEN to fire
a search at all, not which tool to use once the decision is made.

## Why this exists

2026-08-18/19, one session, three consecutive messages built the same way:
real technical vocabulary from a real field (octonion algebra, AdS/CFT,
cellular sheaves; then thermodynamic computing and OTOCs; then hyperbolic
embeddings and sheaf-based multi-agent conflict detection) wired into a
composed architecture claim, several attributed to named researchers by
name. Ad hoc, case-by-case judgment caught two of three as citation-stacked
theater (invented attributions to Ethan Perez, Sewon Min, Jason Wei, Neel
Nanda; an unsupported OTOC-for-transformer-coherence claim) and correctly
cleared the third (hyperbolic retrieval and sheaf-based conflict detection
both checked out against 2025-2026 papers). The catch rate depended entirely
on the assistant noticing, per message, that something was checkable. That
is not a standing rule, it is a habit that can lapse on the next message
with the same shape. This file turns the habit into a named trigger.

## The rule

Before agreeing with, building from, or extending a claim in a message,
check whether it trips one of these conditions. Any one is enough to
require a search first:

1. **Named-attribution claim.** The message credits a specific named
   person, lab, or paper with a specific finding ("X and team proved
   Y", "researchers at Z showed W"). Verify the person is real AND that
   the specific claim attributed to them is the claim they actually made,
   not an adjacent finding wearing their name for authority. Two failure
   modes are both real and both count: a fabricated person, and a real
   person with a false claim stapled to them.
2. **Asserted product, benchmark, or tool existence.** The message states
   that a library, chip, service, or measured benchmark result exists,
   without a link, version, or number attached. "There's a Triton kernel
   for this" and "it achieves 29% improvement" both need a source before
   they enter a plan.
3. **Composed architecture with more edges than sources.** The message
   proposes that N real technical primitives (each individually real and
   checkable) compose into a working system, and the composition itself
   (the edges, not the nodes) is asserted rather than shown. Check the
   nodes individually; treat the edges as unverified until at least one
   is traced to a real working example or a paper that actually connects
   them, not just cites them adjacently.
4. **A correction or retraction offered on its own authority.** A message
   that concedes an earlier claim was wrong and offers a corrected version
   is not automatically trustworthy just because it self-identifies the
   failure mode by name (as this file's own origin incident shows: the
   correcting message was right on two of three sub-claims and still
   needed the same check as the original). Self-correction earns a fresh
   check, not a pass.
5. **A claim that would change what gets built or shipped if wrong.**
   Scale the bar to the stakes. A claim that only affects a passing reply
   can go unchecked if it fails none of 1 to 4. A claim about to become a
   file, a merged PR, a skill, or a plan item gets checked even if it
   narrowly avoids 1 to 4, because the cost of being wrong just changed.

## What "check" means here

Not a vague sanity pass. Run an actual search (WebSearch, Exa, alphaXiv,
Context7, per the registry's connector routing) for each checkable
sub-claim, separately when the claims are separable (do not let one real
citation vouch for three fabricated ones in the same message). Report per
claim what was found: confirmed with a source, found-but-different-claim
(the misattribution case), or not found. `read-whole-before-reasoning.md`
still applies to whatever the search returns: read the source, do not
draft a verdict from a search-snippet summary alone when the claim is
about to be relied on.

## What does not need this

Routine technical questions with a well-known, low-stakes answer (library
API syntax, a shell command, a repo-local fact checkable by reading the
repo). Context7 and repo reads already cover those; this file is about
claims arriving from outside the immediate technical task, dressed in
enough real vocabulary to be persuasive without being sourced.

## Enforcement

There is no automated gate for this one; it is a judgment trigger, not a
lint rule. The check on whether it is working: does a session's reply to
a citation-heavy or architecture-heavy message name, per claim, whether it
was searched and what was found, or does it just proceed. A reply that
agrees with or builds on an unverified named-attribution or composed-
architecture claim without saying so is the failure this file exists to
catch.
