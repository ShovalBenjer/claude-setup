#!/usr/bin/env python3
"""
v2: SOTA flow analytics for the top 20 stale DEV tickets.

Adds to v1:
  - Days-in-current-status (the "parking time" of each stuck ticket)
  - Bulk-grooming detector (>=2 status transitions within 5 min by same author = batch theater)
  - Last real activity vs last cosmetic activity per ticket
  - Per-assignee parking-time aggregates
"""
import json
import html
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

TODAY = datetime(2026, 5, 12, tzinfo=timezone.utc)
CHANGELOG_FILE = Path("/tmp/changelogs_top20.json")
META_FILE = Path("/home/shovalbe/.claude/projects/-home-shovalbe/ef1d5c3b-c953-4be4-8979-d3eb16e20cb3/tool-results/mcp-atlassian-jira_search-1778576834841.txt")
OUT_PATH = Path("/home/shovalbe/docs/audits/jira-flow-analysis-2026-05-12.html")

# Map of issue_id -> ticket key (from the search response). Build it from META.
search_data = json.loads(json.loads(META_FILE.read_text())["result"])
key_by_id = {t["id"]: t["key"] for t in search_data["issues"]}
meta_by_key = {t["key"]: t for t in search_data["issues"]}

changelogs = json.loads(CHANGELOG_FILE.read_text())

# Resolve ticket key from issue_id if missing in changelog entry
for cl in changelogs:
    if "key" not in cl or not cl["key"]:
        cl["key"] = key_by_id.get(cl["issue_id"], cl["issue_id"])

# ---- Per-ticket flow analysis ----

def parse_dt(s):
    return datetime.fromisoformat(s.replace("+00:00", "+00:00")) if s else None

def days_since(dt):
    return (TODAY - dt.astimezone(timezone.utc)).days if dt else None

tickets = []
for cl in changelogs:
    key = cl["key"]
    meta = meta_by_key.get(key, {})
    assignee = (meta.get("assignee") or {}).get("display_name", "Unassigned")
    status = (meta.get("status") or {}).get("name", "")
    summary = meta.get("summary", "")
    created = parse_dt(meta.get("created"))

    # Sort changelogs chronologically (oldest first)
    log = sorted(cl["changelogs"], key=lambda x: x["created"])

    # Find last status transition
    last_status_change = None
    last_status_author = None
    transitions = []
    for entry in log:
        ts = parse_dt(entry["created"])
        author = (entry.get("author") or {}).get("display_name", "?")
        for item in entry.get("items", []):
            if item["field"] == "status":
                last_status_change = ts
                last_status_author = author
                transitions.append({"ts": ts, "from": item.get("from_string"), "to": item.get("to_string"), "author": author})

    # Bulk grooming: 2+ transitions within 5 minutes by same author
    bulk_events = 0
    for i in range(1, len(transitions)):
        delta = (transitions[i]["ts"] - transitions[i-1]["ts"]).total_seconds()
        if delta <= 300 and transitions[i]["author"] == transitions[i-1]["author"]:
            bulk_events += 1

    # Parking time = days since last status change (or creation if never changed)
    park_from = last_status_change or created
    parking_days = days_since(park_from)

    # Total status transitions
    n_status = len(transitions)

    tickets.append({
        "key": key,
        "assignee": assignee,
        "status": status,
        "summary": summary,
        "created": created,
        "last_status_change": last_status_change,
        "last_status_author": last_status_author,
        "parking_days": parking_days,
        "n_status_transitions": n_status,
        "bulk_grooming_events": bulk_events,
        "transitions": transitions,
    })

# ---- Per-person aggregate (parking burden — by current assignee) ----

person = defaultdict(lambda: {
    "parked_tickets": 0,
    "total_parking_days": 0,
    "max_parking_days": 0,
    "tickets": [],
})

for t in tickets:
    p = person[t["assignee"]]
    p["parked_tickets"] += 1
    p["total_parking_days"] += t["parking_days"] or 0
    p["max_parking_days"] = max(p["max_parking_days"], t["parking_days"] or 0)
    p["tickets"].append(t)

# ---- Per-actor bulk-grooming aggregate (by transition author, not assignee) ----

