#!/usr/bin/env python3
"""Request one corrective turn when a response claims completion without evidence,
or stops by handing the decision back when nothing was blocking it.

Two checks, one hook, because both are the same failure at different ends of a turn:
a claim that outruns its evidence, and a stop that outruns its reason.

The HANDBACK check was added on 2026-07-29 from measurement, not intuition. Over one
week of transcripts, two independent passes with different definitions converged on
roughly 31 percent of the answers the operator reacted to (124/405 and 136/414) ending
in a question, a menu of options, or a named-but-untaken next step. The downstream cost
was measured too: 66 of 420 operator turns existed only to restart a motion that should
not have stopped, 30 of those were bare continuation tokens ("go", "carry on") after a
run with a MEDIAN OF FIVE TOOL CALLS, and 16 re-granted authority the session already
had. Roughly 940 minutes of the week were dead air waiting for a human to say continue.
Nothing was being denied: permission blocks had already fallen from 77 to 5 after the
move to bypassPermissions, and the five survivors are deny-listed credential reads.

So the thing stopping these runs was the assistant, and the operator's instruction was
to sort it rather than keep him connected for progress to happen.

WHY THIS IS SAFE TO BLOCK ON. Blocking here does not force an action; it forces one more
turn of thinking before the session may end. The loop guard is `stop_hook_active`, the
platform's own signal that a Stop hook already blocked this turn, so this can fire at
most once and can never trap a session.

THE ESCAPE HATCH, and why it is deliberately cheap to use and expensive to abuse. Some
stops are correct: an oracle edit, a destructive action, a publication, a genuinely
ambiguous requirement. A response may say so with an explicit marker naming the reason,
and it passes. That marker is trivially easy to emit, which is the point: the defence is
not that it is hard, it is that every use is written to a ledger, so a session that
reaches for it constantly produces a number rather than a vibe. This mirrors the
rejection-rate gap already recorded as RT-2, where the absence of a countable decision
is itself the finding.

The SLOP check was added on 2026-07-29 from measurement of the hook's own author.
tools/slop_lint.py has gated prose deliverables since ADR-0005, and it only ever sees
FILES. The response text is not a file, so the channel the operator reads continuously
had no oracle on it at all. Measured on one session (dfcabe1b): 28 assistant text turns,
17 carrying a spaced em or en dash used as a connector, 33 violations, 61 percent of
turns, while every markdown file written in that same session passed slop_lint. An
oracle that covers the cheapest surface to check and not the highest-traffic one is
measuring the wrong thing (lesson L-2026-07-29-g).

Code and data are stripped before matching, because the third panel.py waiver
(L-2026-07-29-d) was bought by a checker that could not tell code from prose about
code. A dash inside a fenced block, an inline span, a URL or a CLI flag is content the
operator asked to see verbatim, and flagging it would make quoting a command more
expensive than paraphrasing it, which is the wrong incentive twice over.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HEB = "֐-׿"

COMPLETION = re.compile(
    r"(?i)(?:\b(?:all done|done|fully (?:done|complete|working)|"
    r"production[- ]ready|verified|fixed|implemented(?: successfully)?|"
    r"everything works|it works|implementation is complete|"
    r"deployed successfully|is deployed|now live)\b|"
    r"(?<![" + HEB + r"])(?:הושלם|תוקן|אומת|מוכן לפרודקשן)"
    r"(?![" + HEB + r"])|"
    r"(?<![" + HEB + r"])(?:הקוד|זה|המימוש|המערכת)\s+"
    r"(?:עובד|עובדת)(?![" + HEB + r"]))"
)
EVIDENCE = re.compile(
    r"(?i)(?:\b(?:test(?:ed|s|ing)?|pytest|vitest|jest|cargo test|go test|"
    r"benchmark(?:ed|s|ing)?|lint(?:ed|ing)?|"
    r"typecheck(?:ed|ing)?|build(?:s|ing| passed)?|command|output|"
    r"passed|exit code|sha256|screenshot|oracle|property test|mutation|"
    r"residual risk|not run|unverified)\b|(?:בדיקה|בדיקות|נבדק|פקודה|פלט|סיכון))"
)

# Offers to continue rather than continuing. Matched against the CLOSING segment only:
# a question in the middle of a report is usually rhetorical or a quotation, while the
# same question as the last thing said is the turn ending on the operator's move.
HANDBACK = re.compile(
    r"(?i)(?:\b(?:want me to|shall i|should i|do you want|would you like|"
    r"let me know|your call|up to you|tell me which|which (?:one|would|do) you|"
    r"which would you prefer|if you(?:'d| would) like|say the word|"
    r"give me the go|await(?:ing)? your|waiting (?:for|on) your|"
    r"ready when you are)\b|"
    r"(?<![" + HEB + r"])(?:רוצה ש|שאמשיך|תגיד לי)(?![" + HEB + r"]))"
)

# A stop that names its own reason passes. The marker is explicit so that reaching for
# it is a decision that shows up in the ledger, not an accident of phrasing.
MARKER = re.compile(
    r"(?i)\b(?:NEEDS OPERATOR|NEEDS DECISION|BLOCKED ON OPERATOR|AWAITING APPROVAL)\b"
    r"|(?<![" + HEB + r"])דרוש אישור(?![" + HEB + r"])"
)

# Categories where stopping is correct under this repo's own authority rules, so a
# response discussing them is not nagged even without the explicit marker. Kept short on
# purpose: a broad list would let every stop find a word to hide behind.
LEGIT = re.compile(
    r"(?i)\b(?:requires? (?:your|operator) approval|needs? (?:your|operator) approval|"
    r"destructive|irreversible|force[- ]push|rotate the (?:key|token|credential)|"
    r"credential|secret|api key|production deploy(?:ment)?|publish(?:ing)? to|"
    r"permission denied|cannot proceed until|blocked by)\b"
)

# Identical to tools/slop_lint.py:21 on purpose. Two spellings of one rule would drift,
# and the operator would be corrected by one and not the other.
DASH = re.compile(r" [—–] ")

# Ritual acknowledgement of a correction, added 2026-07-30 at the operator's direction.
#
# The reasoning he gave, and it is the right one: an output style or a CLAUDE.md line is
# a REQUEST, and this pattern is trained in below the prompt layer, so instructions
# fight it rather than override it. The documented failure mode is a session running a
# style that bans celebratory openers and replying "You're absolutely right! I apologize
# for the verbose, celebratory formatting that goes against the Professional output
# style." A request cannot fix that. A gate can, because it does not ask.
#
# What is banned is the RITUAL, not the substance. Stating that a correction was correct
# and what changed because of it is required by the corrections rule and must stay
# possible: "the Stop hook fired because the tree had never been gated, so I ran it" is
# a fine sentence and matches nothing here. What matches is second-person praise,
# apology, and self-flagellation, which carry no information the operator did not
# already have.
RITUAL = re.compile(
    r"(?i)(?:"
    r"\byou(?:'re| are|r)\s+(?:absolutely\s+|completely\s+|totally\s+|quite\s+|so\s+)?"
    r"(?:right|correct)\b"
    r"|\bthat'?s\s+(?:absolutely\s+|completely\s+)?(?:right|correct|fair|a fair point)\b"
    r"|\b(?:good|great|fair|excellent|nice)\s+(?:catch|point|call|question|spot)\b"
    r"|\bmy apolog(?:y|ies)\b|\bi apologi[sz]e\b"
    r"|\bsorry(?:\s+(?:about|for)\s+(?:that|the))?\b"
    r"|\b(?:thanks|thank you)\s+for\s+(?:the\s+)?(?:catch|correction|pointing|flagging)"
    r"|\byou(?:'re| are)\s+right\s+to\b"
    r"|(?<![" + HEB + r"])(?:אתה צודק|סליחה|מצטער|צודק לגמרי)(?![" + HEB + r"])"
    r")"
)

# Evaluative openers. Anchored to the start of a line so that "the merge is perfect for
# this" is untouched while a paragraph opening on "Perfect." is caught. Case-sensitive
# on the capital for the same reason: mid-sentence use is ordinary English, and a
# sentence-initial bare adjective about the operator's input is the ritual.
RITUAL_OPENER = re.compile(
    r"^\s*(?:Perfect|Great|Excellent|Amazing|Wonderful|Fantastic|Awesome|Brilliant|"
    r"Absolutely|Certainly|Indeed|Nice|Exactly|Spot on|Good news)\b[\s!.,:;]",
    re.MULTILINE,
)

# Stripped before DASH runs, in this order: fenced blocks, inline spans, URLs, then
# anything that looks like a shell flag. See the module docstring for why.
FENCE = re.compile(r"```.*?```", re.DOTALL)
INLINE = re.compile(r"`[^`\n]*`")
URL = re.compile(r"https?://\S+")

LOG = Path(
    os.environ.get("CLAUDE_OS_DIR", str(Path.home() / "claude-setup"))
) / "state" / "handback-log.jsonl"

REASONS = {
    "completion_without_evidence": (
        "Evidence check: the response makes a strong completion or quality claim "
        "without naming an executable check. Calibrate the claim and state what was "
        "tested, what was not tested, and residual risk."
    ),
    "handback_without_reason": (
        "Follow-through check: this turn ends by handing the decision back, and nothing "
        "in it names a blocker, a required approval, or a destructive or irreversible "
        "action. Measured cost of this pattern over the last week: 66 operator turns "
        "spent only on restarting work that had stopped for no reason, and about 940 "
        "minutes of waiting. Do not re-ask. Take the decision you were about to hand "
        "over, state the assumption it rests on, and carry on with the work. If the stop "
        "is genuinely correct, say so with an explicit 'NEEDS OPERATOR: <reason>' naming "
        "what only the operator can decide and why nobody else can."
    ),
    "ritual_acknowledgement": (
        "Ritual check: this response acknowledges a correction instead of just acting on "
        "it, or opens on an evaluative adjective about the operator's input. Both carry "
        "no information he does not already have, and he asked for this to be enforced "
        "rather than requested because the pattern is trained in below the prompt layer "
        "and instructions only reduce it. Delete the acknowledgement and the opener. "
        "State what changed and what the new state is. Saying that a correction was "
        "CORRECT and what it altered is fine and is required by the corrections rule; "
        "what is banned is second-person praise, apology, and self-criticism, plus "
        "sentence-initial 'Perfect', 'Great', 'Excellent', 'Absolutely' and their kin."
    ),
    "slop_dash": (
        "Writing rule: this response uses a spaced em or en dash as a connector, which "
        "tools/slop_lint.py fails on for every prose file in this repo and which the "
        "operator has corrected directly. The response channel is held to the same rule "
        "as the files. Rewrite the offending sentences using a comma, a colon, a "
        "semicolon, parentheses, or two sentences. Dashes inside code spans, fenced "
        "blocks and URLs are not counted, so quoting a command verbatim is always safe."
    ),
}


def prose_only(text: str) -> str:
    """Return the text with code, data and URLs removed.

    Order matters: fences first, because an inline-span pattern would otherwise chew
    through the middle of a fenced block and leave its delimiters behind.
    """
    stripped = FENCE.sub(" ", text)
    stripped = INLINE.sub(" ", stripped)
    return URL.sub(" ", stripped)


def assistant_text(payload: dict[str, Any]) -> str:
    for key in ("last_assistant_message", "assistant_message", "response", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for nested in ("text", "content"):
                item = value.get(nested)
                if isinstance(item, str):
                    return item
    return ""


def closing_segment(text: str, limit: int = 600) -> str:
    """The last paragraph, capped.

    Scoped rather than whole-text because the signal is where the turn ENDS. A report
    that asks a question in its third section and then goes on to do the work has not
    handed anything back; a report whose final sentence is the question has.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    tail = blocks[-1] if blocks else ""
    return tail[-limit:]


