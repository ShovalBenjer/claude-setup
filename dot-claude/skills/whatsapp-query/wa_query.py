# -*- coding: utf-8 -*-
"""Query the decrypted WhatsApp Desktop store produced by wa_decrypt.py.

Read-only. Resolves chat IDs to contact names via contacts.dec.db.

Examples:
  uv run python wa_query.py contacts               # list contacts + message counts
  uv run python wa_query.py contacts עידו           # filter contacts by name
  uv run python wa_query.py stats עידו              # thread size + date range
  uv run python wa_query.py search "איטליה" --contact עידו --limit 40
  uv run python wa_query.py search "bench" --from 2025-08-01 --to 2025-10-01
  uv run python wa_query.py thread עידו --from 2026-07-25 --limit 200

Notes / limits:
  - The message table has no per-row sender direction (this is a linked-device
    re-sync), so thread output is chronological text without a ME/THEM column.
  - Group chats (chatId ending @g.us) sometimes carry a "~Sender:" prefix in the
    text itself.
  - Timestamps are unix seconds (occasionally milliseconds); both are handled.
"""
import sqlite3, sys, os, argparse, datetime

DEFAULT_DB = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "wa-decrypted")


def ts(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return str(v)
    if v > 1e12:
        v //= 1000
    try:
        return datetime.datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return str(v)


def to_epoch(datestr):
    return int(datetime.datetime.strptime(datestr, "%Y-%m-%d").timestamp())


def load_names(dbdir):
    """chatId -> best display name, from contacts.dec.db UserStatuses."""
    path = os.path.join(dbdir, "contacts.dec.db")
    names = {}
    if not os.path.exists(path):
        return names
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        for r in con.execute("SELECT Jid,DbLid,ContactName,FirstName,PushName FROM UserStatuses"):
            nm = r["ContactName"] or r["FirstName"] or r["PushName"]
            if not nm:
                continue
            for key in (r["DbLid"], r["Jid"]):
                if key:
                    names[key] = nm
    except sqlite3.Error:
        pass
    con.close()
    return names


def open_msgs(dbdir):
    path = os.path.join(dbdir, "genericStorage.dec.db")
    if not os.path.exists(path):
        sys.exit(f"messages DB not found: {path}\nRun wa_decrypt.py first.")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def resolve_chatids(con, names, who):
    """Return list of chatIds whose contact name contains `who` (case-insensitive),
    or [who] if it already looks like a chatId."""
    if "@" in who:
        return [who]
    exact = [cid for cid, nm in names.items() if (nm or "").lower() == who.lower()]
    hits = exact or [cid for cid, nm in names.items() if who.lower() in (nm or "").lower()]
    # keep only chatIds that actually appear in messages; prefer the busiest thread
    present = [(cid, con.execute("SELECT COUNT(*) FROM message WHERE chatId=?", (cid,)).fetchone()[0])
              for cid in hits]
    present = [(cid, n) for cid, n in present if n > 0]
    present.sort(key=lambda x: -x[1])
    return [cid for cid, _ in present] or hits


def cmd_contacts(con, names, args):
    rows = con.execute("SELECT chatId, COUNT(*) c, MAX(CAST(timestamp AS INTEGER)) last "
                       "FROM message GROUP BY chatId ORDER BY c DESC").fetchall()
    q = (args.query or "").lower()
    shown = 0
    for r in rows:
        nm = names.get(r["chatId"], "")
        label = nm or r["chatId"]
        if q and q not in label.lower():
            continue
        kind = "group" if r["chatId"].endswith("@g.us") else "chat"
        print(f"{r['c']:>6}  {ts(r['last'])}  [{kind}] {label}  ({r['chatId']})")
        shown += 1
        if shown >= args.limit:
            break


def cmd_stats(con, names, args):
    cids = resolve_chatids(con, names, args.who) if args.who else None
    where, params = ("WHERE chatId IN (%s)" % ",".join("?" * len(cids)), cids) if cids else ("", [])
    r = con.execute(f"SELECT COUNT(*) c, MIN(CAST(timestamp AS INTEGER)) a, MAX(CAST(timestamp AS INTEGER)) b "
                    f"FROM message {where}", params).fetchone()
    label = ", ".join(names.get(c, c) for c in cids) if cids else "ALL CHATS"
    print(f"{label}: {r['c']} messages, {ts(r['a'])} -> {ts(r['b'])}")


def cmd_search(con, names, args):
    where = ["text LIKE ?"]
    params = [f"%{args.term}%"]
    if args.contact:
        cids = resolve_chatids(con, names, args.contact)
        if not cids:
            sys.exit(f"no contact matching {args.contact!r}")
        where.append("chatId IN (%s)" % ",".join("?" * len(cids)))
        params += cids
    if args.from_:
        where.append("CAST(timestamp AS INTEGER) >= ?"); params.append(to_epoch(args.from_))
    if args.to:
        where.append("CAST(timestamp AS INTEGER) <= ?"); params.append(to_epoch(args.to))
    sql = ("SELECT chatId, timestamp, text FROM message WHERE " + " AND ".join(where) +
           " ORDER BY CAST(timestamp AS INTEGER) LIMIT ?")
    params.append(args.limit)
    n = 0
    for r in con.execute(sql, params):
        nm = names.get(r["chatId"], r["chatId"])
        body = (r["text"] or "").replace("\n", " ")
        print(f"{ts(r['timestamp'])}  [{nm}]  {body[:200]}")
        n += 1
    print(f"\n({n} hits)")


def cmd_thread(con, names, args):
    cids = resolve_chatids(con, names, args.who)
    if not cids:
        sys.exit(f"no contact matching {args.who!r}")
    where = ["chatId IN (%s)" % ",".join("?" * len(cids))]
    params = list(cids)
    if args.from_:
        where.append("CAST(timestamp AS INTEGER) >= ?"); params.append(to_epoch(args.from_))
    if args.to:
        where.append("CAST(timestamp AS INTEGER) <= ?"); params.append(to_epoch(args.to))
    sql = ("SELECT timestamp, text FROM message WHERE " + " AND ".join(where) +
           " ORDER BY CAST(timestamp AS INTEGER) LIMIT ?")
    params.append(args.limit)
    for r in con.execute(sql, params):
        body = (r["text"] or "").replace("\n", " ")
        print(f"{ts(r['timestamp'])}  {body[:300]}")


def main():
    p = argparse.ArgumentParser(description="Query decrypted WhatsApp store (read-only).")
    p.add_argument("--db", default=DEFAULT_DB, help="decrypted DB dir (default: %%LOCALAPPDATA%%\\Temp\\wa-decrypted)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("contacts"); c.add_argument("query", nargs="?"); c.add_argument("--limit", type=int, default=60)
    s = sub.add_parser("stats"); s.add_argument("who", nargs="?")
    se = sub.add_parser("search"); se.add_argument("term"); se.add_argument("--contact")
    se.add_argument("--from", dest="from_"); se.add_argument("--to"); se.add_argument("--limit", type=int, default=50)
    th = sub.add_parser("thread"); th.add_argument("who")
    th.add_argument("--from", dest="from_"); th.add_argument("--to"); th.add_argument("--limit", type=int, default=200)

    args = p.parse_args()
    names = load_names(args.db)
    con = open_msgs(args.db)
    {"contacts": cmd_contacts, "stats": cmd_stats, "search": cmd_search, "thread": cmd_thread}[args.cmd](con, names, args)
    con.close()


if __name__ == "__main__":
    main()