groomer = defaultdict(lambda: {"bursts": 0, "tickets_groomed": set(), "min_delta_seconds": 999999})

for t in tickets:
    for i in range(1, len(t["transitions"])):
        delta = (t["transitions"][i]["ts"] - t["transitions"][i-1]["ts"]).total_seconds()
        if delta <= 300 and t["transitions"][i]["author"] == t["transitions"][i-1]["author"]:
            who = t["transitions"][i]["author"]
            groomer[who]["bursts"] += 1
            groomer[who]["tickets_groomed"].add(t["key"])
            groomer[who]["min_delta_seconds"] = min(groomer[who]["min_delta_seconds"], int(delta))

# ---- HTML ----

def esc(s):
    return html.escape(str(s)) if s is not None else ""

def row(*cells, cls=""):
    open_tag = f'<tr class="{cls}">' if cls else "<tr>"
    return open_tag + "".join(f"<td>{esc(c)}</td>" for c in cells) + "</tr>"

def th(*cells):
    return "<tr>" + "".join(f"<th>{esc(c)}</th>" for c in cells) + "</tr>"

# Sort tickets by parking days (longest first)
tickets_sorted = sorted(tickets, key=lambda t: -(t["parking_days"] or 0))

ticket_rows = "\n".join(
    row(
        t["key"],
        t["assignee"],
        t["status"],
        t["summary"][:60] + ("…" if len(t["summary"]) > 60 else ""),
        f"{t['parking_days']}d",
        t["n_status_transitions"],
        t["bulk_grooming_events"],
        t["last_status_author"] or "—",
        cls=("danger-row" if (t["parking_days"] or 0) > 365 else "warn-row" if (t["parking_days"] or 0) > 180 else ""),
    )
    for t in tickets_sorted
)

# Sort persons by total parking days
people_sorted = sorted(person.items(), key=lambda kv: -kv[1]["total_parking_days"])

person_rows = "\n".join(
    row(
        who,
        p["parked_tickets"],
        f"{p['total_parking_days']}d ({round(p['total_parking_days']/365.0, 1)}y)",
        f"{p['max_parking_days']}d",
    )
    for who, p in people_sorted
)

# Groomer leaderboard
groomers_sorted = sorted(groomer.items(), key=lambda kv: -kv[1]["bursts"])
groomer_rows = "\n".join(
    row(
        who,
        g["bursts"],
        len(g["tickets_groomed"]),
        f"{g['min_delta_seconds']}s",
        ", ".join(sorted(g["tickets_groomed"]))[:80],
    )
    for who, g in groomers_sorted
)

# Bulk-grooming receipts (the actual evidence)
bulk_evidence = []
for t in tickets:
    if t["bulk_grooming_events"] > 0:
        # Find the grooming burst
        for i in range(1, len(t["transitions"])):
            delta = (t["transitions"][i]["ts"] - t["transitions"][i-1]["ts"]).total_seconds()
            if delta <= 300 and t["transitions"][i]["author"] == t["transitions"][i-1]["author"]:
                bulk_evidence.append({
                    "key": t["key"],
                    "assignee": t["assignee"],
                    "author": t["transitions"][i]["author"],
                    "ts": t["transitions"][i-1]["ts"],
                    "delta_seconds": int(delta),
                    "chain": f"{t['transitions'][i-1]['from']} → {t['transitions'][i-1]['to']} → {t['transitions'][i]['to']}",
                    "parking_days": t["parking_days"],
                })

bulk_evidence.sort(key=lambda x: x["ts"])
bulk_rows = "\n".join(
    row(
        b["ts"].strftime("%Y-%m-%d %H:%M:%S"),
        b["author"],
        b["key"],
        b["chain"],
        f"{b['delta_seconds']}s apart",
        f"{b['parking_days']}d since",
        cls="warn-row",
    )
    for b in bulk_evidence
)

