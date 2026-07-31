"""Declarative platform profiles: budget, shape, and hook strategy.

Each platform says what shape it rewards and which span kinds fill it, in
priority order. The projector reads this; nothing about a platform is hardcoded
in the projector itself, so adding a surface is adding a dict here.

Hook strategy is per platform on purpose. The same opener everywhere is the tell
that a bot posted it, so each platform names the hook *angle* it wants and the
projector picks a hook of that angle.
"""

# char_budget: hard ceiling for a single unit (a post, or one item of a thread).
# thread: whether the platform supports a sequence of units.
# markdown: whether the body renders markdown.
# hook_angle: which hook angle to lead with (matches Span.angle).
# order: span kinds to draw from, in priority order, to fill the body.
# canonical: whether this surface should carry a rel=canonical / link-back.
# note: human guidance the projector prints alongside the draft.

PLATFORMS = {
    "x": {
        "char_budget": 280,
        "thread": True,
        "markdown": False,
        "hook_angle": "cold-number",
        "order": ["hook", "reversal", "number", "failure", "punchline", "cta"],
        "canonical": True,
        "hashtags_max": 1,
        "note": "First post carries the claim, not the setup. Withhold the "
                "subject to buy the second post. One hashtag at most, or none.",
    },
    "bluesky": {
        "char_budget": 300,
        "thread": True,
        "markdown": False,
        "hook_angle": "wry",
        "order": ["hook", "reversal", "number", "punchline", "cta"],
        "canonical": True,
        "hashtags_max": 0,
        "note": "Wry, conversational. Link card renders, so do not also paste "
                "the bare URL in the same post as the link.",
    },
    "devto": {
        "char_budget": 25000,
        "thread": False,
        "markdown": True,
        "hook_angle": "problem",
        "order": ["hook", "claim", "method", "artifact", "failure", "number",
                  "cta"],
        "canonical": True,
        "note": "Problem statement up front. canonical_url MUST point at the "
                "pages.dev article. Tags: at most 4, lowercase.",
    },
    "medium": {
        "char_budget": 25000,
        "thread": False,
        "markdown": True,
        "hook_angle": "in-media-res",
        "order": ["hook", "reversal", "claim", "failure", "number", "cta"],
        "canonical": True,
        "note": "Import tool only (writer API retired); it sets canonical "
                "automatically. Open in-media-res, on the moment of the wrong "
                "answer, not the setup.",
    },
    "reddit": {
        "char_budget": 40000,
        "thread": False,
        "markdown": True,
        "hook_angle": None,   # no hook: any hook reads as self-promotion
        "order": ["claim", "method", "number", "failure", "artifact", "cta"],
        "canonical": True,
        "note": "NO hook. State the artifact plainly and invite critique. "
                "r/LocalLLaMA wants the decryption + cost; r/ClaudeAI wants the "
                "failure taxonomy. Post only AFTER dev.to lands. Read the "
                "subreddit self-promotion rule the same day.",
    },
    "github_readme": {
        "char_budget": 4000,
        "thread": False,
        "markdown": True,
        "hook_angle": "problem",
        "order": ["claim", "punchline", "cta"],
        "canonical": True,
        "note": "What it is and the link, not the narrative. Every command "
                "shown must have been run.",
    },
    "linkedin": {
        "char_budget": 2800,
        "thread": False,
        "markdown": False,
        "hook_angle": "problem",
        "order": ["claim", "failure", "number", "cta"],
        "canonical": True,
        "hashtags_max": 3,
        "note": "Methodology, not story: withheld ground truth, external gate, "
                "cost accounting. Frame as an evaluation protocol. Skip if it "
                "reads as bragging.",
    },
}


def platform(name):
    if name not in PLATFORMS:
        raise KeyError(f"unknown platform {name!r}; known: {sorted(PLATFORMS)}")
    return PLATFORMS[name]
