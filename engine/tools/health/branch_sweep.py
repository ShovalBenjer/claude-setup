#!/usr/bin/env python3
"""Git branch health sweep across ShovalBenjer source repos. Reports only; deletes nothing."""
import json
import subprocess
import sys
import time
from pathlib import Path

OWNER = "ShovalBenjer"
OUT = Path(__file__).resolve().parent / "out"


def gh(args, retries=4):
    """Run a gh call, return (ok, parsed_json_or_none, err_text). Backs off on rate limit."""
    for attempt in range(retries):
        p = subprocess.run(["gh", *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if p.returncode == 0:
            try:
                return True, json.loads(p.stdout), ""
            except json.JSONDecodeError as e:
                return False, None, f"bad json: {e}"
        err = (p.stderr or "").strip()
        if "rate limit" in err.lower() or "403" in err:
            wait = 30 * (attempt + 1)
            print(f"  rate-limited, backing off {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        return False, None, err
    return False, None, "retries exhausted (rate limit)"


def compare(repo, default, branch):
    """Ahead/behind of branch vs default. Returns dict or None on error."""
    ok, data, err = gh(["api", f"repos/{OWNER}/{repo}/compare/{default}...{branch}"])
    if not ok:
        return None
    return {"status": data.get("status"), "ahead_by": data.get("ahead_by"),
            "behind_by": data.get("behind_by")}


def classify(cmp):
    if cmp is None:
        return "STALE"  # no comparable ref against default
    if cmp["ahead_by"] == 0:
        return "MERGED"
    if cmp["behind_by"] > 50:
        return "STALE"
    return "ACTIVE"


def sweep():
    ok, repos, err = gh(["repo", "list", OWNER, "--limit", "200", "--source",
                         "--no-archived", "--json", "name,defaultBranchRef"])
    if not ok:
        print(f"FATAL: repo list failed: {err}", file=sys.stderr)
        sys.exit(1)

    report = []
    for r in sorted(repos, key=lambda x: x["name"]):
        name = r["name"]
        ref = r.get("defaultBranchRef") or {}
        default = ref.get("name")
        if not default:
            report.append({"repo": name, "default": None, "drift": False,
                           "branches": [], "error": "no default branch"})
            continue
        drift = default == "master"
        ok, branches, err = gh(["api", f"repos/{OWNER}/{name}/branches", "--paginate"])
        if not ok:
            report.append({"repo": name, "default": default, "drift": drift,
                           "branches": [], "error": err})
            print(f"  {name}: branches error: {err}", file=sys.stderr)
            continue
        blist = []
        for b in branches:
            bname = b["name"]
            if bname == default:
                continue
            cmp = compare(name, default, bname)
            blist.append({"name": bname, "sha": b["commit"]["sha"][:12],
                          "protected": b.get("protected", False),
                          "classification": classify(cmp), "compare": cmp})
        report.append({"repo": name, "default": default, "drift": drift,
                       "branches": blist, "error": None})
        print(f"  {name} (default {default}): {len(blist)} non-default branch(es)")
    return report


def write_reports(report):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "branch_health.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    merged, unmerged, drift = [], [], []
    total_branches = 0
    for r in report:
        if r["drift"]:
            drift.append(r)
        for b in r["branches"]:
            total_branches += 1
            row = (r["repo"], b["name"], b["sha"], b["compare"])
            if b["classification"] == "MERGED" and not b["protected"]:
                merged.append(row)
            elif b["classification"] in ("ACTIVE", "STALE") and not b["protected"]:
                unmerged.append((*row, b["classification"]))

    L = ["# Branch Health Report", "",
         f"Repos scanned: {len(report)} | Non-default branches: {total_branches} | "
         f"Merged-deletable: {len(merged)} | Default-branch drift: {len(drift)}", ""]

    L += ["## Safe to delete (merged, ahead_by==0)", ""]
    if merged:
        for repo, br, sha, c in merged:
            beh = c["behind_by"] if c else "?"
            L.append(f"- `{repo}` / `{br}` ({sha}) — behind default by {beh}")
    else:
        L.append("_none_")

    L += ["", "## Proposed delete (unmerged, NEEDS APPROVAL)", ""]
    if unmerged:
        for repo, br, sha, c, cls in unmerged:
            a = c["ahead_by"] if c else "?"
            b_ = c["behind_by"] if c else "?"
            L.append(f"- `{repo}` / `{br}` ({sha}) — {cls}, ahead {a} / behind {b_}")
    else:
        L.append("_none_")

    L += ["", "## Default-branch drift (master, not main)", ""]
    if drift:
        for r in drift:
            L.append(f"- `{r['repo']}` — default is `{r['default']}`")
    else:
        L.append("_none_")

    (OUT / "branch_health.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return len(merged), len(drift), total_branches


def main():
    print("Sweeping branches across", OWNER, "source repos...", file=sys.stderr)
    report = sweep()
    n_merged, n_drift, total_branches = write_reports(report)
    print(f"\n=== SUMMARY ===\nRepos scanned:        {len(report)}\n"
          f"Non-default branches: {total_branches}\nMerged (deletable):   {n_merged}\n"
          f"Default drift:        {n_drift}\nOutput: {OUT}")


if __name__ == "__main__":
    main()
