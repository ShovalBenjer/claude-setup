"""Harness logic behind the Claude/Codex session hooks.

Pure, testable functions extracted from the bash-embedded-python hooks
(prompt-router.sh, self-improve.py) so the logic that shapes every session
is regression-guarded instead of untested glue. The hooks become thin shims
that import from here.
"""