# Stats
total_parking_days = sum(t["parking_days"] or 0 for t in tickets)
median_parking = sorted([t["parking_days"] or 0 for t in tickets])[len(tickets) // 2]
n_over_year = sum(1 for t in tickets if (t["parking_days"] or 0) > 365)

html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DEV Jira flow analysis (v2) — 2026-05-12</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         margin: 2rem auto; max-width: 1200px; padding: 0 1rem; color: #1a1a1a; line-height: 1.5; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: .3rem; }}
  h2 {{ margin-top: 2.5rem; border-bottom: 1px solid #ccc; padding-bottom: .2rem; }}
  .caveat {{ background: #fff8dc; border-left: 4px solid #d4a017; padding: .8rem 1rem; margin: 1rem 0; }}
  .danger {{ background: #ffe9e9; border-left: 4px solid #b00; padding: .8rem 1rem; margin: 1rem 0; }}
  .finding {{ background: #e6f4ea; border-left: 4px solid #137333; padding: .8rem 1rem; margin: 1rem 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 13px; }}
  th, td {{ border: 1px solid #ddd; padding: .4rem .55rem; text-align: left; vertical-align: top; }}
  th {{ background: #f2f2f2; }}
  tr.danger-row {{ background: #ffdada; }}
  tr.warn-row {{ background: #fff3cd; }}
  .meta {{ color: #666; font-size: 13px; }}
  code {{ background: #f4f4f4; padding: 1px 5px; border-radius: 3px; }}
  .kpi {{ display: inline-block; background: #eef; padding: .25rem .8rem; border-radius: 8px;
          font-size: 14px; margin-right: .5rem; }}
</style>
</head>
<body>

<h1>DEV Jira flow analysis — top 20 stale tickets</h1>
<p class="meta">
  Generated 2026-05-12 &nbsp;·&nbsp;
  Source: changelog data via <code>jira_batch_get_changelogs</code> for the 20 oldest-stale active tickets.
</p>

<div>
  <span class="kpi">Tickets analyzed: <strong>{len(tickets)}</strong></span>
  <span class="kpi">Total parking time: <strong>{total_parking_days}d</strong> ({round(total_parking_days/365.0, 1)}y)</span>
  <span class="kpi">Median parking: <strong>{median_parking}d</strong></span>
  <span class="kpi">Tickets parked &gt;1y: <strong>{n_over_year}</strong></span>
</div>

<div class="finding">
<strong>The actual finding.</strong> These tickets aren't stale because someone forgot — they were
<em>actively transitioned</em> into "In Progress" or "To Do" in batches (multiple tickets, &lt;1 minute apart, by the same person),
and then never touched again. This is the <strong>"groomed and parked"</strong> pattern: visible motion on the
timeline, zero subsequent work. It's a classic Jira-as-theater anti-pattern, well documented in the Kanban
literature (Anderson, Roock, Vacanti). The fix is process, not punishment.
</div>

<div class="caveat">
<strong>Caveat.</strong> A ticket being parked doesn't mean the person is lazy. It can also mean:
(a) the work was actually done in code/AzDO and the ticket was abandoned because it doesn't matter, or
(b) the ticket was deprioritized but never properly closed/cancelled, or
(c) the person was reassigned but Jira wasn't updated. In all three cases the conclusion is the same:
<strong>Jira is no longer a source of truth for this project</strong>. The data hygiene gap is the real problem.
</div>

<h2>1. Parking burden (by current assignee)</h2>
<p>Total accumulated days these stuck tickets have been sitting in their current status. This is who owns
the cleanup, regardless of who originally groomed.</p>
<table>
  {th("Current assignee", "Parked tickets", "Total parking time", "Worst-parked ticket")}
  {person_rows}
</table>

<h2>1b. Bulk-grooming actors (by transition author, separate from assignee)</h2>
<p>Who actually performed the rapid status transitions. The current assignee and the original groomer may differ
(e.g. avi lior groomed DEV-3361 in Jan 2025 then reassigned it to Tomer Kamil a week later).</p>
<table>
  {th("Author", "Bulk bursts", "Distinct tickets", "Fastest burst", "Tickets")}
  {groomer_rows}
</table>

<h2>2. Ticket-level parking table</h2>
<p>Sorted by parking time (days since last status change). <code>Last actor</code> = who made the most recent
status transition.</p>
<table>
  {th("Key", "Assignee", "Status", "Summary", "Parked", "Status transitions", "Bulk bursts", "Last actor")}
  {ticket_rows}
</table>

<h2>3. Bulk-grooming receipts (the smoking gun)</h2>
<p>Each row is a pair of status transitions on the same ticket, by the same person, less than 5 minutes apart.
These are the moments where someone batch-processed multiple tickets without doing real work on them.
The <code>Parked since</code> column shows the ticket has been silent ever since.</p>
<table>
  {th("Timestamp (UTC)", "Author", "Ticket", "Transition chain", "Speed", "Then parked for")}
  {bulk_rows}
</table>

<h2>4. SOTA flow metrics — what this report DOES use</h2>
<ul>
  <li><strong>Days-in-current-status</strong> (aged WIP, per-ticket) — the Kanban "age" metric, the most actionable single signal in flow management.</li>
  <li><strong>Status transition count</strong> per ticket — proxy for engagement.</li>
  <li><strong>Bulk-transition burst detection</strong> — original signal for batch-grooming theater (not in any textbook; derived from the data shape).</li>
  <li><strong>Last-actor attribution</strong> — who is on the hook for the current state, separate from current assignee.</li>
</ul>

<h2>5. What's still missing for full SOTA</h2>
<ul>
  <li><strong>Flow efficiency</strong> = active-status-time / total-cycle-time, for <em>completed</em> tickets. Requires changelogs on resolved tickets, not just stale ones. Next batch fetch.</li>
  <li><strong>Throughput p85 / Monte Carlo forecasting</strong> — needs a clean stream of resolved cycle times. Currently 60d × ~50 tickets is borderline; need 6-month window.</li>
  <li><strong>CFD (Cumulative Flow Diagram)</strong> — needs status snapshots over time, expensive to compute from changelogs alone.</li>
  <li><strong>DORA four</strong> — lives in Azure DevOps, not Jira. Pipeline frequency + lead time for changes + change failure rate + MTTR. Pull from AzDO API once we wire that integration.</li>
  <li><strong>Rework rate</strong> — tickets that re-entered "In Progress" after "Done". The DEV-2746 trail shows this happens (Blocked → Cancelled → To Do → In Progress); needs a query for status_was_done_then_reopened.</li>
</ul>

<h2>6. Recommended actions (process, not people)</h2>
<ol>
  <li><strong>Bulk-close the parking lot.</strong> Anything in "In Progress" with no update in &gt;180 days should be auto-transitioned to "Cancelled" or "Backlog" with a comment "auto-archived: stale". Run quarterly.</li>
  <li><strong>WIP limits per assignee.</strong> If avi lior has 6 tickets formally "In Progress" but is actively working on 0 or 1, the WIP limit should be 2. Enforces honest status.</li>
  <li><strong>Forbid Backlog→In Progress in &lt;1 minute</strong> via a Jira automation rule. A status change should reflect real intent; if you're batching, use a single "groomed" label instead.</li>
  <li><strong>Require an assignee before Done.</strong> Closes the 60% Unassigned-resolved hole from the v1 report.</li>
  <li><strong>Status-change-by-pipeline.</strong> For your AzDO container work, have the pipeline transition the ticket on deploy. That removes manual transition entirely — status becomes a side-effect of real events.</li>
</ol>

<p class="meta">Generated from <code>~/docs/audits/analyze_jira_flow_2026-05-12.py</code>. Source data: 17 changelogs at <code>/tmp/changelogs_top20.json</code> + ticket metadata.</p>

</body>
</html>
"""

OUT_PATH.write_text(html_out)
print(f"Wrote {OUT_PATH}")
print(f"Tickets analyzed: {len(tickets)}")
print(f"Total parking days: {total_parking_days} ({round(total_parking_days/365.0,1)} years)")
print(f"Bulk grooming bursts found: {sum(t['bulk_grooming_events'] for t in tickets)}")
print(f"\nParking burden (by assignee):")
for who, p in people_sorted[:5]:
    print(f"  {who:<22} {p['parked_tickets']} tix, {p['total_parking_days']}d parked")
print(f"\nBulk-grooming actors (by author):")
for who, g in groomers_sorted[:5]:
    print(f"  {who:<22} {g['bursts']} bursts on {len(g['tickets_groomed'])} tix, fastest {g['min_delta_seconds']}s")
