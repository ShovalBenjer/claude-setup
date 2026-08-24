#!/usr/bin/env python3
"""
DEV project Jira activity analysis - 60-day window ending 2026-05-12.

Inputs: three Jira MCP search result files (updated/created/stale-active).
Output: self-contained HTML report with throughput, staleness, and verbosity signals.
"""
import json
import re
import html
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from statistics import median

TODAY = datetime(2026, 5, 12, tzinfo=timezone.utc)
RESULTS_DIR = Path("/home/shovalbe/.claude/projects/-home-shovalbe/ef1d5c3b-c953-4be4-8979-d3eb16e20cb3/tool-results")
OUT_PATH = Path("/home/shovalbe/docs/audits/jira-throughput-2026-05-12.html")

FILES = {
    "updated":  RESULTS_DIR / "mcp-atlassian-jira_search-1778576833324.txt",
    "created":  RESULTS_DIR / "mcp-atlassian-jira_search-1778576834212.txt",
    "stale":    RESULTS_DIR / "mcp-atlassian-jira_search-1778576834841.txt",
}


def load_jira_file(path: Path):
    raw = path.read_text()
    outer = json.loads(raw)
    inner = json.loads(outer["result"])
    return inner.get("issues", [])


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def days_since(dt):
    if not dt:
        return None
    return (TODAY - dt.astimezone(timezone.utc)).days


def name(field):
    if not field:
        return "Unassigned"
    return field.get("display_name") or "Unassigned"


# ---- Load + dedupe -----------------------------------------------------------

all_tix = {}
for label, p in FILES.items():
    for t in load_jira_file(p):
        # Prefer first instance; do not clobber (created/updated/stale may overlap)
        if t["key"] not in all_tix:
            all_tix[t["key"]] = t

# ---- Aggregate ---------------------------------------------------------------

people = defaultdict(lambda: {
    "reported_60d": 0,
    "reported_self_assigned": 0,
    "reported_to_others": 0,
    "reported_resolved_unassigned": 0,
    "reported_cycle_times": [],
    "assigned_active": 0,
    "assigned_resolved_60d": 0,
    "assigned_total_60d": 0,
    "stale_tix": [],
    "cycle_times": [],
    "desc_lens": [],
    "active_tix": [],
    "resolved_tix": [],
})

for key, t in all_tix.items():
    assignee = name(t.get("assignee"))
    reporter = name(t.get("reporter"))
    status_name = (t.get("status") or {}).get("name", "")
    status_cat = (t.get("status") or {}).get("category", "")
    created = parse_dt(t.get("created"))
    resolved = parse_dt(t.get("resolutiondate"))
    updated = parse_dt(t.get("updated"))
    summary = t.get("summary") or ""
    desc = t.get("description") or ""

    # Reporter activity (count creation in 60d)
    if created and days_since(created) is not None and days_since(created) <= 60:
        people[reporter]["reported_60d"] += 1
        if assignee == reporter:
            people[reporter]["reported_self_assigned"] += 1
        elif assignee != "Unassigned":
            people[reporter]["reported_to_others"] += 1

    # Reporter of resolved-as-Unassigned (proxy for de-facto execution credit)
    if (assignee == "Unassigned" and status_cat == "Done" and resolved
            and days_since(resolved) is not None and days_since(resolved) <= 60):
        people[reporter]["reported_resolved_unassigned"] += 1
        if created:
            cycle = (resolved - created).days
            if cycle >= 0:
                people[reporter]["reported_cycle_times"].append(cycle)

    # Assignee work
    if assignee != "Unassigned":
        people[assignee]["assigned_total_60d"] += 1
        if status_cat == "Done":
            ds_resolved = days_since(resolved)
            if ds_resolved is not None and ds_resolved <= 60:
                people[assignee]["assigned_resolved_60d"] += 1
                if created and resolved:
                    cycle = (resolved - created).days
                    if cycle >= 0:
                        people[assignee]["cycle_times"].append(cycle)
                people[assignee]["resolved_tix"].append({
                    "key": key, "summary": summary, "status": status_name,
                    "cycle": (resolved - created).days if (created and resolved) else None,
                })
        else:
            people[assignee]["assigned_active"] += 1
            people[assignee]["active_tix"].append({
                "key": key, "summary": summary, "status": status_name,
                "days_since_update": days_since(updated),
                "days_since_created": days_since(created),
            })
            ds_updated = days_since(updated)
            if ds_updated is not None and ds_updated > 30:
                people[assignee]["stale_tix"].append({
                    "key": key, "summary": summary, "status": status_name,
                    "days_stale": ds_updated,
                    "days_since_created": days_since(created),
                })

    # Description verbosity (per assignee, on assigned tickets only)
    if desc and assignee != "Unassigned":
        people[assignee]["desc_lens"].append(len(desc))

