#!/usr/bin/env python3
"""Round-trip fidelity oracle for a compressed inter-agent channel.

Why this exists
---------------
The 2026 latent-communication papers all report a token saving and a task score.
None of them ships a way to tell whether a given channel, on a given pair of
models, actually carried the content. arXiv 2607.26773 (2026-07-29) states the
gap directly: greater representational capacity does not establish that a channel
communicates. arXiv 2606.28958 shows the worse case, an agent whose visible
message looks benign while its real state travels underneath.

So the failure mode is not "the channel is slow". It is "the channel dropped the
one paragraph that mattered and the receiver produced fluent text anyway". Task
score cannot see that, because a plausible answer scores like a correct one on
anything but a probe whose answer is only in the dropped paragraph.

What is measured
----------------
For each document, a set of probes. A probe is a question plus the exact answer
token, and it is only admissible if the answer appears in the document and the
question cannot be answered from general knowledge. Two runs:

    baseline = accuracy(probes | plain document)
    channel  = accuracy(probes | document after compress -> transmit -> read)

    fidelity = channel / baseline        (1.0 means the channel lost nothing
                                          the receiver could already use)

Reporting `channel` alone would punish a channel for probes the receiver fails
even with the full text. Normalising against baseline is the same convention
2606.19857 uses for semantic fidelity, and it keeps a weak receiver from being
mistaken for a lossy channel.

A channel passes only at or above its declared floor. Unmeasurable is not a pass:
a channel whose probes could not be run exits non-zero, because otherwise the
cheapest way to go green is to break the probe runner.

Channels
--------
`identity`  transmits the document unchanged. Fidelity must be 1.0. This is the
            anchor: if identity fails, the harness is broken, not the channel.
`truncate`  keeps the head and drops the tail. Deliberately lossy, and it exists
            so `selftest` can prove this file's own PASS can turn red. A gate
            that has never gone red is a gate nobody has tested.
`command`   shells out to a real peer. This is how a live leg is wired; the
            compressor and reader are external processes, so no model is
            simulated here.

Usage
-----
  roundtrip.py run --channel identity
  roundtrip.py run --channel truncate --floor 0.9        # expected to fail
  roundtrip.py run --channel command --compress "..." --read "..."
  roundtrip.py run --json
  roundtrip.py selftest
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field

FLOOR_DEFAULT = 0.95


@dataclass
class Probe:
    question: str
    answer: str


@dataclass
class Case:
    name: str
    document: str
    probes: list[Probe] = field(default_factory=list)

    def admissible(self) -> list[str]:
        """Probes whose answer is not actually in the document are not probes."""
        return [p.question for p in self.probes if p.answer.lower() not in self.document.lower()]


def _fixture() -> list[Case]:
    """Documents whose facts are arbitrary on purpose.

    Real-world names would let a receiver answer from pretraining, which would
    inflate every channel including a lossy one. Each answer sits at a known
    position so `truncate` provably drops some of them.
    """
    return [
        Case(
            name="deploy-note",
            document=(
                "The staging cluster is named quirt-14. Its owner of record is desk 6B. "
                "The rollback token for the 2026-07 window is TK-99420. "
                "Cold start was measured at 812 ms on the third attempt. "
                "The tail of this note records that the fallback region is zz-south-2."
            ),
            probes=[
                Probe("What is the staging cluster named?", "quirt-14"),
                Probe("What is the rollback token?", "TK-99420"),
                Probe("What is the fallback region?", "zz-south-2"),
            ],
        ),
        Case(
            name="incident-log",
            document=(
                "Incident 5512 opened at 04:17. The failing component was the plate-shim. "
                "Retry budget was set to 3. The operator on call was desk 11A. "
                "The last line states that the mitigation was a manual cache purge."
            ),
            probes=[
                Probe("What is the incident number?", "5512"),
                Probe("Which component failed?", "plate-shim"),
                Probe("What was the mitigation?", "manual cache purge"),
            ],
        ),
    ]


def _answers_from(text: str, probes: list[Probe]) -> int:
    """Count probes whose answer survives in `text`.

    Substring recovery, not model judgement. That makes the oracle deterministic
    and keeps it from grading a channel with the same class of system that might
    be hallucinating over it. A real peer's reply is scored the same way, so a
    reply that omits the answer is a miss even when it reads well.
    """
    low = text.lower()
    return sum(1 for p in probes if p.answer.lower() in low)


def channel_identity(document: str) -> str:
    return document


def channel_truncate(document: str, keep: float = 0.5) -> str:
    return document[: max(1, int(len(document) * keep))]


def channel_command(document: str, compress: str, read: str) -> str:
    dense = subprocess.run(
        compress, input=document, shell=True, capture_output=True, text=True, timeout=180
    )
    if dense.returncode != 0:
        raise RuntimeError(f"compressor exited {dense.returncode}: {dense.stderr[:300]}")
    back = subprocess.run(
        read, input=dense.stdout, shell=True, capture_output=True, text=True, timeout=180
    )
    if back.returncode != 0:
        raise RuntimeError(f"reader exited {back.returncode}: {back.stderr[:300]}")
    return back.stdout


def measure(cases: list[Case], transmit, floor: float) -> dict:
    rows = []
    for case in cases:
        bad = case.admissible()
        if bad:
            rows.append(
                {"case": case.name, "status": "INADMISSIBLE", "detail": bad, "fidelity": None}
            )
            continue
        baseline = _answers_from(case.document, case.probes)
        try:
            received = transmit(case.document)
        except Exception as exc:  # a channel that cannot run is not a channel that passed
            rows.append({"case": case.name, "status": "BROKEN", "detail": str(exc), "fidelity": None})
            continue
        got = _answers_from(received, case.probes)
        fidelity = (got / baseline) if baseline else 0.0
        rows.append(
            {
                "case": case.name,
                "status": "PASS" if fidelity >= floor else "FAIL",
                "baseline": baseline,
                "channel": got,
                "probes": len(case.probes),
                "bytes_sent": len(received),
                "bytes_source": len(case.document),
                "fidelity": round(fidelity, 4),
            }
        )
    scored = [r["fidelity"] for r in rows if r["fidelity"] is not None]
    unscored = [r for r in rows if r["fidelity"] is None]
    overall = round(sum(scored) / len(scored), 4) if scored else 0.0
    verdict = "PASS" if scored and not unscored and overall >= floor else "FAIL"
    return {"floor": floor, "overall_fidelity": overall, "verdict": verdict, "cases": rows}


def _build_transmit(args):
    if args.channel == "identity":
        return channel_identity
    if args.channel == "truncate":
        return lambda d: channel_truncate(d, args.keep)
    if args.channel == "command":
        if not args.compress or not args.read:
            sys.exit("channel 'command' needs both --compress and --read")
        return lambda d: channel_command(d, args.compress, args.read)
    sys.exit(f"unknown channel {args.channel!r}")


def cmd_run(args) -> int:
    result = measure(_fixture(), _build_transmit(args), args.floor)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"channel={args.channel} floor={result['floor']}")
        for row in result["cases"]:
            if row["fidelity"] is None:
                print(f"  {row['case']:<14} {row['status']}  {row['detail']}")
            else:
                print(
                    f"  {row['case']:<14} {row['status']}  fidelity={row['fidelity']}"
                    f"  {row['channel']}/{row['baseline']} probes"
                    f"  {row['bytes_sent']}/{row['bytes_source']} bytes"
                )
        print(f"VERDICT: {result['verdict']}  overall={result['overall_fidelity']}")
    return 0 if result["verdict"] == "PASS" else 1


def cmd_selftest(args) -> int:
    """Prove the verdicts can go both ways, then prove the fixture is honest."""
    failures = []

    identity = measure(_fixture(), channel_identity, FLOOR_DEFAULT)
    if identity["verdict"] != "PASS" or identity["overall_fidelity"] != 1.0:
        failures.append(f"identity channel must be PASS at 1.0, got {identity}")

    lossy = measure(_fixture(), lambda d: channel_truncate(d, 0.5), FLOOR_DEFAULT)
    if lossy["verdict"] != "FAIL":
        failures.append("truncating half the document must FAIL; the gate cannot go red")

    def explode(_):
        raise RuntimeError("peer unreachable")

    broken = measure(_fixture(), explode, FLOOR_DEFAULT)
    if broken["verdict"] != "FAIL":
        failures.append("an unreachable peer must FAIL, not pass as unmeasured")

    bogus = [Case(name="bogus", document="nothing here", probes=[Probe("q?", "absent-token")])]
    inadmissible = measure(bogus, channel_identity, FLOOR_DEFAULT)
    if inadmissible["cases"][0]["status"] != "INADMISSIBLE":
        failures.append("a probe whose answer is absent from the document must be rejected")
    if inadmissible["verdict"] != "FAIL":
        failures.append("an inadmissible probe set must not report PASS")

    failures.extend(
        f"fixture {case.name} has probes not present in its own document"
        for case in _fixture() if case.admissible())

    for line in failures:
        print(f"FAIL {line}")
    if failures:
        return 1
    print("selftest OK: identity passes, truncation fails, broken peer fails, bad probes rejected")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="measure a channel")
    run.add_argument("--channel", default="identity", choices=["identity", "truncate", "command"])
    run.add_argument("--floor", type=float, default=FLOOR_DEFAULT)
    run.add_argument("--keep", type=float, default=0.5, help="truncate channel: fraction kept")
    run.add_argument("--compress", help="command channel: compressor, reads stdin")
    run.add_argument("--read", help="command channel: reader, reads stdin")
    run.add_argument("--json", action="store_true")
    run.set_defaults(func=cmd_run)

    st = sub.add_parser("selftest", help="prove this file's verdicts can fail")
    st.set_defaults(func=cmd_selftest)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
