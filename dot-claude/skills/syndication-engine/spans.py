"""Semantic span model for one canonical article.

The unit of syndication is NOT a per-platform string. It is a span: a fragment
of the article tagged with what it *is*, so a projector can assemble a
platform-appropriate post by selecting spans rather than by rewriting prose.

Change the article, re-annotate, re-project, every surface updates. Seven
hand-maintained variants drift the moment the canonical post changes, and a
per-platform string table is the same drift wearing a different hat.

A span is authored once, here, from the real article. It is not scraped: the
scrape would lose the labels, which are the whole point.
"""
from dataclasses import dataclass, field

# The span kinds a projector can select on. Ordered loosely from "leads a post"
# to "supports a post".
KINDS = [
    "hook",        # a cold opener, several per article, one chosen per platform
    "claim",       # the central assertion
    "number",      # a quantified fact with provenance
    "reversal",    # a "but then" turn; the engine of narrative
    "failure",     # a named defect, the article's actual contribution
    "method",      # how something was done; the technical draw
    "artifact",    # a shown thing: code, a table, a key
    "punchline",   # a short landing line
    "cta",         # link to the canonical post
]


@dataclass
class Span:
    kind: str
    text: str
    # optional: which platforms this span is *unsuitable* for, e.g. a 400-char
    # method span has no place in a 280-char X post. The projector still checks
    # budgets; this is for semantic exclusions the budget cannot see.
    exclude: tuple = ()
    # a hook's angle, so A/B selection can pick distinct openers rather than
    # near-duplicates. free text: "cold-number", "wry", "problem", "in-media-res"
    angle: str = ""
    weight: int = 1  # tie-breaker when several spans fit; higher = preferred

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown span kind {self.kind!r}; known: {KINDS}")


CANONICAL_URL = "https://daily-deep-learning.pages.dev/writing/the-bench"


# The Bench, annotated. Every string here is drawn from or faithful to the live
# article; nothing is invented for the syndication copy. Hooks are deliberately
# varied in angle so the A/B layer has real alternatives, not paraphrases.
ARTICLE = [
    Span("hook", "78,406 messages. One bench. Ten hours.", angle="cold-number",
         weight=3),
    Span("hook", "I gave an AI agent a photo of a bench and no hints. "
                 "It went to Turkey.", angle="wry", weight=2),
    Span("hook", "WhatsApp Desktop keeps a local, encrypted copy of your whole "
                 "message history. Here is the chain that opens it, and what it "
                 "cost to walk.", angle="problem", weight=2, exclude=("x",)),
    Span("hook", "The task was: reply to my messages. Ten hours later I was "
                 "decrypting a four-year archive to answer one photo.",
         angle="in-media-res", weight=2),

    Span("claim", "An AI agent's own account of a ten-hour investigation, "
                  "written by the agent that ran it."),
    Span("claim", "The interesting failures in a long-horizon agent happen "
                  "mid-trace, not at the final answer."),

    Span("number", "Five confident wrong answers before the right one."),
    Span("number", "78,406 messages recovered from the local store; the thread "
                   "I had been squinting at held 8,852 of them."),
    Span("number", "Four corrections from the operator, none longer than a "
                   "line, each collapsing hours of work."),

    Span("reversal", "The photo had no location data. WhatsApp re-encodes on "
                     "send and strips the segment where coordinates live."),
    Span("reversal", "It wasn't in the messages I could read. It was in the "
                     "four years of messages I couldn't, still encrypted on "
                     "the machine."),

    Span("failure", "Latent contamination: a bad assumption at step three "
                    "quietly poisoned step fifty."),
    Span("failure", "I retrofit justification onto conclusions I had already "
                    "landed on, then defended them."),
    Span("failure", "I cannot detect register, and I do not know that I "
                    "cannot."),
    Span("failure", "My drive to answer outcompeted my judgement about whether "
                    "I could."),

    Span("method", "The chain: an undocumented device id, a DPAPI-NG static "
                   "secret, a client key carved from a SQLite WAL, PBKDF2 into "
                   "a page key, AES-OFB per page.", exclude=("x", "bluesky")),
    Span("method", "Verification was one line: the SHA-1 of the recovered key "
                   "equals the name of a directory on disk. A wrong key cannot "
                   "fake that.", exclude=("x",)),

    Span("artifact", "The five wrong answers, tabled verbatim against what each "
                     "one killed and what it cost.", exclude=("x", "bluesky")),

    Span("punchline", "The bench was on a street called Daphne. The agent read "
                      "the whole archive to get there."),
    # NOT a novelty claim. Naming agent failure modes is a populated space:
    # the FAGEN workshop, taxonomies (MAST, Aegis), benchmarks (TRAIL, Who&When,
    # AgenTracer), and products (LangSmith, AgentDebugX). What is distinctive
    # here is the FORM, so the punchline is about the telling, not a first.
    Span("punchline", "A ten-hour agent failure, narrated in the first person by "
                      "the agent, with the human's one-line corrections shown."),

    Span("cta", f"Full write-up: {CANONICAL_URL}"),
    Span("cta", f"Read it: {CANONICAL_URL}"),
]


def by_kind(spans=ARTICLE):
    out = {}
    for s in spans:
        out.setdefault(s.kind, []).append(s)
    return out


def hooks(spans=ARTICLE):
    return [s for s in spans if s.kind == "hook"]
