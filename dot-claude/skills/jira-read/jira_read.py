#!/usr/bin/env python3
"""Read-only Jira access for qboservices.atlassian.net.

Auth mirrors ~/.claude/bin/jira-reminder-refresh.py: token comes from Azure
Key Vault 'Shoval'/JIRA-API-KEY at call time via an active `az login` session,
never written to disk, never printed. This module makes ONLY GET requests —
no create/update/transition/comment-post capability exists here by design.
Writes stay human-in-the-loop via jira-task-draft (drafts) and the Jira
comment-drafting rule (post only after explicit per-comment approval).

Usage:
    jira_read.py issue DEV-5062 [--raw]
    jira_read.py comments DEV-5062
    jira_read.py attachments DEV-5062
    jira_read.py download 90405 /tmp/out.zip
    jira_read.py search 'project = DEV AND text ~ "Widgora" ORDER BY created ASC' [--max 50]
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import urllib.parse
import urllib.request

JIRA_URL = "https://qboservices.atlassian.net"
JIRA_USER = "shoval.be@i-sdd.com"
VAULT = "Shoval"

ISSUE_FIELDS = (
    "summary,description,status,comment,priority,issuetype,assignee,"
    "reporter,created,updated,labels,fixVersions,parent,subtasks,"
    "issuelinks,attachment"
)


def kv(secret: str) -> str:
    out = subprocess.run(
        ["az", "keyvault", "secret", "show", "--vault-name", VAULT,
         "--name", secret, "--query", "value", "-o", "tsv"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"Key Vault fetch failed (az login stale?): {out.stderr.strip()[:300]}")
    return out.stdout.strip()


def _token() -> str:
    return kv("JIRA-API-KEY")


def jira_get(path: str, token: str) -> dict:
    cred = base64.b64encode(f"{JIRA_USER}:{token}".encode()).decode()
    req = urllib.request.Request(
        f"{JIRA_URL}{path}",
        headers={"Authorization": f"Basic {cred}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def jira_get_bytes(url: str, token: str) -> bytes:
    cred = base64.b64encode(f"{JIRA_USER}:{token}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {cred}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def adf_to_text(node, indent: int = 0) -> str:
    """Flatten Atlassian Document Format (issue description / comment body) to plain text."""
    if node is None:
        return ""
    t = node.get("type")
    if t == "text":
        text = node.get("text", "")
        marks = {m.get("type") for m in node.get("marks", [])}
        if "strong" in marks:
            text = f"**{text}**"
        if "code" in marks:
            text = f"`{text}`"
        return text
    if t == "hardBreak":
        return "\n"
    if t == "media":
        alt = node.get("attrs", {}).get("alt", "attachment")
        return f"[image: {alt}]"
    children = "".join(adf_to_text(c, indent) for c in node.get("content", []))
    if t == "paragraph":
        return children + "\n"
    if t == "listItem":
        return "  " * indent + "- " + children.strip() + "\n"
    if t in ("bulletList", "orderedList"):
        return "".join(adf_to_text(c, indent + 1) for c in node.get("content", []))
    if t == "rule":
        return "---\n"
    if t == "mediaSingle":
        return children
    if t == "mediaGroup":
        return children
    if t == "doc":
        return children
    return children


def format_issue(issue: dict) -> str:
    f = issue["fields"]
    lines = [
        f"{issue['key']}: {f['summary']}",
        f"  status={f['status']['name']}  priority={(f.get('priority') or {}).get('name', '-')}  "
        f"type={f['issuetype']['name']}",
        f"  reporter={(f.get('reporter') or {}).get('displayName', '-')}  "
        f"assignee={(f.get('assignee') or {}).get('displayName', '-')}",
        f"  created={f.get('created', '-')[:16]}  updated={f.get('updated', '-')[:16]}",
    ]
    if f.get("description"):
        lines.append("\n-- description --")
        lines.append(adf_to_text(f["description"]).rstrip())
    comments = (f.get("comment") or {}).get("comments", [])
    if comments:
        lines.append(f"\n-- comments ({len(comments)}) --")
        for c in comments:
            author = (c.get("author") or {}).get("displayName", "-")
            lines.append(f"[{c.get('created', '-')[:16]}] {author}:")
            lines.append(adf_to_text(c["body"]).rstrip())
            lines.append("")
    attachments = f.get("attachment") or []
    if attachments:
        lines.append(f"-- attachments ({len(attachments)}) --")
        for a in attachments:
            lines.append(f"  [{a['id']}] {a['filename']}  {a['size']}b  {a.get('created', '-')[:16]}")
    return "\n".join(lines)


def cmd_issue(args) -> int:
    token = _token()
    issue = jira_get(f"/rest/api/3/issue/{args.key}?fields={ISSUE_FIELDS}", token)
    print(json.dumps(issue, indent=2) if args.raw else format_issue(issue))
    return 0


def cmd_comments(args) -> int:
    token = _token()
    issue = jira_get(f"/rest/api/3/issue/{args.key}?fields=comment", token)
    for c in (issue["fields"].get("comment") or {}).get("comments", []):
        author = (c.get("author") or {}).get("displayName", "-")
        print(f"[{c.get('created', '-')[:16]}] {author}:")
        print(adf_to_text(c["body"]).rstrip())
        print()
    return 0


def cmd_attachments(args) -> int:
    token = _token()
    issue = jira_get(f"/rest/api/3/issue/{args.key}?fields=attachment", token)
    for a in issue["fields"].get("attachment") or []:
        print(f"{a['id']}\t{a['filename']}\t{a['size']}b\t{a.get('created', '-')[:16]}")
    return 0


def cmd_download(args) -> int:
    token = _token()
    url = f"{JIRA_URL}/rest/api/3/attachment/content/{args.attachment_id}"
    data = jira_get_bytes(url, token)
    with open(args.out, "wb") as fh:
        fh.write(data)
    print(f"wrote {len(data)} bytes -> {args.out}")
    return 0


def cmd_search(args) -> int:
    token = _token()
    q = urllib.parse.quote(args.jql)
    result = jira_get(
        f"/rest/api/3/search/jql?jql={q}&maxResults={args.max}&fields=summary,status,updated,issuetype",
        token,
    )
    for issue in result.get("issues", []):
        f = issue["fields"]
        print(f"{issue['key']}\t{f['status']['name']}\t{f['issuetype']['name']}\t{f['summary']}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_issue = sub.add_parser("issue", help="fetch one issue, human-readable by default")
    p_issue.add_argument("key")
    p_issue.add_argument("--raw", action="store_true", help="print full JSON instead")
    p_issue.set_defaults(func=cmd_issue)

    p_comments = sub.add_parser("comments", help="print just the comments on an issue")
    p_comments.add_argument("key")
    p_comments.set_defaults(func=cmd_comments)

    p_att = sub.add_parser("attachments", help="list attachments on an issue")
    p_att.add_argument("key")
    p_att.set_defaults(func=cmd_attachments)

    p_dl = sub.add_parser("download", help="download one attachment by id")
    p_dl.add_argument("attachment_id")
    p_dl.add_argument("out")
    p_dl.set_defaults(func=cmd_download)

    p_search = sub.add_parser("search", help="JQL search")
    p_search.add_argument("jql")
    p_search.add_argument("--max", type=int, default=50)
    p_search.set_defaults(func=cmd_search)

    args = p.parse_args()
    try:
        return args.func(args)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
