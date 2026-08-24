"""Project the annotated article onto a platform, and generate A/B variants.

The projector is platform-agnostic. It reads a platform profile (budget, shape,
hook angle, span order) and assembles a post by selecting spans to fill that
shape. It contains no per-platform strings; a new surface is a new dict in
platforms.py, not a change here.

A/B is built in: a platform with several hooks of its target angle yields one
variant per hook, each a genuinely different opener rather than a paraphrase,
so the test measures the thing that actually varies on social (the hook) while
holding the body constant.
"""
import hashlib

from platforms import platform as get_platform
from spans import ARTICLE, CANONICAL_URL, by_kind, hooks


def _fits(text, budget):
    return len(text) <= budget


def _stable_id(*parts):
    """Deterministic short id for a variant, so a test can be referred to
    across runs without a timestamp (which the workflow layer forbids anyway)."""
    h = hashlib.blake2b("||".join(parts).encode("utf-8"), digest_size=4)
    return h.hexdigest()


def _thread_from_spans(spans, budget):
    """Pack spans into thread posts, each under budget, never splitting a span
    across posts (a span is a complete thought)."""
    posts, cur = [], ""
    for s in spans:
        piece = s.text
        if len(piece) > budget:
            # a single span longer than the budget becomes its own post,
            # truncated with an ellipsis rather than silently dropped
            if cur:
                posts.append(cur)
                cur = ""
            posts.append(piece[: budget - 1].rstrip() + "…")
            continue
        candidate = piece if not cur else cur + "\n\n" + piece
        if _fits(candidate, budget):
            cur = candidate
        else:
            posts.append(cur)
            cur = piece
    if cur:
        posts.append(cur)
    return posts


def _select_body(pname, prof, hook, spans):
    """Spans for the body, in the platform's declared order, minus the hook and
    minus anything excluding this platform. One cta only: several link-backs in
    one post is noise, and on Bluesky a second bare URL suppresses the link
    card."""
    buckets = by_kind(spans)
    body, cta_used = [], False
    for kind in prof["order"]:
        if kind == "hook":
            continue  # the hook is chosen separately, per variant
        for s in buckets.get(kind, []):
            if pname in s.exclude:
                continue
            if s.kind == "cta":
                if cta_used:
                    continue
                cta_used = True
            body.append(s)
    return body


def project(pname, spans=ARTICLE, ab=1):
    """Return a list of A/B variants for one platform.

    The body is identical across a platform's variants, so a test isolates the
    hook, which is the thing that actually varies in performance on social.

    ab=1 (default): the single authoritative variant, leading with the
    platform's declared hook angle. ab>1: that variant plus up to ab-1
    alternatives from *different* angles, so the test compares real
    alternatives (cold-number vs wry vs in-media-res) rather than paraphrases of
    one angle. A hookless platform (Reddit) always returns its single variant.
    """
    prof = get_platform(pname)
    budget = prof["char_budget"]
    body_spans = _select_body(pname, prof, None, spans)

    # choose the hooks to test
    if prof["hook_angle"] is None:
        chosen_hooks = [None]
    else:
        allowed = [h for h in hooks(spans) if pname not in h.exclude]
        preferred = [h for h in allowed if h.angle == prof["hook_angle"]]
        preferred.sort(key=lambda h: -h.weight)
        # lead with the platform's angle, then fill with distinct other angles
        seen_angles = set()
        chosen_hooks = []
        for h in preferred + sorted(allowed, key=lambda h: -h.weight):
            if h.angle in seen_angles:
                continue
            seen_angles.add(h.angle)
            chosen_hooks.append(h)
            if len(chosen_hooks) >= ab:
                break
        chosen_hooks = chosen_hooks or [None]

    variants = []
    for hk in chosen_hooks:
        lead = hk.text if hk else ""
        if prof["thread"]:
            ordered = ([hk] if hk else []) + body_spans
            units = _thread_from_spans(ordered, budget)
        else:
            # single-unit surface: markdown body, hook as first line/heading
            parts = []
            if lead:
                parts.append(lead)
            for s in body_spans:
                parts.append(s.text)
            blob = "\n\n".join(parts)
            if not _fits(blob, budget):
                # trim from the tail, keeping the cta which is always last
                cta = next((s.text for s in reversed(body_spans)
                            if s.kind == "cta"), CANONICAL_URL)
                keep = []
                running = len(lead) + len(cta) + 8
                for s in body_spans:
                    if s.kind == "cta":
                        continue
                    if running + len(s.text) + 2 > budget:
                        break
                    keep.append(s.text)
                    running += len(s.text) + 2
                blob = "\n\n".join(([lead] if lead else []) + keep + [cta])
            units = [blob]

        variants.append({
            "platform": pname,
            "variant": _stable_id(pname, lead),
            "hook_angle": hk.angle if hk else "none",
            "units": units,
            "unit_count": len(units),
            "longest_unit": max(len(u) for u in units),
            "budget": budget,
            "over_budget": any(len(u) > budget for u in units),
            "canonical": CANONICAL_URL if prof["canonical"] else None,
            "note": prof["note"],
        })
    return variants


def render(pname, spans=ARTICLE, ab=1):
    prof = get_platform(pname)
    out = [f"### {pname}  (budget {prof['char_budget']}, "
           f"{'thread' if prof['thread'] else 'single'}, "
           f"hook: {prof['hook_angle'] or 'NONE'})",
           f"    {prof['note']}", ""]
    for v in project(pname, spans, ab=ab):
        flag = "OVER BUDGET" if v["over_budget"] else "ok"
        out.append(f"  -- variant {v['variant']} [angle: {v['hook_angle']}] "
                   f"{v['unit_count']} unit(s), longest {v['longest_unit']}/"
                   f"{v['budget']}  [{flag}]")
        for i, u in enumerate(v["units"], 1):
            prefix = f"  [{i}/{v['unit_count']}] " if v["unit_count"] > 1 else "  "
            for line in u.split("\n"):
                out.append(f"{prefix}{line}" if line else "")
                prefix = "      " if v["unit_count"] > 1 else "  "
        out.append("")
    return "\n".join(out)
