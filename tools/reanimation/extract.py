#!/usr/bin/env python3
"""Reanimation jutsu, stage 0: extract one contact's WhatsApp thread to a local corpus.

Reads the decrypted store (wa_decrypt.py output, see the whatsapp-query skill) and
writes ~/.intent/reanimation/<slug>/corpus.jsonl, one row per message. The store is
a linked-device re-sync with NO per-row sender direction (verified 2026-08-13: the
message table is rowid,id,chatId,timestamp,text and nothing else), so a thread is
both voices interleaved. Each corpus row is tagged direction:"unknown" so no
downstream stage can silently claim it isolated one speaker.

HARD BOUNDARY (whatsapp-query skill): these are private messages, third parties
included. The corpus stays under ~/.intent (gitignored home, never the repo), never
committed, never sent anywhere raw. Stage 2 tokenizes before any model call.

Local only, read only. Usage:
  extract.py --db <decrypted-dir> --contact <name-or-chatId> [--slug <name>]
  extract.py --db <decrypted-dir> --top <N>      # busiest N one-on-one chats
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

OUT_ROOT = Path.home() / ".intent" / "reanimation"


def slugify(name: str) -> str:
    n = unicodedata.normalize("NFKD", name)
    n = re.sub(r"[^\w֐-׿-]+", "-", n, flags=re.UNICODE).strip("-")
    return n or "contact"


def load_names(con: sqlite3.Connection) -> dict[str, str]:
    names: dict[str, str] = {}
    try:
        for r in con.execute("SELECT chatId, displayName FROM UserStatuses"):
            if r["displayName"]:
                names[r["chatId"]] = r["displayName"]
    except sqlite3.Error:
        pass
    return names


def one_on_one_ranked(msg: sqlite3.Connection) -> list[tuple[str, int]]:
    rows = msg.execute(
        "SELECT chatId, COUNT(*) c FROM message "
        "WHERE chatId NOT LIKE '%@g.us' GROUP BY chatId ORDER BY c DESC")
    return [(r["chatId"], r["c"]) for r in rows]


def resolve(msg: sqlite3.Connection, names: dict[str, str], who: str) -> list[str]:
    present = {r["chatId"] for r in msg.execute("SELECT DISTINCT chatId FROM message")}
    if "@" in who:
        return [who] if who in present else []
    hits = [cid for cid, nm in names.items() if who.lower() in nm.lower()]
    return [c for c in hits if c in present]


def extract_one(msg: sqlite3.Connection, chat_id: str, label: str, slug: str) -> int:
    out_dir = OUT_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus = out_dir / "corpus.jsonl"
    n = 0
    with corpus.open("w", encoding="utf-8") as f:
        for r in msg.execute(
                "SELECT timestamp, text FROM message WHERE chatId=? "
                "ORDER BY CAST(timestamp AS INTEGER)", (chat_id,)):
            text = (r["text"] or "").strip()
            if not text:
                continue
            f.write(json.dumps({
                "ts": r["timestamp"], "text": text,
                "chat_id": chat_id, "contact": label,
                "direction": "unknown",
            }, ensure_ascii=False) + "\n")
            n += 1
    (out_dir / "meta.json").write_text(json.dumps({
        "contact": label, "chat_id": chat_id, "messages": n,
        "direction_known": False,
        "note": "linked-device re-sync has no sender column; thread is both voices",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, help="decrypted store dir (wa_decrypt output)")
    ap.add_argument("--contact", help="name substring or chatId")
    ap.add_argument("--slug", help="output dir name; defaults from the contact label")
    ap.add_argument("--top", type=int, help="extract the busiest N one-on-one chats")
    a = ap.parse_args(argv)

    gs = os.path.join(a.db, "genericStorage.dec.db")
    ct = os.path.join(a.db, "contacts.dec.db")
    if not os.path.isfile(gs):
        print(f"messages DB not found at {gs}; run wa_decrypt.py first", file=sys.stderr)
        return 2
    msg = sqlite3.connect(gs); msg.row_factory = sqlite3.Row
    names: dict[str, str] = {}
    if os.path.isfile(ct):
        c = sqlite3.connect(ct); c.row_factory = sqlite3.Row
        names = load_names(c)

    try:
        if a.top:
            done = 0
            for cid, count in one_on_one_ranked(msg):
                label = names.get(cid, cid)
                n = extract_one(msg, cid, label, slugify(label))
                print(f"{n:>6}  {label}  -> {OUT_ROOT / slugify(label)}")
                done += 1
                if done >= a.top:
                    break
            return 0

        if not a.contact:
            print("give --contact or --top", file=sys.stderr)
            return 2
        cids = resolve(msg, names, a.contact)
        if not cids:
            print(f"no chat matching {a.contact!r}", file=sys.stderr)
            return 1
        cid = cids[0]
        label = names.get(cid, cid)
        slug = a.slug or slugify(label)
        n = extract_one(msg, cid, label, slug)
        print(f"{n} messages -> {OUT_ROOT / slug}")
        return 0
    except sqlite3.Error as e:
        print(f"unexpected store schema: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
