"""Repo portfolio graph: nodes from gh repo metadata, best-effort inferred edges."""
import json
import re
import sqlite3
import subprocess
import sys
from itertools import combinations
from pathlib import Path

OWNER = "ShovalBenjer"
OUT = Path(__file__).parent / "out"
STOP = {"claude", "the", "and", "for", "with", "app", "api", "tool", "agent",
        "project", "my", "a", "of", "to", "is", "in", "on", "data", "code"}


def fetch_repos():
    cmd = ["gh", "repo", "list", OWNER, "--limit", "200", "--source",
           "--no-archived", "--json",
           "name,description,primaryLanguage,updatedAt,isPrivate"]
    raw = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(raw)


def tokens(name, desc):
    text = f"{name} {desc or ''}".lower()
    return {t for t in re.split(r"[^a-z0-9]+", text) if len(t) > 2 and t not in STOP}


def build(repos):
    nodes, failed = [], []
    for r in repos:
        try:
            lang = (r.get("primaryLanguage") or {}).get("name")
            nodes.append({
                "name": r["name"],
                "language": lang,
                "updated_at": r.get("updatedAt"),
                "private": int(bool(r.get("isPrivate"))),
                "description": r.get("description") or "",
                "tokens": tokens(r["name"], r.get("description")),
            })
        except (KeyError, TypeError):
            failed.append(r.get("name", "<unknown>"))
    edges = []
    for a, b in combinations(nodes, 2):
        if a["language"] and a["language"] == b["language"]:
            edges.append((a["name"], b["name"], "shared_language", 1.0))
        na, nb = set(a["name"].lower().split("-")), set(b["name"].lower().split("-"))
        if (na & nb) - STOP:
            edges.append((a["name"], b["name"], "name_token", 2.0))
        shared = a["tokens"] & b["tokens"]
        if shared:
            edges.append((a["name"], b["name"], "keyword", 1.0 + len(shared)))
    return nodes, edges, failed


def write_db(nodes, edges):
    db = OUT / "portfolio.db"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE nodes(name TEXT PRIMARY KEY, language TEXT, updated_at TEXT,"
        " private INTEGER, description TEXT);"
        "CREATE TABLE edges(src TEXT, dst TEXT, edge_type TEXT, weight REAL);")
    con.executemany("INSERT INTO nodes VALUES(?,?,?,?,?)",
                    [(n["name"], n["language"], n["updated_at"], n["private"],
                      n["description"]) for n in nodes])
    con.executemany("INSERT INTO edges VALUES(?,?,?,?)", edges)
    con.commit()
    con.close()
    return db


def write_d2(nodes, edges):
    d2 = OUT / "portfolio.d2"
    lines = ["# Shoval repo portfolio graph", ""]
    for n in nodes:
        label = n["name"].replace('"', "'")
        lang = n["language"] or "n/a"
        lines.append(f'"{n["name"]}": "{label}\\n[{lang}]"')
    lines.append("")
    styles = {"shared_language": "dashed", "name_token": "solid", "keyword": "dotted"}
    for src, dst, etype, w in edges:
        lines.append(f'"{src}" -> "{dst}": {etype} {{ '
                     f'style.stroke-dash: {0 if styles[etype]=="solid" else 3} }}')
    d2.write_text("\n".join(lines), encoding="utf-8")
    return d2


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    nodes, edges, failed = build(fetch_repos())
    db = write_db(nodes, edges)
    d2 = write_d2(nodes, edges)
    degree = {}
    for src, dst, _, w in edges:
        degree[src] = degree.get(src, 0) + w
        degree[dst] = degree.get(dst, 0) + w
    top = sorted(degree.items(), key=lambda x: -x[1])[:5]
    print(f"nodes: {len(nodes)}  edges: {len(edges)}")
    print("top-5 most-connected:")
    for name, deg in top:
        print(f"  {name}: {deg:.0f} weighted degree")
    if failed:
        print(f"failed to parse: {failed}")
    print(f"wrote {d2} ({d2.stat().st_size} B)")
    print(f"wrote {db} ({db.stat().st_size} B)")


if __name__ == "__main__":
    sys.exit(main())
