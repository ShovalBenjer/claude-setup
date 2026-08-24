"""Tests for company.py: Layer 4 persona grading (grade -> PIP -> bench).

The company layer reads graded variants from the archive and turns them into a per-persona
scorecard and roster status. The two guardrails under test: failure is penalized harder than
success is rewarded (asymmetric earned trust), and no persona is demoted on noise (a significance
guard: below the minimum sample count, status stays active regardless of a bad streak).
"""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from intent_control_plane.company import persona_scorecard, roster_status, trust_score


def _v(persona: str, verdict: str, score: float = 0.5, cost: int = 100) -> dict:
    return {"persona": persona, "verdict": verdict, "score": score, "cost_tokens": cost}


def test_trust_asymmetric_penalizes_failure_more_than_success():
    # start 50, one kept (+5) then one rejected (-15) nets below the start: failure weighs more.
    assert trust_score(["kept", "rejected"]) == 40.0
    assert trust_score(["kept"]) == 55.0
    assert trust_score(["rejected"]) == 35.0


def test_trust_score_clamps():
    assert trust_score(["rejected"] * 20) == 0.0
    assert trust_score(["kept"] * 20) == 100.0


def test_trust_score_neutral_verdict_is_not_a_failure():
    # audit #11: 'scored' is a live spawn screened-but-unjudged; it carries no signal and must not
    # tank trust the way a real 'rejected' does, or every un-judged spawn silently sinks the persona.
    assert trust_score(["scored"]) == 50.0
    assert trust_score(["kept", "scored"]) == 55.0
    assert trust_score(["rejected-guardrail"]) == 35.0  # a real guardrail rejection still penalizes


def test_persona_scorecard_aggregates_per_persona():
    variants = [
        _v("Engineering Firm", "kept", 0.8),
        _v("Engineering Firm", "rejected", 0.2),
        _v("Product Studio", "kept", 0.9),
    ]
    card = persona_scorecard(variants)
    assert card["Engineering Firm"]["n"] == 2
    assert card["Engineering Firm"]["kept"] == 1
    assert card["Engineering Firm"]["keep_rate"] == 0.5
    assert card["Product Studio"]["keep_rate"] == 1.0


def test_roster_status_never_demotes_on_insufficient_samples():
    # 3 straight rejections, but below min_samples -> stays active (never fire on noise).
    variants = [_v("New Hire", "rejected") for _ in range(3)]
    status = roster_status(persona_scorecard(variants), min_samples=5)
    assert status["New Hire"] == "active"


def test_roster_status_pip_and_bench_thresholds():
    benched = [_v("Weak", "rejected") for _ in range(8)] + [_v("Weak", "kept") for _ in range(0)]
    pip = [_v("Middling", "kept") for _ in range(3)] + [_v("Middling", "rejected") for _ in range(5)]
    good = [_v("Strong", "kept") for _ in range(7)] + [_v("Strong", "rejected") for _ in range(1)]
    card = persona_scorecard(benched + pip + good)
    status = roster_status(card, min_samples=5, pip_below=0.5, fire_below=0.25)
    assert status["Weak"] == "benched"    # keep_rate 0.0 < 0.25
    assert status["Middling"] == "pip"    # keep_rate 0.375 in [0.25, 0.5)
    assert status["Strong"] == "active"   # keep_rate 0.875 >= 0.5


@given(
    persona=st.sampled_from(["A", "B", "C"]),
    verdicts=st.lists(st.sampled_from(["kept", "rejected"]), min_size=1, max_size=30),
)
def test_roster_status_always_valid(persona, verdicts):
    variants = [_v(persona, v) for v in verdicts]
    status = roster_status(persona_scorecard(variants))
    assert status[persona] in {"active", "pip", "benched"}
