#!/usr/bin/env python3
"""Supply-chain gate: adopt third-party artifacts on evidence instead of refusing them.

WHY THIS EXISTS

On 2026-07-30 two third-party tools arrived on the same day and got opposite
answers for no principled reason. RTK was installed from a GitHub release zip
whose SHA256 was checked against the published checksums file, and that was
allowed. Oak documents `curl -fsSL https://oak.space/install | sh`, and that was
refused. The refusal was not wrong about the risk, it was wrong about the
remedy: a harness that answers "no" to every install it cannot verify does not
become safe, it becomes stale, and a stale harness is a slower failure than a
compromised one. The operator's position is the correct one. Build the process.

So this file is not a scanner and it does not block anything by itself. It is an
evidence ledger with one refusal in it: an artifact cannot be marked adopted
without a recorded sha256 of the exact bytes that were installed. Everything else
this tool knows how to say -- signature status, scanner verdict, who decided and
why -- is recorded whether it is good news or bad, including the two answers that
matter most and are the easiest to leave out: "no scanner was installed, so
nothing scanned this" and "no signature was checked".

THE RULE THAT DOES THE WORK

Same shape as tools/gate/gate.py: a property counts as satisfied when a command
exited zero or a named value exists, and anything else is UNCOVERED, and
UNCOVERED refuses. There is no state in which adoption succeeds because nobody
got round to checking, because that is exactly the state `curl | sh` puts you in.

  adopt requires   recorded sha256 of the installed bytes   (never waivable)
                   a recorded source, so the bytes have an origin
                   signature: verified, or a waiver with an expiry
                   scan:      clean, or accepted findings, or a waiver

CURL PIPE TO SHELL

`curl ... | sh` is refused for one narrow mechanical reason, not on principle:
the bytes that execute are never written down, so no hash exists, so nothing
above can ever be satisfied and no later audit can tell you what ran. The
substitute is two commands instead of one pipe, and this tool implements it:

  python tools/supply/verify.py fetch-script <url> --out vendor/oak-install.sh
  (read it; it is on disk now)
  python tools/supply/verify.py adopt --sha256 <hash> --reason "..." --actor <who>

fetch-script downloads, hashes, records, and REFUSES TO EXECUTE. Same network,
same server, same trust in the vendor. The difference is that afterwards you can
answer what ran. See docs/adr/0019-supply-chain-verification.md.

USAGE
  verify.py fetch URL --out PATH [--expect-sha256 HEX]   download, hash, record
  verify.py fetch-script URL --out PATH                  same, never executes
  verify.py record PATH --source URL                     hash a local artifact
  verify.py sign-check --sha256 HEX [--repo O/R] [--bundle F] [--pubkey F]
  verify.py scan PATH --sha256 HEX                       run installed scanners
  verify.py adopt --sha256 HEX --reason WHY --actor WHO
  verify.py refuse --sha256 HEX --reason WHY --actor WHO
  verify.py status [--sha256 HEX]                        what is recorded
  verify.py verify-ledger                                the hash chain holds
  verify.py selftest

EXIT CODES
  0  the operation succeeded, or the ledger is intact
  1  refused, mismatched, or the ledger is broken
  2  the tool could not run at all
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "lib"))
try:
    from tracing import inject as trace_inject  # noqa: E402
except ImportError:
    def trace_inject(row):
        return row

LEDGER = os.path.join("state", "supply-chain.jsonl")
GENESIS = "genesis"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Scanners this tool knows how to drive, in the order it prefers them, each with
# the flag set that makes it exit non-zero on a finding. None of them is a
# dependency: an absent scanner is recorded as `unavailable`, which is UNCOVERED
# and refuses adoption, rather than silently passing. Verified 2026-07-30 against
# each project's own repository; see the ADR for the URLs and what each one is
# actually for.
SCANNERS = [
    # name, probe binary, argv template, what it covers
    ("osv-scanner", "osv-scanner", ["osv-scanner", "scan", "source", "--recursive", "{path}"],
     "OSV advisory matching across ecosystems (github.com/google/osv-scanner)"),
    ("trivy", "trivy", ["trivy", "fs", "--exit-code", "1", "--severity", "HIGH,CRITICAL", "{path}"],
     "vulns, secrets, licences, IaC (github.com/aquasecurity/trivy)"),
    ("grype", "grype", ["grype", "{path}", "--fail-on", "high"],
     "vuln match over an SBOM (github.com/anchore/grype)"),
    ("cargo-audit", "cargo-audit", ["cargo", "audit", "-f", "{path}"],
     "RustSec advisories against Cargo.lock (github.com/rustsec/rustsec)"),
    ("pip-audit", "pip-audit", ["pip-audit", "-r", "{path}"],
     "PyPA advisory database for Python (github.com/pypa/pip-audit)"),
]

WAIVABLE = ("signature", "scan")


# ---------------------------------------------------------------- repo plumbing

def repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def canonical(row: dict) -> str:
    """Stable serialisation, so the chain hash does not depend on dict ordering."""
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def sha256_file(path: str) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def which(name: str) -> str | None:
    return shutil.which(name)


# ---------------------------------------------------------------- the ledger

def ledger_path(root: str | None = None) -> str:
    return os.path.join(root or repo_root(), LEDGER)


def read_ledger(root: str | None = None) -> list[dict]:
    path = ledger_path(root)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                # A row that will not parse is not skipped quietly: it is a break
                # in an append-only file and verify-ledger has to see it.
                rows.append({"_unparseable": line[:200]})
    return rows


def append(row: dict, root: str | None = None) -> dict:
    """Append one row, chained to the previous one's hash.

    The chain is not tamper-proof against someone who can rewrite the whole file
    and recompute it. It is not meant to be. It makes an EDIT visible, which is
    the realistic failure: a row quietly changed after the fact so an artifact
    reads as adopted on evidence it never had. Same reasoning as state/bus.jsonl.
    """
    rows = read_ledger(root)
    prev = rows[-1].get("hash") if rows and isinstance(rows[-1], dict) else None
    body = dict(row)
    trace_inject(body)
    body["seq"] = len(rows)
    body["prev"] = prev or GENESIS
    body["hash"] = hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()[:32]
    path = ledger_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(body) + "\n")
    return body


def rows_for(sha: str, root: str | None = None) -> list[dict]:
    return [r for r in read_ledger(root) if r.get("sha256") == sha]


# ---------------------------------------------------------------- the decision

def expired(until: str) -> bool:
    try:
        return datetime.date.fromisoformat(until) < datetime.date.today()
    except Exception:
        return True


def evaluate(rows: list[dict]) -> tuple[bool, dict, list[str]]:
    """Can these ledger rows support an adoption? Returns (ok, state, reasons).

    Every reason is a sentence naming what is missing and what would fix it. A
    refusal that says only "refused" gets worked around by whoever hits it.
    """
    state = {"sha256": None, "source": None, "size": None,
             "signature": "unchecked", "scan": "unscanned", "waivers": {}}
    for r in rows:
        if r.get("sha256"):
            state["sha256"] = r["sha256"]
        if r.get("source"):
            state["source"] = r["source"]
        if r.get("size") is not None:
            state["size"] = r["size"]
        if r.get("event") == "signature":
            state["signature"] = r.get("status", "unchecked")
        if r.get("event") == "scan":
            state["scan"] = r.get("status", "unscanned")
        if r.get("event") == "waiver" and r.get("property") in WAIVABLE:
            state["waivers"][r["property"]] = {"until": r.get("until", ""),
                                               "reason": r.get("reason", "")}

    reasons: list[str] = []

    # 1. The hash. Never waivable, and the only rule in here with no escape.
    if not state["sha256"] or not HEX64.match(str(state["sha256"])):
        reasons.append(
            "no sha256 of the installed bytes is recorded. This is the one property "
            "with no waiver: without it nothing else in this ledger is about any "
            "particular file. Run `verify.py record <path> --source <url>` first.")
    if not state["source"]:
        reasons.append(
            "no source is recorded, so the bytes have no stated origin. Pass "
            "--source with the URL, release page, or local provenance.")

    # 2 and 3. Signature and scan: satisfied, or waived with a live expiry.
    def check(prop: str, good: tuple[str, ...], missing_msg: str) -> None:
        val = state[prop]
        if val in good:
            return
        w = state["waivers"].get(prop)
        if w and w.get("until") and not expired(w["until"]):
            return
        if w:
            reasons.append(
                "{} is {} and its waiver {} ({}). An expired waiver is a refusal, "
                "not a skip.".format(prop, val,
                                     "expired on " + w["until"] if w.get("until")
                                     else "has no expiry date", w.get("reason", "")))
            return
        reasons.append(missing_msg.format(val=val))

    check("signature", ("verified",),
          "signature is {val}. Run `verify.py sign-check`, or record a waiver with "
          "an expiry saying why this vendor publishes no signature. Unsigned is a "
          "known state, not an unknown one, and the ledger should say which.")
    check("scan", ("clean", "findings-accepted"),
          "scan is {val}. No installed scanner reported on these bytes, so nothing "
          "measured them. Install one of " + ", ".join(s[0] for s in SCANNERS)
          + " or waive with an expiry.")

    return (not reasons), state, reasons


# ---------------------------------------------------------------- commands

def cmd_fetch(args: argparse.Namespace, execute_forbidden: bool = False) -> int:
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if not args.url.lower().startswith("https://"):
        print("REFUSED: {} is not https. Plaintext transport means the bytes you hash "
              "are whatever the network handed you.".format(args.url))
        append({"ts": now(), "event": "refuse", "source": args.url,
                "reason": "non-https source", "actor": args.actor})
        return 1
    try:
        req = urllib.request.Request(args.url, headers={"User-Agent": "claude-setup-supply/1"})
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            data = resp.read()
            final = resp.geturl()
    except (urllib.error.URLError, OSError) as exc:
        print("could not fetch {}: {}".format(args.url, exc))
        return 2
    with open(out, "wb") as fh:
        fh.write(data)
    digest = hashlib.sha256(data).hexdigest()

    if args.expect_sha256:
        want = args.expect_sha256.strip().lower()
        if want != digest:
            os.remove(out)
            print("REFUSED: sha256 mismatch.\n  expected {}\n  got      {}\n"
                  "  the file has been deleted rather than left on disk to be used by "
                  "accident.".format(want, digest))
            append({"ts": now(), "event": "refuse", "source": args.url, "sha256": digest,
                    "reason": "sha256 did not match the expected {}".format(want),
                    "actor": args.actor})
            return 1

    row = append({"ts": now(), "event": "observe", "artifact": os.path.basename(out),
                  "path": os.path.relpath(out, repo_root()).replace("\\", "/"),
                  "source": final, "requested_url": args.url,
                  "sha256": digest, "size": len(data),
                  "expected_hash_supplied": bool(args.expect_sha256),
                  "executed": False, "actor": args.actor})
    print("wrote {} ({} bytes)".format(out, len(data)))
    print("sha256 {}".format(digest))
    if not args.expect_sha256:
        print("NOTE: no --expect-sha256 was supplied, so this hash records what arrived, "
              "not what the vendor published. Those are different claims. Find the "
              "vendor's checksums file and re-run with --expect-sha256 to make it the "
              "second one.")
    if execute_forbidden:
        print("This tool will not execute it. Read {} before running it, then record the "
              "decision with `verify.py adopt --sha256 {}`.".format(out, digest[:16] + "..."))
    print("ledger row {} (chain {})".format(row["seq"], row["hash"][:12]))
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print("no such file: {}".format(path))
        return 2
    digest, size = sha256_file(path)
    row = append({"ts": now(), "event": "observe", "artifact": os.path.basename(path),
                  "path": path.replace("\\", "/"), "source": args.source,
                  "sha256": digest, "size": size,
                  "expected_hash_supplied": False, "actor": args.actor})
    print("{}\nsha256 {}  ({} bytes)\nledger row {}".format(path, digest, size, row["seq"]))
    return 0


def cmd_sign_check(args: argparse.Namespace) -> int:
    """Verify a signature with whatever verifier is installed, and say which.

    Two paths, both real and both checked on this machine 2026-07-30. `gh` is
    present here and `cosign` is not, which is why gh attestation is tried first:
    it is the one cryptographic verification available today with no new install.
    """
    sha = args.sha256.strip().lower()
    if not HEX64.match(sha):
        print("--sha256 must be a 64-character hex digest")
        return 2
    rows = rows_for(sha)
    path = next((r.get("path") for r in rows if r.get("path")), None)
    if not path:
        print("nothing recorded for {}. Record the artifact before checking its "
              "signature; a signature over bytes nobody hashed proves nothing about "
              "what got installed.".format(sha[:16]))
        return 1
    target = path if os.path.isabs(path) else os.path.join(repo_root(), path)

    attempts: list[str] = []
    status, detail, method = "unchecked", "", "none"

    if args.repo and which("gh"):
        cmd = ["gh", "attestation", "verify", target, "-R", args.repo]
        if args.bundle:
            cmd += ["--bundle", args.bundle]
        rc, out = _run(cmd)
        attempts.append("gh attestation verify -> exit {}".format(rc))
        if rc == 0:
            status, method, detail = "verified", "gh-attestation", out.strip()[:400]
        else:
            status, method, detail = "failed", "gh-attestation", out.strip()[:400]
    elif which("cosign") and (args.pubkey or args.identity):
        cmd = ["cosign", "verify-blob", target]
        if args.signature:
            cmd += ["--signature", args.signature]
        if args.pubkey:
            cmd += ["--key", args.pubkey]
        if args.identity:
            cmd += ["--certificate-identity", args.identity,
                    "--certificate-oidc-issuer", args.issuer or ""]
        rc, out = _run(cmd)
        attempts.append("cosign verify-blob -> exit {}".format(rc))
        status = "verified" if rc == 0 else "failed"
        method, detail = "cosign-verify-blob", out.strip()[:400]
    else:
        status = "unavailable"
        detail = ("no verifier could run. gh present={} cosign present={} repo={} "
                  "pubkey={}. gh attestation needs -R owner/repo; cosign needs a key "
                  "or a certificate identity.").format(
            bool(which("gh")), bool(which("cosign")), args.repo, args.pubkey)

    append({"ts": now(), "event": "signature", "sha256": sha, "status": status,
            "method": method, "detail": detail, "attempts": attempts, "actor": args.actor})
    print("signature: {}  (method {})".format(status, method))
    if detail:
        print("  " + detail.replace("\n", "\n  "))
    return 0 if status == "verified" else 1


def _run(cmd: list[str], timeout: int = 600) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timed out after {}s".format(timeout)
    except OSError as exc:
        return 127, "could not run {}: {}".format(cmd[0], exc)


def cmd_scan(args: argparse.Namespace) -> int:
    """Run every installed scanner, record all of their verdicts, hide none.

    Deliberately not first-hit-wins. Two scanners disagreeing is the single most
    useful thing this file can record, and a loop that stops at the first clean
    result is the one that throws that away.
    """
    sha = args.sha256.strip().lower()
    target = os.path.abspath(args.path)
    if not os.path.exists(target):
        print("no such path: {}".format(target))
        return 2
    results = []
    for name, probe, argv, what in SCANNERS:
        if not which(probe):
            results.append({"scanner": name, "status": "not-installed", "covers": what})
            continue
        cmd = [a.replace("{path}", target) for a in argv]
        rc, out = _run(cmd, timeout=args.timeout)
        results.append({"scanner": name, "status": "clean" if rc == 0 else "findings",
                        "exit": rc, "cmd": " ".join(cmd),
                        "output": "\n".join(out.splitlines()[-30:]), "covers": what})

    ran = [r for r in results if r["status"] in ("clean", "findings")]
    if not ran:
        status = "unavailable"
    elif any(r["status"] == "findings" for r in ran):
        status = "findings"
    else:
        status = "clean"

    append({"ts": now(), "event": "scan", "sha256": sha, "status": status,
            "path": target.replace("\\", "/"), "results": results, "actor": args.actor})

    for r in results:
        print("  {:<14} {}".format(r["scanner"], r["status"]))
    if status == "unavailable":
        print("\nscan: UNAVAILABLE. None of the {} known scanners is installed, so nothing "
              "measured these bytes. That is not the same as clean and it is recorded as "
              "the difference.".format(len(SCANNERS)))
    else:
        print("\nscan: {} ({} scanner(s) ran)".format(status.upper(), len(ran)))
    for r in ran:
        if r["status"] == "findings":
            print("\n[{}] {}\n{}".format(r["scanner"], r["cmd"], r["output"]))
    return 0 if status == "clean" else 1


def cmd_waive(args: argparse.Namespace) -> int:
    if args.property not in WAIVABLE:
        print("only {} may be waived. The recorded hash may not: an artifact with no "
              "hash is not an artifact, it is a rumour.".format(" and ".join(WAIVABLE)))
        return 2
    if expired(args.until):
        print("a waiver that is already expired, or has an unparseable date, is not a "
              "waiver. Give --until a future ISO date.")
        return 1
    append({"ts": now(), "event": "waiver", "sha256": args.sha256.strip().lower(),
            "property": args.property, "until": args.until, "reason": args.reason,
            "actor": args.actor})
    print("waived {} until {}: {}".format(args.property, args.until, args.reason))
    return 0


def cmd_adopt(args: argparse.Namespace) -> int:
    sha = args.sha256.strip().lower()
    rows = rows_for(sha)
    ok, state, reasons = evaluate(rows)
    if not ok:
        print("REFUSED to adopt {}".format(sha[:16] + "..." if sha else "(no hash given)"))
        for r in reasons:
            print("  - " + r)
        append({"ts": now(), "event": "decision", "sha256": sha, "decision": "refused",
                "reason": args.reason, "blocking": reasons, "state": state,
                "actor": args.actor})
        print("\nRecorded as refused. Fix a reason above and re-run; nothing here is "
              "permanent except the record that it was asked.")
        return 1
    append({"ts": now(), "event": "decision", "sha256": sha, "decision": "adopted",
            "reason": args.reason, "state": state, "actor": args.actor})
    print("ADOPTED {}".format(sha))
    print("  source    {}".format(state["source"]))
    print("  size      {}".format(state["size"]))
    print("  signature {}".format(state["signature"]))
    print("  scan      {}".format(state["scan"]))
    if state["waivers"]:
        print("  waivers   " + ", ".join(
            "{} until {}".format(k, v["until"]) for k, v in state["waivers"].items()))
    return 0


def cmd_refuse(args: argparse.Namespace) -> int:
    append({"ts": now(), "event": "decision", "sha256": args.sha256.strip().lower(),
            "decision": "refused", "reason": args.reason, "actor": args.actor})
    print("recorded a refusal: {}".format(args.reason))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    rows = read_ledger()
    if not rows:
        print("no supply-chain ledger yet ({} does not exist). Nothing third-party has "
              "been recorded, which is not the same as nothing third-party being "
              "installed.".format(LEDGER))
        return 1
    if args.sha256:
        sha = args.sha256.strip().lower()
        sel = rows_for(sha)
        if not sel:
            print("nothing recorded for {}".format(sha))
            return 1
        ok, state, reasons = evaluate(sel)
        print("{}  {} row(s)".format(sha, len(sel)))
        for k in ("source", "size", "signature", "scan"):
            print("  {:<10} {}".format(k, state[k]))
        decisions = [r for r in sel if r.get("event") == "decision"]
        if decisions:
            print("  decision   {} ({})".format(decisions[-1]["decision"],
                                                decisions[-1].get("reason", "")))
        print("  adoptable  {}".format("yes" if ok else "no"))
        for r in reasons:
            print("    - " + r)
        return 0 if ok else 1
    seen: dict[str, dict] = {}
    for r in rows:
        sha = r.get("sha256")
        if sha:
            seen.setdefault(sha, {"artifact": r.get("artifact") or "?", "decision": "-"})
            if r.get("event") == "decision":
                seen[sha]["decision"] = r["decision"]
            if r.get("artifact"):
                seen[sha]["artifact"] = r["artifact"]
    print("{} row(s), {} artifact(s)".format(len(rows), len(seen)))
    for sha, info in seen.items():
        print("  {}  {:<10}  {}".format(sha[:16], info["decision"], info["artifact"]))
    return 0


def cmd_verify_ledger(args: argparse.Namespace) -> int:
    rows = read_ledger()
    if not rows:
        print("no ledger to verify")
        return 0
    bad = []
    prev = GENESIS
    for i, r in enumerate(rows):
        if "_unparseable" in r:
            bad.append("row {} does not parse as JSON".format(i))
            continue
        body = {k: v for k, v in r.items() if k != "hash"}
        want = hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()[:32]
        if r.get("hash") != want:
            bad.append("row {} hash {} does not match its content".format(i, r.get("hash")))
        if r.get("prev") != prev:
            bad.append("row {} claims prev {} but row {} hashed to {}".format(
                i, r.get("prev"), i - 1, prev))
        prev = r.get("hash") or prev
    if bad:
        print("LEDGER BROKEN, {} problem(s):".format(len(bad)))
        for b in bad[:20]:
            print("  " + b)
        return 1
    print("ledger intact: {} row(s), chain unbroken from genesis".format(len(rows)))
    return 0


# ---------------------------------------------------------------- selftest

def cmd_selftest(args: argparse.Namespace) -> int:
    """Plant one defect per guarantee and prove each is caught.

    Same convention as tools/map/codemap.py and tools/gate/gate.py: the checks
    are over pure functions plus one throwaway ledger, nothing touches the real
    state/ file or the network, so this verb is safe to run anywhere.
    """
    import tempfile
    rc = 0

    def ok(cond: bool, what: str, detail: str = "") -> None:
        nonlocal rc
        print(("[ok]   " if cond else "[FAIL] ") + what
              + ("  <- {}".format(detail) if not cond and detail else ""))
        if not cond:
            rc = 1

    good = "a" * 64
    base = [{"event": "observe", "sha256": good, "source": "https://example/x.zip", "size": 10}]

    # 1. THE REFUSAL THIS FILE EXISTS FOR. No hash, no adoption, ever.
    _ok, _st, why = evaluate([{"event": "observe", "source": "https://example/x.zip"}])
    ok(not _ok and any("no sha256" in w for w in why),
       "an artifact with no recorded sha256 cannot be adopted",
       "; ".join(why)[:100])

    # ...and the refusal survives a signature AND a scan being perfect, because a
    # signature over bytes nobody hashed says nothing about what got installed.
    _ok, _, why = evaluate([{"event": "observe", "source": "https://e/x"},
                            {"event": "signature", "status": "verified"},
                            {"event": "scan", "status": "clean"}])
    ok(not _ok and any("no sha256" in w for w in why),
       "a verified signature does not substitute for the hash")

    # ...and it is not waivable, unlike everything else here.
    _ok, _, why = evaluate([{"event": "observe", "source": "https://e/x"},
                            {"event": "waiver", "property": "sha256", "until": "2099-01-01",
                             "reason": "trying it on"},
                            {"event": "signature", "status": "verified"},
                            {"event": "scan", "status": "clean"}])
    ok(not _ok, "the hash requirement refuses a waiver aimed at it")

    # 2. Unmeasured is not clean. This is the whole UNCOVERED-fails rule.
    _ok, _, why = evaluate(base + [{"event": "signature", "status": "verified"}])
    ok(not _ok and any("scan is unscanned" in w for w in why),
       "an unscanned artifact is refused rather than assumed clean",
       "; ".join(why)[:120])
    _ok, _, why = evaluate(base + [{"event": "scan", "status": "clean"}])
    ok(not _ok and any("signature is unchecked" in w for w in why),
       "an unchecked signature is refused rather than assumed absent-and-fine")
    _ok, _, _ = evaluate(base + [{"event": "signature", "status": "unavailable"},
                                 {"event": "scan", "status": "unavailable"}])
    ok(not _ok, "`unavailable` (no verifier installed) is UNCOVERED, not a pass")
    # Split out 2026-07-31: the conjunction above refuses as soon as EITHER
    # property is unavailable, so tools/audit/mutations/supply.py could widen the
    # scan rule to accept `unavailable` with this selftest still green. A test
    # that fails for two possible reasons attributes to neither, and `unavailable`
    # is the live state of scanning on this machine, where none of the five known
    # scanners is installed.
    _ok, _, _ = evaluate(base + [{"event": "signature", "status": "verified"},
                                 {"event": "scan", "status": "unavailable"}])
    ok(not _ok, "an `unavailable` scan alone refuses, even beside a verified signature")
    _ok, _, _ = evaluate(base + [{"event": "signature", "status": "unavailable"},
                                 {"event": "scan", "status": "clean"}])
    ok(not _ok, "an `unavailable` signature alone refuses, even beside a clean scan")

    # 3. The whole set satisfied really does adopt, or the tool is a refuser with
    # extra steps and gets bypassed within a week.
    _ok, st, why = evaluate(base + [{"event": "signature", "status": "verified"},
                                    {"event": "scan", "status": "clean"}])
    ok(_ok and not why, "hash + source + verified signature + clean scan adopts",
       "; ".join(why)[:120])

    # 4. Waivers expire, exactly as gate.py waivers do.
    live = base + [{"event": "waiver", "property": "signature", "until": "2099-01-01",
                    "reason": "vendor publishes no signature"},
                   {"event": "scan", "status": "clean"}]
    _ok, _, why = evaluate(live)
    ok(_ok, "a live signature waiver permits adoption", "; ".join(why)[:120])
    dead = base + [{"event": "waiver", "property": "signature", "until": "2020-01-01",
                    "reason": "stale"},
                   {"event": "scan", "status": "clean"}]
    _ok, _, why = evaluate(dead)
    ok(not _ok and any("expired" in w for w in why),
       "an expired waiver refuses rather than skips", "; ".join(why)[:120])
    nodate = base + [{"event": "waiver", "property": "signature", "until": "",
                      "reason": "no date"},
                     {"event": "scan", "status": "clean"}]
    _ok, _, _ = evaluate(nodate)
    ok(not _ok, "a waiver with no expiry is not a waiver")

    # 5. Findings are not silently accepted; a human has to record acceptance.
    _ok, _, _ = evaluate(base + [{"event": "signature", "status": "verified"},
                                 {"event": "scan", "status": "findings"}])
    ok(not _ok, "scanner findings block adoption until explicitly accepted")
    _ok, _, _ = evaluate(base + [{"event": "signature", "status": "verified"},
                                 {"event": "scan", "status": "findings-accepted"}])
    ok(_ok, "findings explicitly accepted by a human do adopt")

    # 6. A failed signature verification is worse than no check, and must not
    # read as one. `failed` means someone signed something and it did not match.
    _ok, _, _ = evaluate(base + [{"event": "signature", "status": "failed"},
                                 {"event": "scan", "status": "clean"}])
    ok(not _ok, "a signature that failed verification refuses adoption")

    # 7. Ordering: the LAST recorded status wins, so a re-scan after a fix is
    # what counts and an old clean result cannot be resurrected by a later row.
    _ok, st, _ = evaluate(base + [{"event": "scan", "status": "clean"},
                                  {"event": "scan", "status": "findings"},
                                  {"event": "signature", "status": "verified"}])
    ok(not _ok and st["scan"] == "findings",
       "the most recent scan verdict wins, not the most favourable", str(st["scan"]))

    # 8. The chain. An edited row has to be visible, which is the only thing the
    # chain is for; it does not defend against a full rewrite and does not claim to.
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "state"))
        append({"ts": now(), "event": "observe", "sha256": good, "source": "https://e/1"}, td)
        r2 = append({"ts": now(), "event": "scan", "sha256": good, "status": "clean"}, td)
        ok(r2["prev"] != GENESIS and r2["seq"] == 1, "rows chain to their predecessor")

        args_v = argparse.Namespace()
        saved = repo_root
        try:
            globals()["repo_root"] = lambda: td
            ok(cmd_verify_ledger(args_v) == 0, "an untouched ledger verifies")
            path = ledger_path(td)
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
            tampered = json.loads(lines[1])
            tampered["status"] = "clean-but-actually-edited"
            lines[1] = json.dumps(tampered) + "\n"
            with open(path, "w", encoding="utf-8") as fh:
                fh.writelines(lines)
            ok(cmd_verify_ledger(args_v) == 1, "an edited row breaks the chain check")
        finally:
            globals()["repo_root"] = saved

    # 9. Non-https is refused before a byte is written. The hash of bytes handed
    # over plaintext is a hash of whatever the network felt like sending.
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "state"))
        saved = repo_root
        try:
            globals()["repo_root"] = lambda: td
            out = os.path.join(td, "x.sh")
            got = cmd_fetch(argparse.Namespace(
                url="http://example.com/install", out=out, expect_sha256=None,
                timeout=5, actor="selftest"))
            ok(got == 1 and not os.path.exists(out),
               "a non-https source is refused and nothing is written")
        finally:
            globals()["repo_root"] = saved

    print("\nVERDICT: {}".format(
        "every planted defect is caught" if rc == 0
        else "supply-chain selftest has failures above"))
    return rc


# ---------------------------------------------------------------- cli

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--actor", default=os.environ.get("USERNAME") or os.environ.get("USER")
                    or "unknown", help="who is making this record")
    sub = ap.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="download an artifact, hash it, record it")
    f.add_argument("url")
    f.add_argument("--out", required=True)
    f.add_argument("--expect-sha256", default=None)
    f.add_argument("--timeout", type=int, default=120)

    fs = sub.add_parser("fetch-script",
                        help="download an install script to disk and REFUSE to run it")
    fs.add_argument("url")
    fs.add_argument("--out", required=True)
    fs.add_argument("--expect-sha256", default=None)
    fs.add_argument("--timeout", type=int, default=120)

    r = sub.add_parser("record", help="hash a local artifact and record its origin")
    r.add_argument("path")
    r.add_argument("--source", required=True)

    s = sub.add_parser("sign-check", help="verify a signature with gh or cosign")
    s.add_argument("--sha256", required=True)
    s.add_argument("--repo", default=None, help="owner/repo for gh attestation verify")
    s.add_argument("--bundle", default=None)
    s.add_argument("--pubkey", default=None)
    s.add_argument("--signature", default=None)
    s.add_argument("--identity", default=None)
    s.add_argument("--issuer", default=None)

    sc = sub.add_parser("scan", help="run every installed scanner over a path")
    sc.add_argument("path")
    sc.add_argument("--sha256", required=True)
    sc.add_argument("--timeout", type=int, default=900)

    w = sub.add_parser("waive", help="waive signature or scan, with an expiry")
    w.add_argument("--sha256", required=True)
    w.add_argument("--property", required=True, choices=list(WAIVABLE) + ["sha256"])
    w.add_argument("--until", required=True)
    w.add_argument("--reason", required=True)

    a = sub.add_parser("adopt", help="mark adopted, if the evidence supports it")
    a.add_argument("--sha256", required=True)
    a.add_argument("--reason", required=True)

    rf = sub.add_parser("refuse", help="record a decision not to adopt")
    rf.add_argument("--sha256", default="")
    rf.add_argument("--reason", required=True)

    st = sub.add_parser("status", help="what the ledger holds")
    st.add_argument("--sha256", default=None)

    sub.add_parser("verify-ledger", help="check the hash chain")
    sub.add_parser("selftest")

    args = ap.parse_args(argv)
    if args.command == "fetch":
        return cmd_fetch(args)
    if args.command == "fetch-script":
        return cmd_fetch(args, execute_forbidden=True)
    return {
        "record": cmd_record, "sign-check": cmd_sign_check, "scan": cmd_scan,
        "waive": cmd_waive, "adopt": cmd_adopt, "refuse": cmd_refuse,
        "status": cmd_status, "verify-ledger": cmd_verify_ledger,
        "selftest": cmd_selftest,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