# ---- Derived metrics ---------------------------------------------------------

def safe_median(xs):
    return int(median(xs)) if xs else None

for who, m in people.items():
    m["median_cycle_days"] = safe_median(m["cycle_times"])
    m["median_reporter_cycle"] = safe_median(m["reported_cycle_times"])
    m["median_desc_len"]   = safe_median(m["desc_lens"])
    m["max_desc_len"]      = max(m["desc_lens"]) if m["desc_lens"] else 0
    m["stale_count"]       = len(m["stale_tix"])
    # Effective work-done credit: formal (assigned-resolved) + likely (reporter-of-resolved-unassigned)
    m["effective_resolved_60d"] = m["assigned_resolved_60d"] + m["reported_resolved_unassigned"]
    # reporter-vs-doer score: higher = creates more than completes
    completed = m["effective_resolved_60d"]
    reported  = m["reported_60d"]
    if reported + completed > 0:
        m["work_creator_ratio"] = round(reported / (reported + completed), 2)
    else:
        m["work_creator_ratio"] = None

# Drop "Unassigned" from human leaderboards (still useful in totals)
unassigned = people.pop("Unassigned", None)

# Sort views
by_effective = sorted(people.items(), key=lambda kv: -kv[1]["effective_resolved_60d"])
by_stale      = sorted(people.items(), key=lambda kv: -kv[1]["stale_count"])
by_reporting  = sorted(people.items(), key=lambda kv: -kv[1]["reported_60d"])

# All stale tickets across team
all_stale = []
for who, m in people.items():
    for s in m["stale_tix"]:
        all_stale.append({**s, "assignee": who})
all_stale.sort(key=lambda x: -x["days_stale"])

# ---- HTML --------------------------------------------------------------------

def esc(s):
    return html.escape(str(s)) if s is not None else ""


def row(*cells, cls=""):
    open_tag = f'<tr class="{cls}">' if cls else "<tr>"
    return open_tag + "".join(f"<td>{esc(c)}</td>" for c in cells) + "</tr>"


def th(*cells):
    return "<tr>" + "".join(f"<th>{esc(c)}</th>" for c in cells) + "</tr>"


def fmt_num(n):
    return "—" if n is None else str(n)


total_tix = len(all_tix)
total_resolved = sum(m["assigned_resolved_60d"] for m in people.values())
total_active   = sum(m["assigned_active"] for m in people.values())
total_stale    = sum(m["stale_count"] for m in people.values())
unassigned_resolved = unassigned["assigned_resolved_60d"] if unassigned else 0

throughput_rows = "\n".join(
    row(
        who,
        m["effective_resolved_60d"],
        m["assigned_resolved_60d"],
        m["reported_resolved_unassigned"],
        m["assigned_active"],
        m["stale_count"],
        (fmt_num(m["median_cycle_days"]) + " d") if m["median_cycle_days"] is not None
            else ((fmt_num(m["median_reporter_cycle"]) + " d") if m["median_reporter_cycle"] is not None else "—"),
        m["reported_60d"],
        fmt_num(m["work_creator_ratio"]),
        cls="stale-row" if m["stale_count"] >= 3 else "",
    )
    for who, m in by_effective if m["effective_resolved_60d"] > 0 or m["assigned_active"] > 0
)

reporter_rows = "\n".join(
    row(
        who,
        m["reported_60d"],
        m["reported_self_assigned"],
        m["reported_to_others"],
        m["reported_resolved_unassigned"],
        m["effective_resolved_60d"],
        fmt_num(m["work_creator_ratio"]),
    )
    for who, m in by_reporting if m["reported_60d"] > 0
)

