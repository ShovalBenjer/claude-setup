"""Mutations for tools/review/panel.py.

panel.py owns the `review` domain of the ship gate, and it is one of the three
components (with gate.py and codemap.py) that had NO mutation spec while carrying
a required domain. The differentiator this estate claims, a gate that provably
fails when it should, was therefore unproven for the reviewer itself.

Two classes of guarantee are re-broken here.

The first is judge isolation, added 2026-07-27. An external judge that can read
the SKILL.md it is grading grades the description rather than the output, which is
the same failure as marking your own homework. The filter that prevents it is
invisible from outside: a filter that silently stopped working looks exactly like
one that had nothing to remove. That is precisely the shape of defect a mutation
spec exists to catch.

The second is the anti-hallucination and fail-closed machinery that was already
there: a finding citing a line the change did not add must be dropped and counted,
and credential-shaped content must stop transmission entirely. Both were live and
both were unfalsified.
"""

TARGET = "tools/review/panel.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- judge isolation ------------------------------------------------
    ("the judge sees skill definitions again",
     "a reviewer holding the SKILL.md confirms the description instead of testing "
     "the artifact, which is the whole reason the filter exists",
     'kept = [ln for ln in lines if not SKILL_DEFINITION.search(ln["file"])]',
     'kept = list(lines)'),

    ("the pattern stops matching a bare SKILL.md",
     "only the directory form would be caught, so a skill file at any other path "
     "reaches the judge",
     r'r"(?i)(^|/)SKILL\.md$|(^|/)(?:dot-claude|dot-codex|dot-agents|\.claude)/"',
     r'r"(?i)(^|/)(?:dot-claude|dot-codex|dot-agents|\.claude)/"'),

    ("the pattern stops covering the codex and agents trees",
     "the skills tree is triplicated across dot-claude, dot-codex and dot-agents; "
     "covering one of three is the same as covering none",
     r'r"(?i)(^|/)SKILL\.md$|(^|/)(?:dot-claude|dot-codex|dot-agents|\.claude)/"',
     r'r"(?i)(^|/)SKILL\.md$|(^|/)(?:dot-claude)/"'),

    ("blinding becomes silent",
     "the caller can no longer tell a filter that removed nothing from one that "
     "stopped working, which is the exact ambiguity this spec exists to remove",
     'return kept, len(lines) - len(kept)',
     'return kept, 0'),

    ("blinding swallows ordinary code too",
     "over-blinding is as bad as under-blinding: the judge would be sent an empty "
     "review and report no findings, which reads as a clean change",
     'kept = [ln for ln in lines if not SKILL_DEFINITION.search(ln["file"])]',
     'kept = [ln for ln in lines if False]'),

    # ---- fail-closed on credentials -------------------------------------
    ("credentials are scanned only AFTER blinding",
     "a key inside a SKILL.md would be filtered out of the scan and the leak check "
     "would pass on content that was never examined",
     '    leaks = redactable(lines)\n    if leaks:',
     '    leaks = redactable(judge_blind(lines)[0])\n    if leaks:'),

    ("a credential hit no longer withholds the content",
     "targets screen_for_send rather than run_external's branch, because after the "
     "2026-07-27 extraction the caller is safe by construction: screen_for_send "
     "returns an empty sendable list on a leak, so even a caller that ignored the "
     "leaks value transmits nothing. The real regression is here, where the "
     "withholding is decided",
     '    if leaks:\n        return [], 0, leaks',
     '    if False:\n        return [], 0, leaks'),

    # ---- anti-hallucination ---------------------------------------------
    ("findings citing a line the change did not add are kept",
     "an invented file:line is the normal failure mode of a model reviewer, and "
     "keeping them turns the reviewer into a generator of unactionable work",
     '        if (fl, li) not in valid:\n            dropped += 1\n            continue',
     '        if False:\n            dropped += 1\n            continue'),

    ("the dropped count stops being reported",
     "a reviewer that quietly discards half its own output while reporting the rest "
     "as clean is worse than one that reports nothing",
     'model, kept, dropped, str(model_note)[:300],',
     'model, kept, 0, str(model_note)[:300],'),

    ("the withheld count vanishes from the note",
     "blinding becomes invisible to the reader of the artifact, so a review of two "
     "lines out of forty reads exactly like a review of all forty",
     '"  {} skill/agent definition line(s) withheld from the judge.".format(blinded)\n'
     '            if blinded else ""))',
     '""))'),
]
