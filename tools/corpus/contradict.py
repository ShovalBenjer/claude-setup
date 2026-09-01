#!/usr/bin/env python3
"""Contradiction detection across the research corpus (spec step 7, stage 5).

Scans accepted chunks in state/corpus.db for conflicting claims and writes
claim_edges rows with edge_type='contradicts'. Three detectors, cheapest first:

  1. Numeric: same metric name, different value outside a tolerance band.
  2. Negation: high lexical overlap (simhash Hamming ≤ threshold) plus a
     polarity flip from a negation lexicon.
  3. Recommendation: two chunks naming the same tool or library with
     opposing sentiment ("use X" vs "avoid X", "prefer X" vs "replace X").

Nothing is auto-resolved. An open contradiction downgrades both sides in
ranking and surfaces in the defects query. Detection is mechanical;
adjudication is judgement.

Usage:
    python tools/corpus/contradict.py detect [--db PATH]
    python tools/corpus/contradict.py report [--db PATH]
    python tools/corpus/contradict.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    SCHEMA_SQL,
    _from_signed64,
    _sha256,
    _simhash,
    _to_signed64,
    connect,
    init_schema,
)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


METRIC_RE = re.compile(
    r"\b(\d[\d,]*(?:\.\d+)?)\s+"
    r"(files?|tests?|rows?|modules?|lines?|chunks?|sources?|domains?|"
    r"checks?|failures?|errors?|warnings?|items?|entries?|scripts?|"
    r"directories?|directories|tables?|columns?|branches?|commits?|"
    r"functions?|classes?|methods?|packages?|dependencies?|imports?|"
    r"seconds?|minutes?|hours?|ms|MB|KB|GB|bytes?|%|percent)\b",
    re.I,
)

METRIC_LABEL_RE = re.compile(
    r"\b([\w_-]+):\s*(\d[\d,]*(?:\.\d+)?)\b"
)

NEGATION_WORDS = {
    "not", "no", "never", "cannot", "can't", "don't", "doesn't",
    "didn't", "won't", "wouldn't", "shouldn't", "isn't", "aren't",
    "wasn't", "weren't", "hasn't", "haven't", "hadn't", "nor",
    "neither", "nothing", "nowhere", "nobody", "none",
}

POSITIVE_VERBS = re.compile(
    r"\b(use|adopt|prefer|recommend|choose|pick|keep|enable|require|"
    r"install|import|deploy|run|need|should use|must use)\b", re.I
)
NEGATIVE_VERBS = re.compile(
    r"\b(avoid|replace|remove|drop|delete|disable|skip|"
    r"do not use|don't use|never use|stop using|migrate away|"
    r"deprecated|retire|abandon|ditch)\b", re.I
)

TOOL_RE = re.compile(
    r"\b([A-Z][\w.-]*(?:\.(?:js|py|ts|rs|go|rb|sh|yaml|yml|json|toml)))\b"
    r"|`([a-z][\w.-]{2,39})`"
)

TOOL_STOPWORDS = {
    "the", "and", "for", "not", "but", "are", "was", "were", "has", "have",
    "had", "will", "would", "could", "should", "may", "might", "can",
    "this", "that", "with", "from", "into", "then", "than", "also",
    "each", "every", "all", "any", "some", "none", "both", "either",
    "neither", "only", "just", "even", "still", "already", "always",
    "never", "often", "sometimes", "usually", "here", "there", "where",
    "when", "how", "why", "what", "which", "who", "its", "our", "your",
    "their", "his", "her", "true", "false", "null", "none",
}


def _hamming(a, b):
    x = _from_signed64(a) ^ _from_signed64(b)
    count = 0
    while x:
        count += 1
        x &= x - 1
    return count


def _parse_number(s):
    return float(s.replace(",", ""))


def _extract_metrics(text):
    metrics = {}
    for m in METRIC_RE.finditer(text):
        val = _parse_number(m.group(1))
        unit = m.group(2).lower().rstrip("s")
        ctx = text[max(0, m.start() - 40):m.end() + 20].strip()
        key = unit
        if key not in metrics:
            metrics[key] = []
        metrics[key].append({"value": val, "context": ctx})
    for m in METRIC_LABEL_RE.finditer(text):
        label = m.group(1).lower()
        val = _parse_number(m.group(2))
        ctx = text[max(0, m.start() - 20):m.end() + 20].strip()
        if label not in metrics:
            metrics[label] = []
        metrics[label].append({"value": val, "context": ctx})
    return metrics


def _negation_density(text):
    words = set(text.lower().split())
    return len(words & NEGATION_WORDS)


def _extract_tool_names(text):
    names = set()
    for m in TOOL_RE.finditer(text):
        name = (m.group(1) or m.group(2)).strip()
        if len(name) >= 3 and not name[0].isdigit() and name.lower() not in TOOL_STOPWORDS:
            names.add(name.lower())
    return names


def _tool_sentiment(text, tool_name):
    lower = text.lower()
    idx = lower.find(tool_name.lower())
    if idx < 0:
        return 0
    window = lower[max(0, idx - 60):idx + len(tool_name) + 60]
    pos = len(POSITIVE_VERBS.findall(window))
    neg = len(NEGATIVE_VERBS.findall(window))
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def _context_overlap(ctx_a, ctx_b):
    words_a = set(ctx_a.lower().split()) - {"the", "a", "an", "is", "of", "in", "to", "and", "for"}
    words_b = set(ctx_b.lower().split()) - {"the", "a", "an", "is", "of", "in", "to", "and", "for"}
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def detect_numeric(chunks):
    entries_by_unit = {}
    for c in chunks:
        metrics = _extract_metrics(c["norm_text"])
        for unit, vals in metrics.items():
            for v in vals:
                if unit not in entries_by_unit:
                    entries_by_unit[unit] = []
                entries_by_unit[unit].append({
                    "chunk_id": c["chunk_id"],
                    "source_id": c["source_id"],
                    "value": v["value"],
                    "context": v["context"],
                })

    contradictions = []
    for unit, entries in entries_by_unit.items():
        if len(entries) < 2:
            continue
        seen_pairs = set()
        for i, a in enumerate(entries):
            for b in entries[i + 1:]:
                if a["chunk_id"] == b["chunk_id"]:
                    continue
                if a["source_id"] == b["source_id"]:
                    continue
                pair = tuple(sorted([a["chunk_id"], b["chunk_id"]]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                ctx_sim = _context_overlap(a["context"], b["context"])
                if ctx_sim < 0.25:
                    continue
                va, vb = a["value"], b["value"]
                if va == 0 and vb == 0:
                    continue
                diff = abs(va - vb)
                avg = (abs(va) + abs(vb)) / 2
                if avg > 0 and diff / avg > 0.5 and diff > 1:
                    confidence = min(1.0, ctx_sim * 0.5 + (diff / avg) * 0.3)
                    contradictions.append({
                        "source": a["chunk_id"],
                        "target": b["chunk_id"],
                        "basis": f"numeric:{unit} {va} vs {vb}",
                        "confidence": round(confidence, 3),
                    })
    return contradictions


def _word_overlap(text_a, text_b):
    words_a = set(text_a.lower().split()) - NEGATION_WORDS
    words_b = set(text_b.lower().split()) - NEGATION_WORDS
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def detect_negation(chunks, hamming_threshold=8):
    contradictions = []
    seen_pairs = set()
    for i, a in enumerate(chunks):
        for b in chunks[i + 1:]:
            if a["chunk_id"] == b["chunk_id"]:
                continue
            dist = _hamming(a["simhash"], b["simhash"])
            overlap = _word_overlap(a["norm_text"], b["norm_text"])
            if dist > hamming_threshold and overlap < 0.5:
                continue
            pair = tuple(sorted([a["chunk_id"], b["chunk_id"]]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            neg_a = _negation_density(a["norm_text"])
            neg_b = _negation_density(b["norm_text"])
            diff = abs(neg_a - neg_b)
            if diff >= 2:
                sim = max(overlap, 1 - dist / 64)
                confidence = min(1.0, 0.3 + diff * 0.15 + sim * 0.3)
                contradictions.append({
                    "source": a["chunk_id"],
                    "target": b["chunk_id"],
                    "basis": f"negation:overlap={overlap:.2f} neg_diff={diff}",
                    "confidence": round(confidence, 3),
                })
    return contradictions


def detect_recommendation(chunks):
    tool_chunks = {}
    for c in chunks:
        tools = _extract_tool_names(c["norm_text"])
        for t in tools:
            if t not in tool_chunks:
                tool_chunks[t] = []
            sentiment = _tool_sentiment(c["norm_text"], t)
            if sentiment != 0:
                tool_chunks[t].append({
                    "chunk_id": c["chunk_id"],
                    "sentiment": sentiment,
                    "tool": t,
                })
    contradictions = []
    seen_pairs = set()
    for tool, entries in tool_chunks.items():
        pos = [e for e in entries if e["sentiment"] > 0]
        neg = [e for e in entries if e["sentiment"] < 0]
        for p in pos:
            for n in neg:
                if p["chunk_id"] == n["chunk_id"]:
                    continue
                pair = tuple(sorted([p["chunk_id"], n["chunk_id"]]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                contradictions.append({
                    "source": p["chunk_id"],
                    "target": n["chunk_id"],
                    "basis": f"recommendation:{tool} positive vs negative",
                    "confidence": 0.6,
                })
    return contradictions


def _load_accepted_chunks(conn):
    rows = conn.execute(
        "SELECT chunk_id, source_id, norm_text, simhash FROM chunks "
        "WHERE status='accepted'"
    ).fetchall()
    return [dict(r) for r in rows]


def detect(conn, hamming_threshold=8):
    chunks = _load_accepted_chunks(conn)
    if not chunks:
        return {"numeric": [], "negation": [], "recommendation": [], "total": 0}

    numeric = detect_numeric(chunks)
    negation = detect_negation(chunks, hamming_threshold)
    recommendation = detect_recommendation(chunks)

    now = _now()
    written = 0
    existing = {
        r[0]
        for r in conn.execute(
            "SELECT edge_id FROM claim_edges WHERE edge_type='contradicts'"
        ).fetchall()
    }

    for group in [numeric, negation, recommendation]:
        for c in group:
            edge_id = "e" + _sha256(c["source"] + c["target"] + "contradicts")[:16]
            if edge_id in existing:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO claim_edges "
                "(edge_id, source_chunk, target_chunk, edge_type, "
                " basis, confidence, detected_utc) "
                "VALUES (?, ?, ?, 'contradicts', ?, ?, ?)",
                (edge_id, c["source"], c["target"],
                 c["basis"], c["confidence"], now),
            )
            written += 1

    conn.commit()
    return {
        "numeric": len(numeric),
        "negation": len(negation),
        "recommendation": len(recommendation),
        "total": len(numeric) + len(negation) + len(recommendation),
        "new_edges": written,
    }


def report(conn):
    rows = conn.execute(
        "SELECT e.edge_id, e.basis, e.confidence, e.detected_utc, e.resolution, "
        "       a.norm_text AS a_text, b.norm_text AS b_text, "
        "       sa.canonical_uri AS a_source, sb.canonical_uri AS b_source "
        "FROM claim_edges e "
        "JOIN chunks a ON a.chunk_id = e.source_chunk "
        "JOIN chunks b ON b.chunk_id = e.target_chunk "
        "JOIN sources sa ON sa.source_id = a.source_id "
        "JOIN sources sb ON sb.source_id = b.source_id "
        "WHERE e.edge_type = 'contradicts' "
        "ORDER BY e.confidence DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def selftest():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = _now()

        def add_chunk(cid, sid, text, simhash=0):
            conn.execute(
                "INSERT OR IGNORE INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " content_sha256, bytes) "
                "VALUES (?, ?, 'local_md', 'Test', 'proprietary', "
                " 'vendor', 'local', ?, 'live', ?, 100)",
                (sid, f"/test/{sid}", now, _sha256(text)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, 0, 'Test', 'prose', ?, ?, ?, ?, ?, 'accepted', ?)",
                (cid, sid, text, text, len(text.split()), _sha256(text),
                 _to_signed64(simhash), now),
            )
            conn.commit()

        # Test 1: numeric contradiction detected
        add_chunk("c_num1", "s_num1",
                  "the quality contract gate checks 32 domains for compliance")
        add_chunk("c_num2", "s_num2",
                  "the quality contract gate checks 12 domains for compliance")
        chunks = _load_accepted_chunks(conn)
        numeric = detect_numeric(chunks)
        found_domain = any("domain" in c["basis"] for c in numeric)
        if not found_domain:
            failures.append("numeric detector missed 32 vs 12 domains")

        # Test 2: same values do not contradict
        add_chunk("c_same1", "s_same1", "we have 5 tests in the suite")
        add_chunk("c_same2", "s_same2", "the suite contains 5 tests total")
        chunks = _load_accepted_chunks(conn)
        same_val = [c for c in detect_numeric(chunks)
                    if "c_same1" in (c["source"], c["target"])
                    and "c_same2" in (c["source"], c["target"])]
        if same_val:
            failures.append("numeric detector false-positive on identical values")

        # Test 3: negation flip detected
        base_words = ("the deployment pipeline runs integration tests "
                      "against the staging environment and validates "
                      "schema migrations before promoting to production "
                      "with automated rollback on failure detection")
        text_pos = base_words + " and the results are reliable"
        text_neg = base_words + " but the results are not reliable and never consistent"
        sh_pos = _simhash(text_pos)
        sh_neg = _simhash(text_neg)
        add_chunk("c_neg1", "s_neg1", text_pos, sh_pos)
        add_chunk("c_neg2", "s_neg2", text_neg, sh_neg)
        chunks = _load_accepted_chunks(conn)
        negation = detect_negation(chunks, hamming_threshold=12)
        found_neg = any(
            {"c_neg1", "c_neg2"} == {c["source"], c["target"]}
            for c in negation
        )
        if not found_neg:
            failures.append("negation detector missed polarity flip")

        # Test 4: recommendation conflict detected
        add_chunk("c_rec1", "s_rec1",
                  "we recommend using `pytest` for all test suites in the project")
        add_chunk("c_rec2", "s_rec2",
                  "avoid `pytest` and replace it with unittest for reliability")
        chunks = _load_accepted_chunks(conn)
        rec = detect_recommendation(chunks)
        found_rec = any("pytest" in c["basis"] for c in rec)
        if not found_rec:
            failures.append("recommendation detector missed pytest conflict")

        # Test 5: agreeing recommendations do not contradict
        add_chunk("c_agree1", "s_agree1",
                  "use `ruff` for linting as the standard tool")
        add_chunk("c_agree2", "s_agree2",
                  "adopt `ruff` and install it in every project")
        chunks = _load_accepted_chunks(conn)
        rec = detect_recommendation(chunks)
        agree_conflict = [c for c in rec
                          if "ruff" in c["basis"]
                          and {"c_agree1", "c_agree2"} == {c["source"], c["target"]}]
        if agree_conflict:
            failures.append("recommendation detector false-positive on agreement")

        # Test 6: detect() writes edges to DB
        conn.execute("DELETE FROM claim_edges")
        conn.commit()
        result = detect(conn)
        if result["total"] == 0:
            failures.append("detect() found zero contradictions with test data")
        edges = conn.execute(
            "SELECT count(*) FROM claim_edges WHERE edge_type='contradicts'"
        ).fetchone()[0]
        if edges == 0:
            failures.append("detect() wrote zero edges")

        # Test 7: report() returns rows
        rows = report(conn)
        if not isinstance(rows, list):
            failures.append("report() did not return a list")

        # Test 8: idempotent re-run does not duplicate edges
        first_count = edges
        detect(conn)
        second_count = conn.execute(
            "SELECT count(*) FROM claim_edges WHERE edge_type='contradicts'"
        ).fetchone()[0]
        if second_count != first_count:
            failures.append(f"re-run changed edge count: {first_count} -> {second_count}")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS contradict selftest (8 checks)")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("detect", "report", "selftest"),
                        default="detect", nargs="?")
    parser.add_argument("--db", default=None)
    parser.add_argument("--hamming", type=int, default=8)
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    conn = connect(args.db)
    init_schema(conn)

    if args.command == "detect":
        result = detect(conn, hamming_threshold=args.hamming)
        print(f"  numeric contradictions: {result['numeric']}")
        print(f"  negation contradictions: {result['negation']}")
        print(f"  recommendation conflicts: {result['recommendation']}")
        print(f"  total: {result['total']}, new edges written: {result['new_edges']}")
        conn.close()
        return 0

    if args.command == "report":
        rows = report(conn)
        if not rows:
            print("no open contradictions")
            conn.close()
            return 0
        print(f"{len(rows)} open contradiction(s):\n")
        for r in rows:
            print(f"  [{r['confidence']:.2f}] {r['basis']}")
            print(f"    A: {r['a_source']}")
            print(f"       {r['a_text'][:100]}...")
            print(f"    B: {r['b_source']}")
            print(f"       {r['b_text'][:100]}...")
            if r["resolution"]:
                print(f"    resolved: {r['resolution']}")
            print()
        conn.close()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
