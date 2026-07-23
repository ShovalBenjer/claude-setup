#!/usr/bin/env python3
"""Jira reminder refresher (cron).

Pulls Shoval's open tickets from qboservices.atlassian.net, flags the ones that
need a human action (stale status / new comment by someone else), writes a digest
to ~/.claude/jira/reminders.json (read cheaply by the SessionStart banner), and
emails a summary to shoval.be@i-sdd.com via Brevo SMTP.

Secrets (Jira token, SMTP login/password) are read from Azure Key Vault 'Shoval'
at runtime — never stored on disk. Requires an active `az login` session.

Writes nothing back to Jira. Status moves / comments stay human-in-the-loop.
"""
from __future__ import annotations

import base64
import html
import json
import os
import smtplib
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

JIRA_URL = "https://qboservices.atlassian.net"
JIRA_USER = "shoval.be@i-sdd.com"
MAIL_TO = "shoval.be@i-sdd.com"
MAIL_FROM = "shoval.be@i-sdd.com"
BREVO_HOST = "smtp-relay.brevo.com"
BREVO_PORT = 587

VAULT = "Shoval"
STATE_DIR = Path.home() / ".claude" / "jira"
DIGEST_PATH = STATE_DIR / "reminders.json"
AUTH_FLAG = STATE_DIR / "az-auth-needed.flag"  # surfaced by the SessionStart banner
AZ_RG = "AZAI_group"
AZ_OWNER = "shoval.be@i-sdd.com"

# Existing telemetry only. Do not create Log Analytics, action groups, alerts, or exports here.
APP_INSIGHTS_COMPONENTS = [
    {"label": "CS agents dev", "component": "func-cs-agents-dev"},
    {"label": "QC telephony prod", "component": "func-qc-telephony-prod-insights"},
    {"label": "Training platform", "component": "sales-training-insights"},
    {"label": "Axia/Seekapa CRM", "component": "axia-seekapa-crm-insights"},
]

INTERESTING_ACTIVITY = (
    "/write", "/delete", "/action", "/stop/", "/restart/", "/start/",
    "roleassignments", "listkeys", "regeneratekey", "config",
)

WEB_METRICS = "Requests,Http4xx,Http5xx,BytesReceived,BytesSent,AverageResponseTime"
STATIC_SITE_METRICS = "SiteHits,SiteErrors,FunctionHits,FunctionErrors,CdnRequestCount,CdnPercentageOf4XX,CdnPercentageOf5XX,BytesSent"

# Substrings that mean "interactive az login required" (vs a transient error).
AUTH_HINTS = ("az login", "AADSTS", "refresh token", "expired", "no subscription",
              "please run", "interaction_required", "DefaultAzureCredential")

# Thresholds (days) for flagging "needs a move".
STALE_IN_PROGRESS_DAYS = 2
STALE_TODO_DAYS = 5

JQL = "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"


class AzAuthError(RuntimeError):
    """az session needs interactive re-login (or KV unreachable)."""


