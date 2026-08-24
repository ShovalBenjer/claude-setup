"""The shared result type every rule checker returns.

Item 2 of the 2026-08-24 worktree session (docs/taste.md, "global rule-
enforcement oracle"): six checkers (panel.py's 6 personas, slop_lint.py,
rules_sync.py, pointers.py, persona_audit.py, skills_sync.py) each grew their
own ad-hoc dict shape for "here is a problem I found". panel.py's dict has
keys persona/check/severity/file/line/why/snippet/source; slop_lint.py
returns bare (kind, fragment, line) tuples with no file field at all, since it
operates on one already-open file. A raw dict/tuple crossing the boundary
between a checker and whatever calls it is exactly the anti-pattern
boundary-contracts.md exists to name: typed DTOs, not passthrough.

Finding is that one contract. Every checker migrated under item 2 returns
list[Finding] from a function named check(...), never a bare dict or tuple.
Fields are a superset of what panel.py already emits, so migrating panel.py's
personas is additive (each dict key maps onto a named field) rather than a
rename that risks dropping information silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SEVERITIES = ("high", "medium", "low")


@dataclass(frozen=True, slots=True)
class Finding:
    """One rule violation, from one checker, at one location.

    `file` and `line` are the checker's best locator, not always both
    meaningful: a checker over free text (a session transcript, a response
    string) may have no filename, in which case `file` is the empty string
    rather than a placeholder that looks like a real path. `severity` is
    checked against SEVERITIES in __post_init__ rather than left free-form,
    the same fallback-to-medium discipline panel.py's validate_findings
    already applies to an external judge's output.
    """

    checker: str          # which check produced this, e.g. "slop_lint.banned_phrase"
    severity: str         # one of SEVERITIES; unrecognized values raise, not silently pass
    file: str             # locator path, "" if not file-scoped (transcript/text checks)
    line: int             # 1-indexed; 0 if not line-scoped
    why: str              # one-line reason a human reads
    snippet: str = ""     # the offending text, truncated by the checker if long
    source: str = "local" # "local" | "external" | future check origins
    meta: dict = field(default_factory=dict)  # checker-specific extras, never load-bearing

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"Finding.severity must be one of {SEVERITIES}, got {self.severity!r} "
                f"from checker {self.checker!r}. Unknown severities do not silently pass "
                f"as one of the recognized ones, that made the earlier ad-hoc dict shapes "
                f"harder to trust: an unrecognized value here should say so, immediately.")

    def as_dict(self) -> dict:
        """Bridge back to the dict shape panel.py's callers (cmd_run, emit_github_annotations)
        already expect, so migrating a checker does not require migrating every caller in
        the same commit. Field names match panel.py's existing dict keys where they overlap:
        persona -> checker is the one rename, because "persona" was never a fitting name for
        a non-persona checker like slop_lint."""
        return {
            "persona": self.checker, "check": self.checker, "severity": self.severity,
            "file": self.file, "line": self.line, "why": self.why,
            "snippet": self.snippet, "source": self.source,
        }