stale_rows = "\n".join(
    row(
        s["assignee"],
        s["key"],
        s["summary"][:80] + ("…" if len(s["summary"]) > 80 else ""),
        s["status"],
        f"{s['days_stale']} d",
        f"{s['days_since_created']} d" if s["days_since_created"] is not None else "—",
        cls="warn" if s["days_stale"] > 60 else "",
    )
    for s in all_stale[:50]
)

verbosity_rows = "\n".join(
    row(
        who,
        len(m["desc_lens"]),
        fmt_num(m["median_desc_len"]),
        fmt_num(m["max_desc_len"]),
    )
    for who, m in sorted(people.items(), key=lambda kv: -(kv[1]["median_desc_len"] or 0))
    if m["desc_lens"]
)

html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DEV Jira activity signal — 60 days to 2026-05-12</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         margin: 2rem auto; max-width: 1100px; padding: 0 1rem; color: #1a1a1a; line-height: 1.5; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: .3rem; }}
  h2 {{ margin-top: 2.5rem; border-bottom: 1px solid #ccc; padding-bottom: .2rem; }}
  .caveat {{ background: #fff8dc; border-left: 4px solid #d4a017; padding: .8rem 1rem; margin: 1rem 0; }}
  .danger {{ background: #ffe9e9; border-left: 4px solid #b00; padding: .8rem 1rem; margin: 1rem 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 14px; }}
  th, td {{ border: 1px solid #ddd; padding: .45rem .6rem; text-align: left; vertical-align: top; }}
  th {{ background: #f2f2f2; }}
  tr.stale-row {{ background: #fff5f5; }}
  tr.warn {{ background: #ffdada; }}
  .meta {{ color: #666; font-size: 13px; }}
  .pill {{ display: inline-block; background: #eef; padding: .15rem .55rem; border-radius: 999px;
           font-size: 12px; margin-right: .3rem; }}
  code {{ background: #f4f4f4; padding: 1px 5px; border-radius: 3px; }}
</style>
</head>
<body>

<h1>DEV Jira activity signal — last 60 days</h1>
<p class="meta">
  Window: 2026-03-13 → 2026-05-12 &nbsp;·&nbsp;
  Project: <code>DEV</code> &nbsp;·&nbsp;
  Tickets in window: <strong>{total_tix}</strong> &nbsp;·&nbsp;
  Resolved (assigned): <strong>{total_resolved}</strong> &nbsp;·&nbsp;
  Resolved (unassigned): <strong>{unassigned_resolved}</strong> &nbsp;·&nbsp;
  Active assigned: <strong>{total_active}</strong> &nbsp;·&nbsp;
  Stale (&gt;30d no update): <strong>{total_stale}</strong>
</p>

<div class="caveat">
<strong>What this report is.</strong> Signals from Jira metadata only. It tells you who's <em>moving tickets through</em>,
who's <em>parking tickets</em>, and who's <em>creating work versus completing it</em>. It does <strong>not</strong>
tell you who is "lazy" or whose tickets are "AI-generated" — that requires reading the work product itself.
Engineering work at i-sdd lives in Azure DevOps, not here; people invisible to this report may be heads-down in code outside Jira.
</div>

<div class="danger">
<strong>Use as input to a conversation, not as a verdict.</strong> If you act on this, pair every number with the question
"is this person supposed to be using Jira?" Several visible patterns (e.g. tickets resolved against <em>Unassigned</em>) suggest
the team's workflow doesn't reliably assign before resolving — that's a process gap, not necessarily individual behavior.
</div>

<div class="caveat">
<strong>Workflow gap detected.</strong> {unassigned_resolved} of {total_tix} tickets ({round(100*unassigned_resolved/total_tix)}%)
were resolved while assigned to <em>Unassigned</em>. The team is not assigning owners before closing.
This makes formal "Resolved by X" mostly empty. The <code>Effective</code> column below adds back
"reporter of resolved-as-Unassigned" — a proxy for who likely actually did the work, since people typically
self-report and self-resolve their own quick fixes.
</div>

<h2>1. Throughput leaderboard (effective work credit)</h2>
<p><code>Effective</code> = formally assigned-and-resolved + reported-and-resolved-as-Unassigned. The latter is a <em>proxy</em>
for de-facto execution: if you reported it and it closed against nobody, you likely did it yourself. Could also mean someone
else cleaned it up silently — open a sample to check. <code>Creator ratio</code> = reported / (reported + effective_resolved):
closer to 1 means they delegate, closer to 0 means they execute.</p>
<table>
  {th("Person", "Effective", "Formal assigned", "Self-resolved (Unassigned)", "Active", "Stale ≥30d", "Median cycle", "Reported 60d", "Creator ratio")}
  {throughput_rows}
</table>

<h2>2. Reporter activity (who creates work)</h2>
<p>Tickets they <strong>filed</strong> in the last 60 days. High <code>to others</code> + low <code>resolved</code> = task-distributor.
Doesn't make them lazy; can mean they're the PM or escalation owner.</p>
<table>
  {th("Reporter", "Reported 60d", "Self-assigned", "To others", "Self-resolved (Unassigned)", "Effective resolved", "Creator ratio")}
  {reporter_rows}
</table>

<h2>3. Stale ticket alert (top 50, sorted by oldest)</h2>
<p>Assigned tickets in active status with no update in 30+ days. The <em>process</em> red flag, not necessarily the <em>person</em>.</p>
<table>
  {th("Assignee", "Key", "Summary", "Status", "Days stale", "Days since created")}
  {stale_rows}
</table>

<h2>4. Description verbosity signal (per assignee)</h2>
<p>Median and max description length of tickets <strong>assigned to them</strong>. Suspiciously long, structured descriptions
on routine fix-tickets <em>can</em> be an AI-template tell — but it can also just be a thorough author. <strong>Treat as a sample
selector, not evidence.</strong> Open the high-verbosity tickets and read them.</p>
<table>
  {th("Assignee", "Tickets with desc", "Median chars", "Max chars")}
  {verbosity_rows}
</table>

<h2>5. What the data can <em>not</em> tell you</h2>
<ul>
  <li><strong>Whether tickets were AI-drafted.</strong> Jira metadata has no provenance field. Verbosity + formulaic structure
      across many tickets <em>suggests</em> templating; only opening the tickets confirms it.</li>
  <li><strong>Whether someone is doing the work elsewhere.</strong> i-sdd engineering tracks on Azure DevOps. Anyone whose
      delivery is code-and-PRs will look idle here.</li>
  <li><strong>Whether assignee changed mid-flight.</strong> No changelog was fetched. Tickets resolved by <em>Unassigned</em>
      ({unassigned_resolved} of {total_tix}) hide who actually did the work.</li>
  <li><strong>Comment/transition density.</strong> Not fetched in this pass. Add <code>expand=changelog</code> and per-ticket
      comments for the next layer.</li>
  <li><strong>Sprint commitments.</strong> No sprint data pulled. Throughput here is calendar-time, not
      sprint-commitment-vs-delivered.</li>
</ul>

<h2>6. Recommended next steps</h2>
<ol>
  <li>For each name with high <code>Creator ratio</code> (&gt;0.7), confirm role — should they be reporting or executing?</li>
  <li>For each <code>Stale ≥30d</code> entry, audit the status. "Ready for QA" 60+ days = QA bottleneck, not assignee lazy.</li>
  <li>For high-verbosity assignees, read 3-5 of their tickets directly. If the descriptions are templated boilerplate,
      ask the team to standardize a real template (so the signal goes to zero).</li>
  <li>Fix the <strong>Unassigned resolved</strong> hole. Require assignee before transition to Done — that single change
      makes the next report 10× more honest.</li>
</ol>

<p class="meta">Generated 2026-05-12 from <code>~/docs/audits/analyze_jira_2026-05-12.py</code>.
Data source: three Jira MCP search results in <code>tool-results/</code>. No tickets modified.</p>

</body>
</html>
"""

OUT_PATH.write_text(html_out)
print(f"Wrote {OUT_PATH}")
print(f"Tickets in window: {total_tix}")
print(f"People with activity: {len(people)}")
print(f"Top 5 by effective throughput: {[(k, v['effective_resolved_60d']) for k, v in by_effective[:5]]}")
print(f"Top 5 by stale: {[(k, v['stale_count']) for k, v in by_stale[:5]]}")
print(f"Top 5 reporters: {[(k, v['reported_60d']) for k, v in by_reporting[:5]]}")
