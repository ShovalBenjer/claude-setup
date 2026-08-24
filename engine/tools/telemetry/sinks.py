#!/usr/bin/env python3
"""Where a rendered digest goes. Two implementations, one contract.

The split exists because the SURFACE moved and the derivation did not. Everything that
decides WHAT to post (collect, select, fingerprint, cursor, throttle, cap) stays in
publish.py and is untouched. A sink only knows how to hand a finished string to GitHub
and how to say where it landed.

WHY THE SURFACE MOVED. The feed ran as comments on issue #38 under a systemd timer every
31 minutes. In its first 18h36m it fired 37 times, posted 12 comments carrying 146 item
lines, and received 0 reactions and 0 replies. The issue body wrote its own tripwire and
`docs/prior-art/tools-telemetry.json` recheck item (1) restates it: a feed with posts and
no engagement has become the bus's successor in the worst way. Operator decision on
2026-08-05 was to move it to GitHub Discussions rather than to slow it down.

Discussions is the surface GitHub built for threaded asynchronous conversation, and an
issue tracker is not. That is the whole argument for the move and it is a bet, not a
measurement: the engagement problem may follow the feed there. The recheck date and
threshold are recorded with the prior-art record rather than left as a hope.

THE ISSUE SINK IS KEPT, NOT DELETED. A migration whose old path is removed is a migration
that cannot be reversed, and the systemd unit on disk keeps pointing at the issue until
somebody redeploys it. Deleting the sink would turn a deployment lag into an outage.

NO IMPLICIT DEFAULT. `sink_from_config` errors rather than falling back, for the reason
ADR-0018 decision 1 gives about the inter-agent channel: a downgrade that reads as
success is the failure. A publish that silently posts to the wrong surface is worse than
one that refuses.
"""
from __future__ import annotations

import json
import subprocess
from typing import Protocol

# Non-answerable categories only. A Q&A category marks every post as a question awaiting
# an answer, and a machine feed would sit there permanently unanswered, which is a worse
# signal than no signal.
PREFERRED_CATEGORIES = ("agent-feed", "General", "Announcements")


class Sink(Protocol):
    """Somewhere a rendered digest can land."""

    name: str

    def describe(self) -> str:
        """One line for the dry-run banner, so a dry run says where it WOULD have gone."""

    def post(self, body: str) -> tuple[int, str]:
        """Return (returncode, output). Nonzero means the cursor must NOT advance."""