def verdict(text: str) -> tuple[str, str]:
    """Return (action, reason_key), where action is "block" or "pass"."""
    if COMPLETION.search(text) and not EVIDENCE.search(text):
        return "block", "completion_without_evidence"

    tail = closing_segment(text)
    if HANDBACK.search(tail) or tail.rstrip().endswith("?"):
        if MARKER.search(text):
            return "pass", "handback_with_marker"
        if LEGIT.search(text):
            return "pass", "handback_legitimate_category"
        return "block", "handback_without_reason"

    # Ritual before dash. Both cost a reread rather than minutes, but the operator has
    # corrected the ritual directly and it is the one he asked to be made enforceable
    # rather than requested, so it outranks the punctuation rule.
    prose = prose_only(text)
    if RITUAL.search(prose) or RITUAL_OPENER.search(prose):
        return "block", "ritual_acknowledgement"

    # Last, so a turn that both hands back AND breaks the writing rule is told about the
    # handback, which costs the operator minutes, rather than the dash, which costs him
    # a reread. Ordering here is a claim about which failure is worse, and it is.
    if DASH.search(prose):
        return "block", "slop_dash"

    return "pass", "clean"


def record(reason_key: str, action: str, session: str) -> None:
    """Append one row per stop, so the rate is measurable rather than argued about.

    Every path is logged, including "clean", because a gate's false-positive rate cannot
    be computed from the times it fired alone. Failure to write is swallowed: a hook that
    dies on a full disk must not take the session with it.

    The except is deliberately broad, and that is not laziness. It was narrowed to
    OSError first, and a test passing a path with an embedded null byte showed
    pathlib raising ValueError straight through it, which would have made every turn
    end in a traceback instead of a verdict. Telemetry is the least important thing
    this function does, so nothing it can do is worth losing the decision for.
    """
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session": session,
            "action": action,
            "reason": reason_key,
        }
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    except Exception:  # noqa: BLE001 - see docstring
        pass


def main() -> int:
    try:
        payload: Any = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError
        text = assistant_text(payload)
        stop_hook_active = payload.get("stop_hook_active") is True
        session = str(payload.get("session_id", ""))[:8]
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        print("{}")
        return 0

    action, reason_key = verdict(text)

    # The loop guard. One block per turn, always. A second pass through this hook in the
    # same turn means it already spoke, and repeating itself would trap the session.
    if stop_hook_active:
        action, reason_key = "pass", "loop_guard"

    record(reason_key, action, session)

    if action == "block":
        print(json.dumps({"decision": "block", "reason": REASONS[reason_key]}))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