def kv(secret: str) -> str:
    out = subprocess.run(
        ["az", "keyvault", "secret", "show", "--vault-name", VAULT,
         "--name", secret, "--query", "value", "-o", "tsv"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        err = (out.stderr or "").strip()
        if any(h.lower() in err.lower() for h in AUTH_HINTS):
            raise AzAuthError(err)
        raise RuntimeError(f"KV '{secret}' fetch failed: {err[:300]}")
    return out.stdout.strip()


def raise_auth_flag(reason: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_FLAG.write_text(json.dumps({
        "since": datetime.now(timezone.utc).isoformat(),
        "reason": reason[:500],
    }, indent=2))


def clear_auth_flag() -> None:
    AUTH_FLAG.unlink(missing_ok=True)


def jira_get(path: str, token: str) -> dict:
    cred = base64.b64encode(f"{JIRA_USER}:{token}".encode()).decode()
    req = urllib.request.Request(
        f"{JIRA_URL}{path}",
        headers={"Authorization": f"Basic {cred}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def az_json(args: list[str], timeout: int = 60) -> dict | list:
    out = subprocess.run(
        ["az", *args, "-o", "json"],
        capture_output=True, text=True, timeout=timeout,
    )
    if out.returncode != 0:
        err = (out.stderr or out.stdout or "").strip()
        if any(h.lower() in err.lower() for h in AUTH_HINTS):
            raise AzAuthError(err)
        raise RuntimeError(err[:500] or f"az {' '.join(args)} failed")
    text = out.stdout.strip()
    return json.loads(text) if text else {}


def first_appinsights_row(component: str, query: str) -> list:
    data = az_json([
        "monitor", "app-insights", "query",
        "--app", component,
        "-g", AZ_RG,
        "--analytics-query", query,
    ], timeout=45)
    tables = data.get("tables", []) if isinstance(data, dict) else []
    rows = tables[0].get("rows", []) if tables else []
    return rows[0] if rows else []


def appinsights_rows(component: str, query: str, limit: int = 5) -> list:
    data = az_json([
        "monitor", "app-insights", "query",
        "--app", component,
        "-g", AZ_RG,
        "--analytics-query", query,
    ], timeout=45)
    tables = data.get("tables", []) if isinstance(data, dict) else []
    rows = tables[0].get("rows", []) if tables else []
    return rows[:limit]


def resource_name(resource_id: str) -> str:
    parts = [p for p in (resource_id or "").split("/") if p]
    return parts[-1] if parts else "unknown"


def metric_window_start() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat().replace("+00:00", "Z")


def metric_totals(metrics: dict) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for value in (metrics.get("value", []) if isinstance(metrics, dict) else []):
        metric = value.get("name", {}).get("value")
        total = 0.0
        avg_sum = 0.0
        avg_count = 0
        max_avg = 0.0
        for ts in value.get("timeseries", []):
            for point in ts.get("data", []):
                if point.get("total") is not None:
                    total += float(point.get("total") or 0)
                if point.get("average") is not None:
                    avg = float(point.get("average") or 0)
                    avg_sum += avg
                    avg_count += 1
                    max_avg = max(max_avg, avg)
        out[metric] = {
            "total": total,
            "average": (avg_sum / avg_count) if avg_count else 0.0,
            "max_average": max_avg,
        }
    return out


def build_app_usage() -> list[dict]:
    apps = []
    usage_query = (
        "requests | where timestamp > ago(24h) "
        "| summarize requests=count(), failed=countif(success == false), "
        "users=dcount(user_AuthenticatedId), ips=dcount(client_IP)"
    )
    users_query = (
        "requests | where timestamp > ago(24h) "
        "| where isnotempty(user_AuthenticatedId) "
        "| summarize count=count(), last=max(timestamp) by user_AuthenticatedId "
        "| top 5 by count desc"
    )
    routes_query = (
        "requests | where timestamp > ago(24h) "
        "| summarize count=count(), failed=countif(success == false) by name "
        "| top 5 by count desc"
    )
    countries_query = (
        "requests | where timestamp > ago(24h) "
        "| summarize count=count() by client_CountryOrRegion "
        "| top 5 by count desc"
    )
    for app in APP_INSIGHTS_COMPONENTS:
        try:
            row = first_appinsights_row(app["component"], usage_query)
            if not row:
                apps.append({**app, "error": "no request telemetry returned"})
                continue
            item = {
                **app,
                "requests": int(row[0] or 0),
                "failed": int(row[1] or 0),
                "authenticated_users": int(row[2] or 0),
                "distinct_ips": int(row[3] or 0),
                "top_users": [],
                "top_routes": [],
                "top_countries": [],
            }
            for field, query in (
                ("top_users", users_query),
                ("top_routes", routes_query),
                ("top_countries", countries_query),
            ):
                try:
                    item[field] = appinsights_rows(app["component"], query)
                except Exception as e:
                    item.setdefault("warnings", []).append(f"{field}: {str(e)[:120]}")
            apps.append(item)
        except Exception as e:
            apps.append({**app, "error": str(e)[:240]})
    return apps


def build_storage_usage() -> list[dict]:
    resources = az_json([
        "resource", "list",
        "-g", AZ_RG,
        "--resource-type", "Microsoft.Storage/storageAccounts",
        "--query", "[].{name:name,id:id}",
    ], timeout=45)
    stores = []
    for r in resources if isinstance(resources, list) else []:
        name = r["name"]
        item = {"name": name, "id": r["id"]}
        try:
            props = az_json([
                "storage", "account", "show",
                "-g", AZ_RG,
                "-n", name,
                "--query", "{kind:kind,sku:sku.name,publicNetworkAccess:publicNetworkAccess,allowBlobPublicAccess:allowBlobPublicAccess}",
            ], timeout=45)
            item.update(props if isinstance(props, dict) else {})
            metrics = az_json([
                "monitor", "metrics", "list",
                "--resource", r["id"],
                "--metric", "Transactions,Ingress,Egress",
                "--start-time", metric_window_start(),
                "--interval", "PT1H",
                "--aggregation", "Total",
            ], timeout=45)
            totals = metric_totals(metrics)
            item["transactions"] = int(totals.get("Transactions", {}).get("total", 0))
            item["ingress_mb"] = round(totals.get("Ingress", {}).get("total", 0) / 1024 / 1024, 2)
            item["egress_mb"] = round(totals.get("Egress", {}).get("total", 0) / 1024 / 1024, 2)
        except Exception as e:
            item["error"] = str(e)[:240]
        stores.append(item)
    return stores


def build_platform_app_metrics() -> list[dict]:
    resources = az_json([
        "resource", "list",
        "-g", AZ_RG,
        "--query",
        "[?type=='Microsoft.Web/sites' || type=='Microsoft.Web/staticSites'].{name:name,type:type,kind:kind,id:id}",
    ], timeout=45)
    apps = []
    for r in resources if isinstance(resources, list) else []:
        item = {
            "name": r["name"],
            "type": r["type"],
            "kind": r.get("kind"),
            "id": r["id"],
        }
        try:
            is_static = r["type"] == "Microsoft.Web/staticSites"
            metrics = az_json([
                "monitor", "metrics", "list",
                "--resource", r["id"],
                "--metric", STATIC_SITE_METRICS if is_static else WEB_METRICS,
                "--start-time", metric_window_start(),
                "--interval", "PT1H",
                "--aggregation", "Total",
            ], timeout=45)
            totals = metric_totals(metrics)
            if is_static:
                item.update({
                    "requests": int(
                        totals.get("CdnRequestCount", {}).get("total", 0)
                        or totals.get("SiteHits", {}).get("total", 0)
                    ),
                    "errors": int(
                        totals.get("SiteErrors", {}).get("total", 0)
                        + totals.get("FunctionErrors", {}).get("total", 0)
                    ),
                    "function_hits": int(totals.get("FunctionHits", {}).get("total", 0)),
                    "bytes_sent_mb": round(totals.get("BytesSent", {}).get("total", 0) / 1024 / 1024, 2),
                    "pct_4xx": round(totals.get("CdnPercentageOf4XX", {}).get("average", 0), 2),
                    "pct_5xx": round(totals.get("CdnPercentageOf5XX", {}).get("average", 0), 2),
                })
            else:
                item.update({
                    "requests": int(totals.get("Requests", {}).get("total", 0)),
                    "http4xx": int(totals.get("Http4xx", {}).get("total", 0)),
                    "http5xx": int(totals.get("Http5xx", {}).get("total", 0)),
                    "bytes_in_mb": round(totals.get("BytesReceived", {}).get("total", 0) / 1024 / 1024, 2),
                    "bytes_out_mb": round(totals.get("BytesSent", {}).get("total", 0) / 1024 / 1024, 2),
                    "response_time_total": round(totals.get("AverageResponseTime", {}).get("total", 0), 1),
                })
        except Exception as e:
            item["error"] = str(e)[:240]
        apps.append(item)
    return apps


def build_container_job_status() -> list[dict]:
    resources = az_json([
        "resource", "list",
        "-g", AZ_RG,
        "--resource-type", "Microsoft.App/jobs",
        "--query", "[].{name:name,id:id}",
    ], timeout=45)
    jobs = []
    for r in resources if isinstance(resources, list) else []:
        item = {"name": r["name"], "id": r["id"], "executions": []}
        try:
            executions = az_json([
                "containerapp", "job", "execution", "list",
                "-g", AZ_RG,
                "-n", r["name"],
                "--query",
                "[].{name:name,status:properties.status,start:properties.startTime,end:properties.endTime}",
            ], timeout=45)
            status_counts: dict[str, int] = {}
            safe_execs = []
            for e in executions if isinstance(executions, list) else []:
                status = e.get("status", "Unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
                safe_execs.append({
                    "name": e.get("name"),
                    "status": status,
                    "start": e.get("start"),
                    "end": e.get("end"),
                })
            item["status_counts"] = sorted(status_counts.items(), key=lambda x: x[0])
            item["executions"] = safe_execs[:5]
        except Exception as e:
            item["error"] = str(e)[:240]
        jobs.append(item)
    return jobs


def build_activity_digest() -> dict:
    events = az_json([
        "monitor", "activity-log", "list",
        "--resource-group", AZ_RG,
        "--offset", "24h",
        "--max-events", "2000",
    ], timeout=60)
    interesting = []
    caller_counts: dict[str, int] = {}
    for e in events if isinstance(events, list) else []:
        op = ((e.get("operationName") or {}).get("value") or "")
        status = ((e.get("status") or {}).get("value") or "")
        if not any(k in op.lower() for k in INTERESTING_ACTIVITY):
            continue
        caller = e.get("caller") or "unknown"
        caller_counts[caller] = caller_counts.get(caller, 0) + 1
        interesting.append({
            "time": (e.get("eventTimestamp") or "")[:19].replace("T", " "),
            "caller": caller,
            "operation": op,
            "status": status,
            "resource": resource_name(e.get("resourceId", "")),
            "correlationId": e.get("correlationId", ""),
        })
    non_owner = [e for e in interesting if e["caller"].lower() != AZ_OWNER.lower()]
    return {
        "total": len(interesting),
        "non_owner": len(non_owner),
        "caller_counts": sorted(caller_counts.items(), key=lambda x: x[1], reverse=True),
        "latest": interesting[:12],
        "latest_non_owner": non_owner[:12],
    }


def build_monitoring_digest() -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    monitor = {
        "generated_at": generated_at,
        "resource_group": AZ_RG,
        "window": "last 24h",
        "apps": [],
        "platform_apps": [],
        "storage": [],
        "jobs": [],
        "activity": {},
        "errors": [],
    }
    for key, builder in (
        ("apps", build_app_usage),
        ("platform_apps", build_platform_app_metrics),
        ("storage", build_storage_usage),
        ("jobs", build_container_job_status),
        ("activity", build_activity_digest),
    ):
        try:
            monitor[key] = builder()
        except AzAuthError:
            raise
        except Exception as e:
            monitor["errors"].append(f"{key}: {str(e)[:300]}")
    return monitor


def days_since(iso: str, now: datetime) -> float:
    # Jira: 2026-06-01T11:09:13.214+0300
    dt = datetime.fromisoformat(iso)
    return (now - dt).total_seconds() / 86400.0


def build_digest(token: str) -> dict:
    now = datetime.now(timezone.utc)
    search = jira_get(
        "/rest/api/3/search/jql?"
        f"jql={urllib.parse.quote(JQL)}"
        "&maxResults=50&fields=summary,status,updated,comment,priority,issuetype",
        token,
    )
    flagged = []
    for issue in search.get("issues", []):
        f = issue["fields"]
        key = issue["key"]
        status = f["status"]["name"]
        cat = f["status"]["statusCategory"]["name"]
        updated = f["updated"]
        age = days_since(updated, now)
        reasons = []

        # Backlog is meant to sit — don't nag on age, only on new comments.
        if cat == "In Progress" and age >= STALE_IN_PROGRESS_DAYS:
            reasons.append(f"In Progress {age:.0f}d, no update — move it or note progress")
        elif cat == "To Do" and status != "Backlog" and age >= STALE_TODO_DAYS:
            reasons.append(f"To Do {age:.0f}d untouched — start it or push to backlog")

        # New comment authored by someone other than Shoval.
        comments = (f.get("comment") or {}).get("comments", [])
        if comments:
            last = comments[-1]
            author = (last.get("author") or {}).get("emailAddress", "")
            if author and author != JIRA_USER:
                reasons.append(f"new comment from {last['author'].get('displayName', author)} — reply/ack")

        if reasons:
            flagged.append({
                "key": key,
                "summary": f["summary"],
                "status": status,
                "priority": (f.get("priority") or {}).get("name", "—"),
                "type": f["issuetype"]["name"],
                "age_days": round(age, 1),
                "reasons": reasons,
            })

    return {
        "generated_at": now.isoformat(),
        "jira_url": JIRA_URL,
        "open_total": len(search.get("issues", [])),
        "flagged": flagged,
    }


def render_text(d: dict) -> str:
    lines = [
        f"Jira reminders — {d['open_total']} open, {len(d['flagged'])} need action",
        f"(generated {d['generated_at'][:16]}Z)",
        "",
    ]
    if not d["flagged"]:
        lines.append("Nothing stale. All open tickets are fresh.")
    for t in d["flagged"]:
        lines.append(f"• {t['key']} [{t['status']}] {t['summary']}")
        for r in t["reasons"]:
            lines.append(f"    - {r}")
        lines.append(f"    {d['jira_url']}/browse/{t['key']}")
    lines += ["", "Status moves / comments are human-in-the-loop — open Claude and confirm."]
    if d.get("monitoring"):
        lines.extend(["", "", render_monitoring_text(d["monitoring"])])
    return "\n".join(lines)


def h(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def compact_op(op: str) -> str:
    parts = [p for p in (op or "").split("/") if p]
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return op or "unknown"


def risk_items(d: dict) -> list[dict]:
    items: list[dict] = []
    m = d.get("monitoring") or {}
    a = m.get("activity") or {}
    non_owner = int(a.get("non_owner") or 0)
    if non_owner:
        items.append({
            "level": "warning",
            "title": "External operator activity",
            "detail": f"{non_owner} write/action/delete-like operations were performed by someone other than {AZ_OWNER}.",
        })

    failed_jobs = []
    stopped_jobs = []
    for job in m.get("jobs", []):
        counts = dict(job.get("status_counts") or [])
        if counts.get("Failed"):
            failed_jobs.append(f"{job['name']} ({counts['Failed']})")
        if counts.get("Stopped"):
            stopped_jobs.append(f"{job['name']} ({counts['Stopped']})")
    if failed_jobs or stopped_jobs:
        detail = []
        if failed_jobs:
            detail.append("failed: " + ", ".join(failed_jobs))
        if stopped_jobs:
            detail.append("stopped: " + ", ".join(stopped_jobs))
        items.append({"level": "warning", "title": "Report job interruptions", "detail": "; ".join(detail) + "."})

    web_5xx = []
    for app in m.get("platform_apps", []):
        if int(app.get("http5xx") or 0) > 0:
            web_5xx.append(f"{app['name']} ({app['http5xx']} 5xx)")
    if web_5xx:
        items.append({"level": "error", "title": "Server errors observed", "detail": ", ".join(web_5xx) + "."})

    telemetry_errors = [app for app in m.get("apps", []) if app.get("error")]
    if telemetry_errors:
        items.append({
            "level": "info",
            "title": "Telemetry gaps",
            "detail": ", ".join(app["label"] for app in telemetry_errors) + " returned telemetry errors.",
        })

    if d.get("flagged"):
        items.append({
            "level": "warning",
            "title": "Jira needs action",
            "detail": f"{len(d['flagged'])} ticket(s) need a move, reply, or backlog decision.",
        })
    return items


def score_class(level: str) -> str:
    return {
        "error": "background:#f38ba8;color:#2e3440;",
        "warning": "background:#88c0d0;color:#2e3440;",
        "info": "background:#d8dee9;color:#2e3440;",
        "ok": "background:#a3be8c;color:#2e3440;",
    }.get(level, "background:#d8dee9;color:#2e3440;")


def render_html(d: dict) -> str:
    m = d.get("monitoring") or {}
    a = m.get("activity") or {}
    risks = risk_items(d)
    risk_level = "error" if any(r["level"] == "error" for r in risks) else ("warning" if risks else "ok")
    risk_label = "Needs attention" if risks else "Healthy"
    generated = h((m.get("generated_at") or d.get("generated_at", ""))[:16].replace("T", " "))
    flagged = d.get("flagged") or []
    platform_apps = m.get("platform_apps") or []
    storage = m.get("storage") or []
    jobs = m.get("jobs") or []
    latest_activity = (a.get("latest_non_owner") or a.get("latest") or [])[:8]

    body_bg = "#d8dee9"
    ink = "#2e3440"
    panel = "#eceff4"
    accent = "#88c0d0"
    success = "#a3be8c"
    border = "#c8d0dc"

    def card(label: str, value: object, sub: str = "") -> str:
        return f"""
        <td style="width:25%;padding:8px;">
          <div style="background:{panel};border:1px solid {border};border-radius:8px;padding:14px;">
            <div style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:{ink};opacity:.72;">{h(label)}</div>
            <div style="font-size:26px;line-height:1.2;font-weight:700;color:{ink};">{h(value)}</div>
            <div style="font-size:12px;color:{ink};opacity:.72;">{h(sub)}</div>
          </div>
        </td>"""

    risk_rows = "".join(
        f"""
        <tr>
          <td style="padding:10px 12px;border-top:1px solid {border};">
            <span style="display:inline-block;border-radius:999px;padding:3px 8px;font-size:12px;font-weight:700;{score_class(r['level'])}">{h(r['level']).upper()}</span>
          </td>
          <td style="padding:10px 12px;border-top:1px solid {border};font-weight:700;color:{ink};">{h(r['title'])}</td>
          <td style="padding:10px 12px;border-top:1px solid {border};color:{ink};">{h(r['detail'])}</td>
        </tr>"""
        for r in risks
    ) or f"""
        <tr><td colspan="3" style="padding:12px;border-top:1px solid {border};color:{ink};">
          No high-signal operational issues in the last 24h.
        </td></tr>"""

    jira_rows = "".join(
        f"""
        <tr>
          <td style="padding:10px 12px;border-top:1px solid {border};font-weight:700;"><a style="color:{ink};" href="{h(d['jira_url'])}/browse/{h(t['key'])}">{h(t['key'])}</a></td>
          <td style="padding:10px 12px;border-top:1px solid {border};">{h(t['status'])}</td>
          <td style="padding:10px 12px;border-top:1px solid {border};">{h(t['summary'])}</td>
          <td style="padding:10px 12px;border-top:1px solid {border};">{h('; '.join(t.get('reasons') or []))}</td>
        </tr>"""
        for t in flagged
    ) or f"""<tr><td colspan="4" style="padding:12px;border-top:1px solid {border};">No Jira tickets need action.</td></tr>"""

    app_rows = "".join(
        f"""
        <tr>
          <td style="padding:9px 12px;border-top:1px solid {border};font-weight:700;">{h(app['name'])}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(app.get('requests', 0))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(app.get('http4xx', app.get('errors', 0)))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(app.get('http5xx', 0))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(app.get('bytes_out_mb', app.get('bytes_sent_mb', 0)))} MB</td>
        </tr>"""
        for app in platform_apps
    )

    telemetry_rows = "".join(
        f"""
        <tr>
          <td style="padding:9px 12px;border-top:1px solid {border};font-weight:700;">{h(app['label'])}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(app.get('requests', 'err' if app.get('error') else 0))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(app.get('failed', '-'))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(app.get('authenticated_users', '-'))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};">{h(app.get('error') or 'ok')}</td>
        </tr>"""
        for app in m.get("apps", [])
    )

    storage_rows = "".join(
        f"""
        <tr>
          <td style="padding:9px 12px;border-top:1px solid {border};font-weight:700;">{h(s['name'])}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(s.get('transactions', 0))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(s.get('ingress_mb', 0))} MB</td>
          <td style="padding:9px 12px;border-top:1px solid {border};text-align:right;">{h(s.get('egress_mb', 0))} MB</td>
          <td style="padding:9px 12px;border-top:1px solid {border};">{h('public blob=' + str(s.get('allowBlobPublicAccess')))}</td>
        </tr>"""
        for s in storage
    )

    job_rows = "".join(
        f"""
        <tr>
          <td style="padding:9px 12px;border-top:1px solid {border};font-weight:700;">{h(job['name'])}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};">{h(', '.join(f'{status}={count}' for status, count in job.get('status_counts', [])) or 'no executions')}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};">{h((job.get('executions') or [{}])[0].get('status', '-'))}</td>
        </tr>"""
        for job in jobs
    )

    activity_rows = "".join(
        f"""
        <tr>
          <td style="padding:9px 12px;border-top:1px solid {border};white-space:nowrap;">{h(e.get('time'))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};">{h(e.get('caller'))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};">{h(compact_op(e.get('operation', '')))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};">{h(e.get('resource'))}</td>
          <td style="padding:9px 12px;border-top:1px solid {border};">{h(e.get('status'))}</td>
        </tr>"""
        for e in latest_activity
    )

    return f"""<!doctype html>
<html>
<body style="margin:0;background:{body_bg};font-family:Arial,'Segoe UI',sans-serif;color:{ink};">
  <div style="max-width:980px;margin:0 auto;padding:24px;">
    <div style="background:{ink};color:{panel};border-radius:8px;padding:22px 24px;">
      <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:{accent};">Daily Ops Briefing</div>
      <div style="font-size:28px;line-height:1.15;font-weight:700;margin-top:4px;">Jira + Azure monitoring</div>
      <div style="font-size:14px;opacity:.82;margin-top:8px;">{generated} UTC · {h(m.get('resource_group', AZ_RG))} · last 24h</div>
    </div>

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:16px;"><tr>
      {card("Overall", risk_label, f"{len(risks)} item(s) to inspect")}
      {card("Jira", f"{len(flagged)} / {d.get('open_total', '?')}", "need action / open")}
      {card("Resource activity", a.get("non_owner", 0), f"non-owner ops of {a.get('total', 0)}")}
      {card("Jobs", sum(1 for j in jobs if any(s in dict(j.get('status_counts', [])) for s in ('Failed','Stopped'))), "interrupted jobs")}
    </tr></table>

    <div style="background:{panel};border:1px solid {border};border-radius:8px;margin-top:16px;overflow:hidden;">
      <div style="padding:14px 16px;font-weight:700;background:{accent};color:{ink};">What needs attention</div>
      <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px;">
        {risk_rows}
      </table>
    </div>

    <div style="background:{panel};border:1px solid {border};border-radius:8px;margin-top:16px;overflow:hidden;">
      <div style="padding:14px 16px;font-weight:700;background:{accent};color:{ink};">Jira evidence</div>
      <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px;">
        <tr style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;"><th align="left" style="padding:10px 12px;">Key</th><th align="left" style="padding:10px 12px;">Status</th><th align="left" style="padding:10px 12px;">Summary</th><th align="left" style="padding:10px 12px;">Reason</th></tr>
        {jira_rows}
      </table>
    </div>

    <div style="background:{panel};border:1px solid {border};border-radius:8px;margin-top:16px;overflow:hidden;">
      <div style="padding:14px 16px;font-weight:700;background:{accent};color:{ink};">Application evidence</div>
      <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px;">
        <tr style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;"><th align="left" style="padding:10px 12px;">App</th><th align="right" style="padding:10px 12px;">Req</th><th align="right" style="padding:10px 12px;">4xx</th><th align="right" style="padding:10px 12px;">5xx</th><th align="right" style="padding:10px 12px;">Out</th></tr>
        {app_rows}
      </table>
    </div>

    <div style="background:{panel};border:1px solid {border};border-radius:8px;margin-top:16px;overflow:hidden;">
      <div style="padding:14px 16px;font-weight:700;background:{accent};color:{ink};">Identity telemetry quality</div>
      <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px;">
        <tr style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;"><th align="left" style="padding:10px 12px;">Component</th><th align="right" style="padding:10px 12px;">Req</th><th align="right" style="padding:10px 12px;">Fail</th><th align="right" style="padding:10px 12px;">Auth users</th><th align="left" style="padding:10px 12px;">Evidence</th></tr>
        {telemetry_rows}
      </table>
    </div>

    <div style="background:{panel};border:1px solid {border};border-radius:8px;margin-top:16px;overflow:hidden;">
      <div style="padding:14px 16px;font-weight:700;background:{accent};color:{ink};">Storage and jobs</div>
      <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px;">
        <tr style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;"><th align="left" style="padding:10px 12px;">Storage</th><th align="right" style="padding:10px 12px;">Tx</th><th align="right" style="padding:10px 12px;">In</th><th align="right" style="padding:10px 12px;">Out</th><th align="left" style="padding:10px 12px;">Exposure</th></tr>
        {storage_rows}
      </table>
      <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px;margin-top:10px;">
        <tr style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;"><th align="left" style="padding:10px 12px;">Job</th><th align="left" style="padding:10px 12px;">24h status</th><th align="left" style="padding:10px 12px;">Latest</th></tr>
        {job_rows}
      </table>
    </div>

    <div style="background:{panel};border:1px solid {border};border-radius:8px;margin-top:16px;overflow:hidden;">
      <div style="padding:14px 16px;font-weight:700;background:{accent};color:{ink};">Resource activity evidence</div>
      <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px;">
        <tr style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;"><th align="left" style="padding:10px 12px;">Time</th><th align="left" style="padding:10px 12px;">Caller</th><th align="left" style="padding:10px 12px;">Operation</th><th align="left" style="padding:10px 12px;">Resource</th><th align="left" style="padding:10px 12px;">Status</th></tr>
        {activity_rows}
      </table>
    </div>

    <div style="font-size:12px;line-height:1.5;color:{ink};opacity:.72;margin-top:16px;">
      Evidence comes from existing Jira, App Insights, Azure Monitor metrics, Container Apps execution metadata, and Azure Activity Log. No new Azure resources or diagnostic ingestion were created by this email.
    </div>
  </div>
</body>
</html>"""


def render_monitoring_text(m: dict) -> str:
    lines = [
        f"Azure monitoring — {m.get('resource_group')} ({m.get('window')})",
        f"(generated {m.get('generated_at', '')[:16]}Z)",
        "",
        "Apps:",
    ]
    for app in m.get("apps", []):
        if app.get("error"):
            lines.append(f"• {app['label']}: {app['error']}")
            continue
        lines.append(
            f"• {app['label']}: {app['requests']} requests, "
            f"{app['failed']} failed, {app['authenticated_users']} auth users, "
            f"{app['distinct_ips']} IPs"
        )
        if app.get("top_users"):
            compact = ", ".join(f"{u[0]} ({u[1]})" for u in app["top_users"][:3])
            lines.append(f"    top users: {compact}")
        else:
            lines.append("    top users: no authenticated user IDs in telemetry")
        if app.get("top_routes"):
            routes = ", ".join(f"{r[0]} ({r[1]})" for r in app["top_routes"][:3])
            lines.append(f"    top routes: {routes}")
        if app.get("top_countries"):
            countries = ", ".join(f"{c[0] or 'unknown'} ({c[1]})" for c in app["top_countries"][:3])
            lines.append(f"    countries: {countries}")

    lines.extend(["", "Deployed app platform metrics:"])
    for app in m.get("platform_apps", []):
        if app.get("error"):
            lines.append(f"• {app['name']}: {app['error']}")
            continue
        if app.get("type") == "Microsoft.Web/staticSites":
            lines.append(
                f"• {app['name']} [static]: {app.get('requests', 0)} requests, "
                f"{app.get('errors', 0)} errors, function hits {app.get('function_hits', 0)}, "
                f"out {app.get('bytes_sent_mb', 0)} MB, "
                f"4xx {app.get('pct_4xx', 0)}%, 5xx {app.get('pct_5xx', 0)}%"
            )
        else:
            lines.append(
                f"• {app['name']}: {app.get('requests', 0)} requests, "
                f"4xx {app.get('http4xx', 0)}, 5xx {app.get('http5xx', 0)}, "
                f"in {app.get('bytes_in_mb', 0)} MB, out {app.get('bytes_out_mb', 0)} MB"
            )

    lines.extend(["", "Storage:"])
    for s in m.get("storage", []):
        if s.get("error"):
            lines.append(f"• {s['name']}: {s['error']}")
            continue
        pub = f"publicBlob={s.get('allowBlobPublicAccess')}, publicNetwork={s.get('publicNetworkAccess')}"
        lines.append(
            f"• {s['name']}: {s.get('transactions', 0)} transactions, "
            f"in {s.get('ingress_mb', 0)} MB, out {s.get('egress_mb', 0)} MB, {pub}"
        )

    lines.extend(["", "Container jobs:"])
    for job in m.get("jobs", []):
        if job.get("error"):
            lines.append(f"• {job['name']}: {job['error']}")
            continue
        counts = ", ".join(f"{status}={count}" for status, count in job.get("status_counts", [])) or "no executions returned"
        lines.append(f"• {job['name']}: {counts}")
        for e in job.get("executions", [])[:3]:
            start = (e.get("start") or "")[:19].replace("T", " ")
            end = (e.get("end") or "")[:19].replace("T", " ")
            suffix = f" -> {end}" if end else ""
            lines.append(f"    - {start}{suffix}: {e.get('status')}")

    a = m.get("activity", {})
    lines.extend(["", "Azure resource activity:"])
    lines.append(
        f"• {a.get('total', 0)} write/action/delete-like operations; "
        f"{a.get('non_owner', 0)} by someone other than {AZ_OWNER}"
    )
    for caller, count in a.get("caller_counts", [])[:5]:
        lines.append(f"    {caller}: {count}")
    rows = a.get("latest_non_owner") or a.get("latest") or []
    if rows:
        lines.append("    latest notable:")
        for e in rows[:6]:
            lines.append(
                f"    - {e['time']} {e['caller']} {e['operation']} "
                f"on {e['resource']} ({e['status']})"
            )
    if m.get("errors"):
        lines.extend(["", "Monitoring errors:"])
        lines.extend(f"• {e}" for e in m["errors"])
    return "\n".join(lines)


def send_email(body: str, n_flagged: int, has_monitoring: bool = False, html_body: str | None = None) -> None:
    login = kv("SMTP-BREVO-LOGIN")
    password = kv("SMTP-BREVO-PASSWORD")
    msg = EmailMessage()
    prefix = "[Daily] Jira + Azure monitoring" if has_monitoring else "[Jira]"
    msg["Subject"] = f"{prefix}: {n_flagged} ticket(s) need action"
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(BREVO_HOST, BREVO_PORT, timeout=30) as s:
        s.starttls()
        s.login(login, password)
        s.send_message(msg)


def main() -> int:
    no_email = "--no-email" in sys.argv
    include_monitoring = "--monitoring" in sys.argv
    try:
        token = kv("JIRA-API-KEY")
    except AzAuthError as e:
        raise_auth_flag(str(e))
        print(f"[az login required — Jira refresh skipped]\n{e}", file=sys.stderr)
        return 2  # banner will surface the flag; cannot email (needs az for SMTP creds)
    clear_auth_flag()  # az is healthy — clear any stale warning
    digest = build_digest(token)
    if include_monitoring:
        try:
            digest["monitoring"] = build_monitoring_digest()
        except AzAuthError as e:
            raise_auth_flag(str(e))
            print(f"[az login required — monitoring refresh skipped]\n{e}", file=sys.stderr)
            return 2
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    DIGEST_PATH.write_text(json.dumps(digest, indent=2))
    body = render_text(digest)
    html_body = render_html(digest) if include_monitoring else None
    print(body)
    if not no_email and (digest["flagged"] or include_monitoring):
        send_email(body, len(digest["flagged"]), include_monitoring, html_body)
        print(f"\n[emailed {MAIL_TO}]")
    elif not no_email:
        print("\n[no flagged tickets — email skipped]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