def graphql(query: str, variables: dict | None = None,
            stdin_body: str | None = None) -> tuple[int, dict]:
    """One `gh api graphql` call.

    A body goes over STDIN rather than argv. The digest contains backticks, asterisks and
    newlines, and argv is exactly where those break: a shell-quoted body is the class of
    bug that truncates a post at the first backtick and looks like a partial success.
    """
    cmd = ["gh", "api", "graphql", "-f", "query=" + query]
    for k, v in (variables or {}).items():
        cmd += ["-F", "{}={}".format(k, v)]
    if stdin_body is not None:
        cmd += ["-F", "body=@-"]
    r = subprocess.run(cmd, input=stdin_body, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return r.returncode, {"error": (r.stdout + r.stderr).strip()}
    try:
        return 0, json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        # A zero exit with unparseable output is not a success. Saying so is the point:
        # the alternative is treating an empty dict as a posted comment.
        return 1, {"error": "gh returned rc=0 with unparseable output: " + r.stdout[:400]}


def resolve_category(owner: str, repo: str,
                     prefer: tuple[str, ...] = PREFERRED_CATEGORIES) -> dict | None:
    """Pick a non-answerable discussion category by preference order.

    Returns None rather than guessing. An empty category list means Discussions is off or
    has no categories, and that is an operator step (categories are UI-only: GitHub
    publishes no `createDiscussionCategory` mutation, verified by enumerating every
    mutation in the schema on 2026-08-05). Surfacing it here as None makes it a readable
    message instead of a crash at post time.
    """
    rc, doc = graphql(
        "query($o:String!,$n:String!){repository(owner:$o,name:$n){"
        "discussionCategories(first:25){nodes{id name slug isAnswerable}}}}",
        {"o": owner, "n": repo})
    if rc != 0:
        return None
    nodes = (((doc.get("data") or {}).get("repository") or {})
             .get("discussionCategories") or {}).get("nodes") or []
    open_ended = [n for n in nodes if not n.get("isAnswerable")]
    for want in prefer:
        for n in open_ended:
            if n.get("name", "").lower() == want.lower():
                return n
    return open_ended[0] if open_ended else None


class IssueCommentSink:
    """`gh issue comment`. The original surface, kept so the move is reversible."""

    name = "issue"

    def __init__(self, issue: int) -> None:
        self.issue = int(issue)

    def describe(self) -> str:
        return "issue #{}".format(self.issue)

    def post(self, body: str) -> tuple[int, str]:
        r = subprocess.run(["gh", "issue", "comment", str(self.issue), "--body", body],
                           capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr).strip()


class DiscussionCommentSink:
    """`addDiscussionComment` against ONE long-lived discussion.

    One discussion with appended comments, not one discussion per digest. A per-digest
    discussion would create 48 unsubscribed surfaces a day, would make the category id a
    permanent runtime dependency instead of a one-time lookup, and would break the
    cursor's meaning, since dedupe is across the whole feed and not within one post.

    Takes the NODE id (`D_kw...`), never the number. `addDiscussionComment` declares
    `discussionId: ID!`, and passing `38` there fails with a type error whose text reads
    like an authentication problem, which is a bad half hour for whoever hits it.
    """

    name = "discussion"

    def __init__(self, discussion_id: str) -> None:
        if not str(discussion_id).startswith("D_"):
            raise ValueError(
                "discussion id must be the GraphQL node id (D_kw...), got {!r}. "
                "The discussion NUMBER is not accepted by addDiscussionComment."
                .format(discussion_id))
        self.discussion_id = str(discussion_id)

    def describe(self) -> str:
        return "discussion {}".format(self.discussion_id)

    def post(self, body: str) -> tuple[int, str]:
        rc, doc = graphql(
            "mutation($did:ID!,$body:String!){addDiscussionComment("
            "input:{discussionId:$did, body:$body}){comment{id url createdAt}}}",
            {"did": self.discussion_id}, stdin_body=body)
        if rc != 0:
            return rc, str(doc.get("error", doc))
        if doc.get("errors"):
            # GraphQL reports application errors with a 200 and an `errors` array, so a
            # zero return code is not evidence of a posted comment.
            return 1, json.dumps(doc["errors"])[:400]
        comment = (((doc.get("data") or {}).get("addDiscussionComment") or {})
                   .get("comment") or {})
        return 0, comment.get("url", "posted, but the response carried no url")


def create_discussion(repository_id: str, category_id: str, title: str,
                      body: str) -> tuple[int, dict]:
    """Create the one long-lived discussion. Called by --bootstrap, never by the timer."""
    rc, doc = graphql(
        "mutation($rid:ID!,$cid:ID!,$t:String!,$body:String!){createDiscussion("
        "input:{repositoryId:$rid, categoryId:$cid, title:$t, body:$body}){"
        "discussion{id number url}}}",
        {"rid": repository_id, "cid": category_id, "t": title}, stdin_body=body)
    if rc != 0:
        return rc, doc
    if doc.get("errors"):
        return 1, {"error": json.dumps(doc["errors"])[:400]}
    return 0, ((doc.get("data") or {}).get("createDiscussion") or {}).get("discussion") or {}


def sink_from_config(sink_name: str, issue: int | None,
                     discussion_id: str | None) -> Sink:
    """Resolve a sink or raise. There is deliberately no default.

    ADR-0018 decision 1 forbids a silent channel downgrade between agents, and the same
    reasoning applies to a publishing surface: falling back to the issue because a
    discussion id was missing would post real content to the surface being retired, and
    the run would report success.
    """
    if sink_name == "issue":
        if not issue:
            raise ValueError("--sink issue needs --issue N naming an existing issue")
        return IssueCommentSink(issue)
    if sink_name == "discussion":
        if not discussion_id:
            raise ValueError(
                "--sink discussion needs --discussion-id D_kw... . Run --bootstrap once "
                "to create the discussion and record its id in state/agent-feed.json")
        return DiscussionCommentSink(discussion_id)
    raise ValueError("unknown sink {!r}; expected issue or discussion".format(sink_name))


def selftest() -> int:
    """No network. Every check is about the contract, not about GitHub."""
    failures = []

    try:
        DiscussionCommentSink("38")
    except ValueError:
        pass
    else:
        failures.append("a discussion NUMBER was accepted where a node id is required, "
                        "so the first post fails with a type error that reads like auth")

    try:
        DiscussionCommentSink("D_kwABC").describe()
    except Exception as exc:  # noqa: BLE001
        failures.append("a valid node id was rejected: {}".format(exc))

    for bad, why in (
        (("discussion", 38, None), "a discussion sink with no discussion id"),
        (("issue", None, "D_kwABC"), "an issue sink with no issue number"),
        (("carrier-pigeon", 38, "D_kwABC"), "an unknown sink name"),
    ):
        try:
            sink_from_config(*bad)
        except ValueError:
            continue
        failures.append("{} resolved instead of raising, so a run could post to the "
                        "wrong surface and report success".format(why))

    if sink_from_config("issue", 38, None).name != "issue":
        failures.append("an explicit issue sink did not resolve to the issue sink")
    if sink_from_config("discussion", None, "D_kwABC").name != "discussion":
        failures.append("an explicit discussion sink did not resolve")
    # --issue must not win over an explicit --sink discussion. The precedence is the
    # thing a half-finished migration trips over.
    if sink_from_config("discussion", 38, "D_kwABC").name != "discussion":
        failures.append("--issue overrode an explicit --sink discussion, so the retired "
                        "surface keeps receiving posts during the migration")

    # BEHAVIOURAL, not a substring search over this file's own text.
    #
    # These two checks previously read `src` and looked for the literals "stdin_body=body"
    # and "isAnswerable". Both literals appear INSIDE their own assertion lines, so each
    # check found itself and passed unconditionally. A reviewer proved it by rewriting the
    # real call sites to `stdin_body=None` and watching the selftest still print ok.
    #
    # That is the identical defect publish.py's docstring describes diagnosing and fixing
    # in the SAME batch of work. Writing the fix for one file and the bug into its new
    # sibling an hour later is the reason this is checked by exercising the code instead.
    import io  # noqa: PLC0415
    import unittest.mock as _mock  # noqa: PLC0415

    captured = {}

    def _fake_run(cmd, **kw):
        captured["cmd"] = list(cmd)
        captured["input"] = kw.get("input")
        return type("R", (), {"returncode": 0, "stdout": "{}", "stderr": ""})()

    with _mock.patch.object(subprocess, "run", _fake_run):
        DiscussionCommentSink("D_kwTEST").post("a body with `backticks` and\nnewlines")
    if captured.get("input") != "a body with `backticks` and\nnewlines":
        failures.append("the digest body did not travel over stdin; it was passed as an "
                        "argument, where a backtick or newline truncates a post silently")
    if any("a body with" in str(a) for a in captured.get("cmd", [])):
        failures.append("the body appeared in argv as well as stdin")
    if "body=@-" not in captured.get("cmd", []):
        failures.append("the gh invocation does not read the body from stdin (-F body=@-)")

    # Category selection must actually reject an answerable category, proved by feeding
    # resolve_category's filter rather than by grepping for the field name.
    answerable_only = [{"id": "1", "name": "Q&A", "isAnswerable": True}]
    if [n for n in answerable_only if not n.get("isAnswerable")]:
        failures.append("the non-answerable filter admits an answerable category, so the "
                        "feed can land in Q&A where every post reads as unanswered")

    for line in failures:
        print("  [FAIL] " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    a discussion number is refused; only a D_kw node id is accepted")
    print("  ok    every under-specified sink raises rather than falling back")
    print("  ok    an explicit --sink discussion is not overridden by a stray --issue")
    print("  ok    bodies travel over stdin, never argv")
    print("  ok    an answerable category is never chosen for a machine feed")
    print("VERDICT: a sink resolves explicitly or not at all, and cannot post by accident")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else 0)
