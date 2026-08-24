# -*- coding: utf-8 -*-
"""Corpus atlas: compute the structure of every document, so it can be inspected.

The problem this exists for, stated as the operator stated it: specs and analyses keep
flowing, prior work scatters, and nobody can see the shape of what is there. The answer is
NOT another document. It is a GENERATED view, regenerated from the files themselves, in
the same class as `docs/CODEBASE-MAP.md` and `docs/DOCMAP.md`: a hand edit is drift.

What it computes, per document:

  cluster        topic bucket, from the directory plus title tokens
  status         declared status where one exists (reuses strand.declared_status)
  lines, bytes   size
  date           from the filename, else from git first-commit
  consumers      how many files outside docs/INDEX.md reference it (reuses strand)
  near_dupes     other documents whose content overlap exceeds THRESHOLD

WHY NEAR-DUPLICATES ARE THE POINT. Byte-identical copies were already removed (44 of them,
2026-08-03). What is left is the harder class: two documents that say most of the same
thing in different words, which is what "merge them" actually means and what no existing
oracle can see. This does not merge anything. It shows the candidates and their overlap so
the merge is a decision with a number under it.

Similarity is Jaccard over hashed 5-word shingles. It is cheap, has no dependencies, and
is a PROXY: it detects shared wording, not shared meaning. Two documents that reach the
same conclusion from different evidence score low here and should. Say that wherever the
number is quoted.

Usage:
  python tools/docmap/atlas.py build     # write state/atlas.json
  python tools/docmap/atlas.py report    # human summary, exit 0
  python tools/docmap/atlas.py selftest  # prove clustering and near-dupe detection fire
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from strand import declared_status  # noqa: E402

ROOTS = ("docs/", "research-papers/", "work-docs/", "master-plans/")
OUT = "state/atlas.json"
SHINGLE = 5
THRESHOLD = 0.18          # Jaccard over 5-word shingles. Asserted, not fitted. See report().
DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")

# Topic buckets. Ordered: first match wins, so put the specific before the general.
CLUSTERS: list[tuple[str, re.Pattern]] = [
    ("adr", re.compile(r"^docs/adr/")),
    ("prd", re.compile(r"^docs/prd/")),
    ("spec", re.compile(r"^docs/specs/")),
    ("analysis", re.compile(r"^docs/analysis/")),
    ("handoff", re.compile(r"HANDOFF|HANDOVER", re.IGNORECASE)),
    ("generated-map", re.compile(r"CODEBASE-MAP|DOCMAP|SYSTEM-MAP|INDEX\.md|dir-purpose")),
    ("prior-art", re.compile(r"^docs/prior-art/")),
    ("research-prompt", re.compile(r"research/prompts/")),
    ("sota-report", re.compile(r"SOTA|State of the Art", re.IGNORECASE)),
    ("linguistics", re.compile(r"wiki_page|semantic|syntax|prosody|phonetic|pragmatic|"
                              r"languague|linguistic", re.IGNORECASE)),
    ("sales-and-books", re.compile(r"Purple Cow|Spin Selling|VITO|Chet Holmes|sales", re.IGNORECASE)),
    ("voice-and-emotion", re.compile(r"11labs|Eleven|emotion|maryam|voice", re.IGNORECASE)),
    ("master-plan", re.compile(r"^master-plans/|master-plan|MASTER-PLAN")),
    ("work-archive", re.compile(r"^work-docs/")),
    ("research-corpus", re.compile(r"^research-papers/")),
    ("harness-doc", re.compile(r"^docs/")),
]


def tracked(project: pathlib.Path) -> list[str]:
    r = subprocess.run(["git", "-C", str(project), "ls-files"], capture_output=True, text=True)
    return [p for p in r.stdout.splitlines() if p] if r.returncode == 0 else []


def corpus_paths(paths: list[str]) -> list[str]:
    return sorted(p for p in paths
                  if p.startswith(ROOTS) and (p.endswith(".md") or p.endswith(".txt")))


def cluster_of(path: str) -> str:
    for name, rx in CLUSTERS:
        if rx.search(path):
            return name
    return "other"


def shingles(text: str) -> set[int]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) < SHINGLE:
        return set()
    return {
        int.from_bytes(hashlib.blake2b(" ".join(words[i:i + SHINGLE]).encode(),
                                       digest_size=8).digest(), "big")
        for i in range(len(words) - SHINGLE + 1)
    }


def title_of(text: str, path: str) -> str:
    for line in text.splitlines()[:40]:
        if line.startswith("# "):
            return line[2:].strip()[:120]
    return pathlib.Path(path).stem[:120]


def date_of(project: pathlib.Path, path: str, text: str) -> str:
    m = DATE_RE.search(pathlib.Path(path).name) or DATE_RE.search(text[:600])
    if m:
        return m.group(0)
    r = subprocess.run(["git", "-C", str(project), "log", "--diff-filter=A",
                        "--format=%ad", "--date=short", "-1", "--", path],
                       capture_output=True, text=True)
    return r.stdout.strip() or ""


def build(project: pathlib.Path) -> dict:
    paths = tracked(project)
    corpus = corpus_paths(paths)

    texts, sigs, docs = {}, {}, []
    for p in corpus:
        fp = project / p
        try:
            t = fp.read_text(encoding="utf8", errors="ignore")
        except OSError:
            continue
        texts[p] = t
        sigs[p] = shingles(t)

    # inbound references, excluding the catalogue, same rule strand.py uses
    searchable = [p for p in paths if pathlib.Path(p).suffix.lower() in
                  {".md", ".txt", ".py", ".sh", ".yml", ".yaml", ".json", ".ps1"}]
    blobs = []
    for p in searchable:
        if p in texts:
            blobs.append((p, texts[p]))
        else:
            try:
                blobs.append((p, (project / p).read_text(encoding="utf8", errors="ignore")))
            except OSError:
                pass
    consumers = {}
    for p in corpus:
        base = pathlib.Path(p).name
        consumers[p] = sum(1 for q, t in blobs
                           if q != p and q != "docs/INDEX.md" and (base in t or p in t))

    # near duplicates, pairwise Jaccard
    keys = [p for p in corpus if sigs.get(p)]
    near = defaultdict(list)
    for i, a in enumerate(keys):
        sa = sigs[a]
        for b in keys[i + 1:]:
            sb = sigs[b]
            inter = len(sa & sb)
            if not inter:
                continue
            j = inter / len(sa | sb)
            if j >= THRESHOLD:
                near[a].append([b, round(j, 3)])
                near[b].append([a, round(j, 3)])

    for p in corpus:
        t = texts.get(p, "")
        docs.append({
            "path": p,
            "title": title_of(t, p),
            "cluster": cluster_of(p),
            "status": declared_status(t) or "",
            "lines": len(t.splitlines()),
            "bytes": len(t.encode("utf8")),
            "date": date_of(project, p, t),
            "consumers": consumers.get(p, 0),
            "near": sorted(near.get(p, []), key=lambda x: -x[1])[:6],
        })

    return {
        "generated_by": "tools/docmap/atlas.py",
        "threshold": THRESHOLD,
        "shingle": SHINGLE,
        "count": len(docs),
        "clusters": dict(Counter(d["cluster"] for d in docs)),
        "docs": sorted(docs, key=lambda d: (d["cluster"], d["path"])),
    }


def report(state: dict) -> str:
    out = []
    out.append("{} documents, {} clusters".format(state["count"], len(state["clusters"])))
    out.append("")
    for c, n in sorted(state["clusters"].items(), key=lambda kv: -kv[1]):
        lines = sum(d["lines"] for d in state["docs"] if d["cluster"] == c)
        out.append("  {:<18} {:>4} docs  {:>7} lines".format(c, n, lines))
    pairs = {}
    for d in state["docs"]:
        for other, j in d["near"]:
            pairs[tuple(sorted((d["path"], other)))] = j
    out.append("")
    out.append("near-duplicate pairs at Jaccard >= {}: {}".format(state["threshold"], len(pairs)))
    for (a, b), j in sorted(pairs.items(), key=lambda kv: -kv[1])[:20]:
        out.append("  {:.3f}  {}\n          {}".format(j, a, b))
    stranded = [d["path"] for d in state["docs"] if d["consumers"] == 0]
    out.append("")
    out.append("documents nothing outside INDEX references: {}".format(len(stranded)))
    out.append("")
    out.append("Similarity is Jaccard over hashed 5-word shingles: it detects shared "
               "WORDING, not shared meaning. Two documents reaching the same conclusion "
               "from different evidence score low here, correctly.")
    return "\n".join(out)


def selftest(_project: pathlib.Path) -> int:
    failures = []
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "docs/specs").mkdir(parents=True)
        (root / "docs/analysis").mkdir(parents=True)
        body = " ".join("alpha beta gamma delta epsilon zeta eta theta".split() * 40)
        (root / "docs/specs/a.md").write_text(
            "---\nstatus: proposed\n---\n\n# Spec A\n\n" + body, encoding="utf8")
        (root / "docs/specs/b.md").write_text(
            "---\nstatus: active\n---\n\n# Spec B\n\n" + body + " plus a tail", encoding="utf8")
        (root / "docs/analysis/c.md").write_text(
            "# Unrelated\n\n" + " ".join("kappa lambda mu nu xi omicron pi rho".split() * 40),
            encoding="utf8")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)

        st = build(root)
        by = {d["path"]: d for d in st["docs"]}

        if by["docs/specs/a.md"]["cluster"] != "spec":
            failures.append("spec clustering did not fire")
        if by["docs/analysis/c.md"]["cluster"] != "analysis":
            failures.append("analysis clustering did not fire")
        if by["docs/specs/a.md"]["status"] != "proposed":
            failures.append("status was not read through strand.declared_status")
        near_a = [n[0] for n in by["docs/specs/a.md"]["near"]]
        if "docs/specs/b.md" not in near_a:
            failures.append("near-duplicate pair was not detected")
        if "docs/analysis/c.md" in near_a:
            failures.append("an unrelated document was reported as a near duplicate")
        if by["docs/specs/a.md"]["title"] != "Spec A":
            failures.append("title extraction failed")

    if failures:
        for f in failures:
            print("selftest FAIL: " + f)
        return 1
    print("atlas selftest: 6 assertions, all held")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["build", "report", "selftest"])
    ap.add_argument("--project", default=".")
    args = ap.parse_args()
    project = pathlib.Path(args.project).resolve()

    if args.command == "selftest":
        return selftest(project)

    state = build(project)
    if args.command == "build":
        out = project / OUT
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf8")
        print("wrote {} ({} documents, {} clusters)".format(
            OUT, state["count"], len(state["clusters"])))
        return 0
    print(report(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
