#!/usr/bin/env python3
"""DoltHub client: a versioned SQL store reachable over plain HTTPS.

What it is for here. Two standing problems in this setup want a remote, queryable,
history-keeping store and currently have none:

  1. Cross-terminal A2A. state/bus.jsonl only exists on this machine, so a lane
     running in another terminal on another box cannot see it.
  2. The raw-gold archive. Conversations and call logs are to be kept and mined
     later, never deleted. A git-tracked JSONL grows without bound and cannot be
     queried; a plain database loses the history that makes it auditable. Dolt is
     the one store that is both SQL-queryable and commit-versioned, so "what did
     this table say on the 25th" is a real query and not a backup hunt.

PRIVACY CONSTRAINT, verified 2026-07-25 against DoltHub's own pages. A plain free
DoltHub account can host PUBLIC databases only: "All databases are public unless
you have a DoltHub Pro account", and "a DoltHub Pro subscription gives you access
to the private database hosting option". Pro carries "100 MB of private data
storage free" and bills "$5/month" only above that, up to 5 GB, then "$1/GB/month".
So until a Pro account exists and is confirmed, treat every database reachable with
this client as PUBLIC: no transcripts, no employer material, no resume content, no
customer data, no key material. Schema and synthetic rows only.

API contract. Read is from DoltHub's docs; everything marked [probed] was
established empirically on 2026-07-25 because the v2 doc pages 404 and the
authenticated-read rule is not on the page that documents the read.

  v1alpha1 read   GET  {V1}/{owner}/{db}[/{ref}]?q=<sql>
                  -> {query_execution_status, query_execution_message,
                      repository_owner, repository_name, commit_ref, sql_query,
                      schema[{columnName,columnType}], rows[{col: val}]}
     [probed] Anonymous reads may omit the ref. An authenticated read MUST carry
     one: sending a token with no ref returns HTTP 400 "Calls authenticated with
     a token must include a refName". The default branch is not always main
     (dolthub/ip-to-country is master), so the ref cannot be defaulted blindly.
  v1alpha1 write  POST {V1}/{owner}/{db}/write/{from}/{to}?q=<sql>
                  -> {operation_name}
  v1alpha1 poll   GET  {V1}/{owner}/{db}/write?operationName=...
                  -> {done: bool, res_details: {...}}
  v2 sql [probed] GET  {V2}/databases/{owner}/{db}/sql?q=<sql>&ref=<branch>
                  -> {"data": {"columns": [{name,type,is_primary_key,source_table}],
                               "rows": [[...], ...]}}
     `ref` is REQUIRED and is spelled `ref`: refName and revision both return 400
     VALIDATION_FAILED, as do POST bodies keyed q or query. v2 rows are arrays,
     v1alpha1 rows are objects, so the two are not drop-in interchangeable.
  v2 branches     GET  {V2}/databases/{owner}/{db}/branches
                  -> {"data": [{name, head_commit_sha, last_updated_at}]}
  auth            Authorization: Bearer <token>
  host            www.dolthub.com. The docs are explicit: "please send requests to
                  https://www.dolthub.com, not https://dolthub.com".
  public reads    need no token at all, on both v1alpha1 and v2.

TOKEN STATUS, 2026-07-25, corrected: the token in .env under `dolthob_api_key` is
VALID. It authenticates on API v1alpha1 as user `shovalb9`, and is rejected by API
v2. The two versions accept different credential types; v2's own doc example shows a
`dh_`-prefixed token while this one leads with `dhat.`. So a v2 rejection of this
credential is a type mismatch, not a bad credential.

  arm                     v1 /user   v2 /user   v1 sql +ref   v2 branches
  anonymous               400 no authentication  200           200
  stored token            200 shovalb9  401      200           401 no token found
  synthetic, same shape   -            -         400 bad hdr   401 invalid auth hdr
  synthetic, malformed    -            -         400 bad hdr   401 invalid auth hdr

HOW THIS WAS GOT WRONG FIRST, because the mistake is instructive and cheap to repeat.
The original conclusion was "parses but is not registered". Every measurement behind
it was accurate and the reasoning on top of it was careful: the v1alpha1 200 really
is uninformative, because an anonymous caller gets the same 200 on that endpoint, and
v2 really does reject the token at the lookup stage rather than the parser. The error
was in the choice of oracle. v2/branches is the only endpoint tested where sending
the credential changed the outcome, so it was promoted to the oracle, and its verdict
was read as a verdict on the credential when it was only ever a verdict on the
credential's TYPE. The check that settles it, v1alpha1 /user, was never run: it
requires authentication, mutates nothing, refuses anonymous callers with 400 "no
authentication", and returns the username. One endpoint, and it was not on the list.

The generalisable form: an authorization oracle is only valid for the API version it
belongs to, and "this endpoint reacts to the credential" is weaker than "this endpoint
is the right place to ask". Before concluding a credential is bad, enumerate every
endpoint the docs say REQUIRES auth and test all of them, rather than promoting
whichever one happened to respond differently.

Consequence for this client: v1alpha1 writes are authorised, because `write()` posts
to V1 and V1 accepts this credential. The v2 read path works only for public
databases, anonymously, via the 401 fallback in `_get_tolerant`. A v2 credential would
have to be minted separately and is not needed by anything here.

Usage:
  client.py sql    owner/db[@ref] "SELECT ..."     v1alpha1 read
  client.py v2sql  owner/db@ref  "SELECT ..."      v2 read, ref required
  client.py tables owner/db[@ref]
  client.py write  owner/db "INSERT ..." [--from main] [--to main] [--wait 120]
  client.py merge  owner/db --from BR --to main    [unverified endpoint path]
  client.py discriminate                           three-arm real-vs-synthetic test
  client.py branches owner/db
  client.py authcheck                              is the token accepted at all
  client.py whoami                                 identity oracle, both versions
  client.py probe [--db owner/db]                  what this token can reach
  client.py selftest                               read a public db end to end
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from envload import get  # noqa: E402
from quota import DailyQuota  # noqa: E402

HOST = "https://www.dolthub.com"
V1 = HOST + "/api/v1alpha1"
V2 = HOST + "/api/v2"
# The .env spells it `dolthob_api_key`. That is the real name in the real file, so
# it leads the list; the conventional spellings follow for portability.
KEY_NAMES = ("dolthob_api_key", "dolthub_api_key", "DOLTHUB_API_KEY", "DOLT_API_TOKEN")
# DoltHub publishes no numeric free-tier request ceiling, so this is a local
# self-imposed cap, not a provider limit. It exists to bound a runaway loop.
SELF_CAP_PER_DAY = 500

PUBLIC_DEMO_DB = "dolthub/ip-to-country"  # the database DoltHub's own docs query
PUBLIC_DEMO_REF = "master"                # its default branch is master, not main

# Synthetic tokens for the differential test in cmd_discriminate. Both are
# hardcoded nonsense and are not derived from the stored credential in any way,
# so they can appear in source, in output, and in a shell command safely. The
# first imitates the stored credential's shape (60 characters, 'dhat' lead, one
# dot, charset [A-Za-z0-9._-]); the second does not imitate anything.
FAKE_WELLFORMED = "dhat." + ("0" * 55)
FAKE_MALFORMED = "obviously-not-a-dolthub-token"


def token() -> str | None:
    """The API token if present. Absence is legal: public reads need none."""
    return get(*KEY_NAMES)


def _http(method: str, url: str, *, auth: bool = True, timeout: int = 120,
          body: bytes | None = None, as_token: str | None = None,
          scheme: str = "Bearer") -> tuple[int, dict]:
    """One request.

    as_token substitutes a caller-supplied string for the stored token, which is
    what makes the differential test in cmd_discriminate possible: a synthetic
    token of the same shape goes out instead of the real one.

    scheme exists because DoltHub's two API versions document two different
    schemes for the same credential. v1alpha1's example sends
    'authorization: token <t>'; v2's sends 'Authorization: Bearer <t>'. Sending
    v2's scheme to a v1alpha1 endpoint is a plausible way to get a rejection
    that has nothing to do with the credential being wrong, so the caller picks.
    """
    headers = {"Accept": "application/json"}
    tok = as_token if as_token is not None else (token() if auth else None)
    if tok:
        headers["Authorization"] = ("{} {}".format(scheme, tok) if scheme else tok)
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw[:800]}
    except urllib.error.URLError as e:
        # Status 0 is reserved for "the request never reached DoltHub". Folding
        # this into a 4xx would let a dead network read as a refusal.
        return 0, {"error": "transport failure: {}".format(e.reason)}
    except json.JSONDecodeError as e:
        return -1, {"error": "non-JSON response: {}".format(e)}


def _get_tolerant(url: str, timeout: int = 120) -> tuple[int, dict, bool]:
    """GET with the token, and fall back to anonymous if the token is rejected.

    A rejected token would otherwise break reads that need no token at all: v2
    answers 401 for every request carrying an unknown token, public database or
    not. Retrying without the header keeps public reads working while the token
    is broken, and the returned flag makes that visible instead of silent.
    """
    status, data = _http("GET", url, auth=bool(token()), timeout=timeout)
    if status == 401 and token():
        status, data = _http("GET", url, auth=False, timeout=timeout)
        return status, data, True
    return status, data, False


def _err(body: dict) -> str:
    """One line of whatever the API said, across both error shapes."""
    if not isinstance(body, dict):
        return str(body)[:300]
    for k in ("query_execution_message", "detail", "error", "raw"):
        if body.get(k):
            return str(body[k])[:300]
    return json.dumps(body)[:300]


def _log(op: str, status: int, **fields) -> None:
    DailyQuota("dolthub", SELF_CAP_PER_DAY).record(op=op, status=status, **fields)


def split_db(spec: str) -> tuple[str, str, str | None]:
    """'owner/db@branch' -> (owner, db, branch|None)."""
    ref = None
    if "@" in spec:
        spec, ref = spec.split("@", 1)
    if spec.count("/") != 1:
        raise SystemExit("database must be owner/name, got {!r}".format(spec))
    owner, db = spec.split("/", 1)
    return owner, db, ref


def sql(spec: str, query: str) -> dict:
    """v1alpha1 read.

    Auth is sent only when a ref is given, because DoltHub rejects an
    authenticated read that has no refName. Dropping the header for a ref-less
    read is not a workaround: public reads need no token, and a private database
    needs an explicit ref anyway, which the error below asks for.
    """
    owner, db, ref = split_db(spec)
    path = "{}/{}/{}".format(V1, owner, db) + ("/" + ref if ref else "")
    url = path + "?" + urllib.parse.urlencode({"q": query})
    status, data = _http("GET", url, auth=bool(ref))
    _log("read", status, db="{}/{}".format(owner, db), ref=ref, authed=bool(ref),
         rows=len(data.get("rows") or []) if isinstance(data, dict) else None)
    if status in (401, 403, 404) and not ref:
        raise SystemExit(
            "dolthub read HTTP {} for {}/{} with no ref. A public database reads "
            "anonymously; a private one needs both a token and an explicit ref. "
            "Retry as {}/{}@<branch>.\n{}".format(status, owner, db, owner, db,
                                                  _err(data)))
    if status != 200:
        raise SystemExit("dolthub read HTTP {}: {}".format(status, _err(data)))
    if data.get("query_execution_status") not in (None, "Success"):
        raise SystemExit("dolthub query failed: {} {}".format(
            data.get("query_execution_status"), _err(data)))
    return data


def sql_v2(spec: str, query: str) -> dict:
    """v2 read. `ref` is mandatory server-side, so it is mandatory here."""
    owner, db, ref = split_db(spec)
    if not ref:
        raise SystemExit("v2 sql requires a branch: use owner/db@branch "
                         "(v2 returns 400 VALIDATION_FAILED without ref)")
    url = "{}/databases/{}/{}/sql?{}".format(
        V2, owner, db, urllib.parse.urlencode({"q": query, "ref": ref}))
    status, data, fell_back = _get_tolerant(url)
    payload = data.get("data") or {}
    _log("read_v2", status, db="{}/{}".format(owner, db), ref=ref,
         rows=len(payload.get("rows") or []), anon_fallback=fell_back)
    if fell_back:
        print("note: the token was rejected, so this read went out anonymously. "
              "It only works because the database is public.", file=sys.stderr)
    if status != 200:
        raise SystemExit("dolthub v2 read HTTP {}: {}".format(status, _err(data)))
    return payload


def write(spec: str, query: str, from_branch: str, to_branch: str,
          wait_s: int) -> dict:
    owner, db, _ = split_db(spec)
    if not token():
        raise SystemExit("write needs a token: none of {} is set".format(
            " / ".join(KEY_NAMES)))
    url = "{}/{}/{}/write/{}/{}?{}".format(
        V1, owner, db, urllib.parse.quote(from_branch), urllib.parse.quote(to_branch),
        urllib.parse.urlencode({"q": query}))
    status, data = _http("POST", url)
    _log("write", status, db="{}/{}".format(owner, db),
         branch="{}->{}".format(from_branch, to_branch))
    if status == 401:
        raise SystemExit(
            "dolthub write refused the token (HTTP 401: {}). Mint a fresh one at "
            "dolthub.com/settings/tokens and put it in .env as dolthob_api_key, "
            "then re-check with: client.py authcheck".format(_err(data)))
    if status != 200:
        raise SystemExit("dolthub write HTTP {}: {}".format(status, _err(data)))
    op = data.get("operation_name")
    if not op:
        raise SystemExit("write returned no operation_name: {}".format(
            json.dumps(data)[:500]))
    if wait_s <= 0:
        return data
    return poll(spec, op, wait_s)


def poll(spec: str, operation_name: str, wait_s: int) -> dict:
    owner, db, _ = split_db(spec)
    url = "{}/{}/{}/write?{}".format(
        V1, owner, db, urllib.parse.urlencode({"operationName": operation_name}))
    deadline = time.time() + wait_s
    delay = 1.0
    last: dict = {}
    while time.time() < deadline:
        status, last = _http("GET", url)
        if status != 200:
            raise SystemExit("poll HTTP {}: {}".format(status, _err(last)))
        if last.get("done"):
            _log("poll", status, done=True, op=operation_name)
            return last
        time.sleep(delay)
        delay = min(delay * 1.6, 8.0)
    _log("poll", 200, done=False, op=operation_name)
    raise SystemExit("write did not finish within {}s; operation {} is still "
                     "running. Poll it again rather than resubmitting.".format(
                         wait_s, operation_name))


def rows_table(data: dict, limit: int) -> str:
    """Render either API shape: v1alpha1 dict-rows or v2 array-rows."""
    if "columns" in data:  # v2
        cols = [c["name"] for c in (data.get("columns") or [])]
        rows = [list(r) for r in (data.get("rows") or [])]
    else:                  # v1alpha1
        cols = [c["columnName"] for c in (data.get("schema") or [])]
        dicts = data.get("rows") or []
        if not cols and dicts:
            cols = list(dicts[0].keys())
        rows = [[d.get(c) for c in cols] for d in dicts]
    out = []
    if cols:
        out.append(" | ".join(cols))
        out.append("-+-".join("-" * len(c) for c in cols))
    for r in rows[:limit]:
        out.append(" | ".join("" if v is None else str(v) for v in r))
    if len(rows) > limit:
        out.append("... and {} more row(s)".format(len(rows) - limit))
    return "\n".join(out) if out else "(no rows)"


def cmd_sql(args) -> int:
    data = sql(args.db, args.query)
    if args.json:
        print(json.dumps(data.get("rows") or [], indent=2, ensure_ascii=False))
    else:
        print("{}/{} @ {}".format(data.get("repository_owner"),
                                  data.get("repository_name"),
                                  data.get("commit_ref")))
        print(rows_table(data, args.limit))
    return 0


def cmd_v2sql(args) -> int:
    payload = sql_v2(args.db, args.query)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:8000])
    else:
        print(rows_table(payload, args.limit))
    return 0


def cmd_tables(args) -> int:
    print(rows_table(sql(args.db, "SHOW TABLES"), args.limit))
    return 0


def cmd_write(args) -> int:
    print(json.dumps(write(args.db, args.query, args.from_branch, args.to_branch,
                           args.wait), indent=2)[:4000])
    return 0


def cmd_merge(args) -> int:
    # UNVERIFIED path: the v1alpha1 merge endpoint is not on any doc page that
    # resolves. The printed status is the evidence. A 404 means the real path
    # differs and belongs in the contract block above, not in a retry loop.
    owner, db, _ = split_db(args.db)
    url = "{}/{}/{}/merge/{}/{}".format(V1, owner, db,
                                        urllib.parse.quote(args.from_branch),
                                        urllib.parse.quote(args.to_branch))
    status, data = _http("POST", url)
    _log("merge", status, db="{}/{}".format(owner, db))
    print("POST {}\nHTTP {}\n{}".format(url, status, json.dumps(data, indent=2)[:2000]))
    return 0 if status == 200 else 1


def cmd_branches(args) -> int:
    owner, db, _ = split_db(args.db)
    url = "{}/databases/{}/{}/branches".format(V2, owner, db)
    status, data, fell_back = _get_tolerant(url)
    if fell_back:
        print("(token rejected, retried anonymously)")
    _log("branches", status, db="{}/{}".format(owner, db), anon_fallback=fell_back)
    if status != 200:
        print("HTTP {}: {}".format(status, _err(data)))
        return 1
    for b in data.get("data") or []:
        print("{:24s} {}  {}".format(b.get("name", ""), b.get("head_commit_sha", ""),
                                     b.get("last_updated_at", "")))
    return 0


def cmd_authcheck(args) -> int:
    """Is this token accepted by DoltHub at all?

    The oracle is v1alpha1 /user, and picking it correctly took two tries. The
    first version of this function used a v2 endpoint on the reasoning that v2
    was the only cheap endpoint that positively rejects a bad token. That
    reasoning was sound and the conclusion it produced was still wrong, because
    v2 rejects a perfectly valid v1alpha1 token: the two versions accept
    different credential types, and a 'dhat.' personal token is v1alpha1's.
    Measuring rejection on the wrong version reads as a bad credential.

    v1alpha1 /user is the right oracle because it requires authentication on the
    version this token belongs to, mutates nothing, and answers an anonymous
    caller with 400 'no authentication'. That last property is what makes its
    200 positive proof rather than another ambiguous public read.

    Use `whoami` for the full four-combination picture across both versions.
    """
    tok = token()
    if not tok:
        print("no token: none of {} is set in .env or the environment".format(
            " / ".join(KEY_NAMES)))
        return 2
    url = "{}/user".format(V1)
    status, data = _http("GET", url, auth=True, timeout=45, scheme="token")
    anon_status, _ = _http("GET", url, auth=False, timeout=45)
    print("oracle: GET {}".format(url))
    print("  with token: HTTP {}  {}".format(status,
                                             _err(data) if status != 200 else "ok"))
    print("  anonymous : HTTP {}".format(anon_status))
    if status == 200 and anon_status != 200:
        body = data.get("data") if isinstance(data.get("data"), dict) else data
        print("VERDICT: ACCEPTED. The endpoint refuses anonymous callers and accepted "
              "this one as {!r}, so the credential is genuinely registered and "
              "v1alpha1 writes are authorised.".format(body.get("username")))
        print("  Note: API v2 rejects this token. That is a credential-type mismatch, "
              "not a bad token. v2 wants its own credential; mint one separately if a "
              "v2-only endpoint is ever needed.")
        return 0
    if status == 401:
        # DoltHub uses different text for the two failure modes, and the difference
        # is the whole diagnosis: "invalid authorization header" is thrown out at the
        # parser, "no token found" got parsed and then missed a lookup. Collapsing
        # both into "rejected" loses the one fact that says where to go next.
        detail = _err(data).lower()
        if "no token found" in detail:
            print("VERDICT: the token PARSES but the lookup MISSED. DoltHub found no "
                  "stored token matching it, which narrows the cause to revoked, "
                  "deleted, altered, or issued by another deployment. It does not fit "
                  "a valid token owned by someone else: that would be found and would "
                  "come back as a permission error, not a lookup miss.")
        elif "invalid authorization header" in detail:
            print("VERDICT: the token is MALFORMED. DoltHub rejected it at the parser "
                  "without a lookup, so the stored value is the wrong shape, not "
                  "merely the wrong token.")
        else:
            print("VERDICT: rejected with 401, and the message is one this tool has "
                  "not seen before. Treat the cause as unknown.")
        print("  Public reads still work because they need no token; writes do not. "
              "Before concluding the token is bad, run `client.py whoami`: it tries "
              "both documented header schemes against both API versions, and a "
              "rejection on only one version is a credential-type mismatch rather "
              "than a bad credential.")
        return 1
    if status == 200 and anon_status == 200:
        print("VERDICT: UNPROVEN, and this is a defect in the check rather than a "
              "finding. The oracle answered an anonymous caller, so it is not "
              "gating on authentication and its 200 carries no information. Fix the "
              "oracle before trusting any verdict from it.")
        return 1
    print("VERDICT: unexpected status {}, treat as unproven".format(status))
    return 1


def cmd_whoami(args) -> int:
    """Ask DoltHub who this credential belongs to. The real identity oracle.

    Every earlier check in this file used an endpoint that serves anonymous
    callers, which is why they could only ever produce weak evidence: a 200 was
    ambiguous and a 401 could in principle be about the scheme rather than the
    credential. The user endpoints are different in kind. Both API versions
    document one, both REQUIRE authentication, and neither mutates anything, so
    a 200 here is positive proof of acceptance and names the account.

    Both documented schemes are tried against both versions, four combinations,
    because the two docs disagree about the scheme and guessing wrong would
    manufacture a false rejection. Emails are counted, never printed.
    """
    tok = token()
    if not tok:
        print("no token: none of {} is set in .env or the environment".format(
            " / ".join(KEY_NAMES)))
        return 2

    attempts = [
        ("v1alpha1 /user", "{}/user".format(V1), "token"),
        ("v1alpha1 /user", "{}/user".format(V1), "Bearer"),
        ("v2 /user", "{}/user".format(V2), "Bearer"),
        ("v2 /user", "{}/user".format(V2), "token"),
    ]
    accepted: list[tuple[str, str, dict]] = []
    print("identity oracle: endpoints that require authentication and change nothing")
    for label, url, scheme in attempts:
        status, data = _http("GET", url, auth=True, timeout=45, scheme=scheme)
        _log("whoami", status, endpoint=label, scheme=scheme)
        note = "ok" if status == 200 else _err(data)
        print("  {:<16} scheme {:<7} HTTP {:>3}  {}".format(label, scheme, status, note))
        if status == 200:
            accepted.append((label, scheme, data))

    # An anonymous arm keeps the same discipline the rest of this file uses: if
    # these endpoints answered 200 without any credential they would be public,
    # and a 200 with the credential would prove nothing again.
    anon_status, anon_data = _http("GET", "{}/user".format(V1), auth=False, timeout=45)
    print("  {:<16} {:<14} HTTP {:>3}  {}".format(
        "v1alpha1 /user", "anonymous", anon_status,
        "ok" if anon_status == 200 else _err(anon_data)))
    if anon_status == 200:
        print("VERDICT: this endpoint answered an anonymous caller, so it is not the "
              "auth oracle the docs describe. Treat every result above as unproven.")
        return 1

    if not accepted:
        print("VERDICT: REJECTED by every endpoint that actually checks a credential, "
              "under both documented header schemes. This is the strongest available "
              "evidence that the stored value is not a credential DoltHub recognises. "
              "The next step is on the DoltHub settings page, not in this code.")
        return 1

    for label, scheme, data in accepted:
        body = data.get("data") if isinstance(data.get("data"), dict) else data
        emails = body.get("email_addresses") or []
        print("VERDICT: ACCEPTED by {} using scheme {!r}.".format(label, scheme))
        print("  username     : {}".format(body.get("username", "(absent)")))
        print("  display name : {}".format(body.get("display_name") or "(empty)"))
        print("  emails       : {} on file, not printed".format(len(emails)))
    if len(accepted) < len(attempts):
        rejected = [(l, s) for l, _u, s in attempts
                    if (l, s) not in [(a[0], a[1]) for a in accepted]]
        print("  note: accepted on some combinations and not others: {} still refuse "
              "it. The credential is real; the scheme or the API version is what "
              "differs.".format(", ".join("{}+{}".format(l, s) for l, s in rejected)))
    return 0


def cmd_probe(args) -> int:
    """Empirical discovery of what this token can reach. Statuses only."""
    tok = token()
    print("token present: {}".format("yes" if tok else "NO (public reads only)"))
    q = urllib.parse.urlencode({"q": "SHOW TABLES"})
    demo_ref = urllib.parse.urlencode({"q": "SHOW TABLES", "ref": PUBLIC_DEMO_REF})
    checks = [
        ("v1 anon, no ref", "GET", "{}/{}?{}".format(V1, PUBLIC_DEMO_DB, q), False),
        ("v1 auth, no ref", "GET", "{}/{}?{}".format(V1, PUBLIC_DEMO_DB, q), True),
        ("v1 auth, with ref", "GET",
         "{}/{}/{}?{}".format(V1, PUBLIC_DEMO_DB, PUBLIC_DEMO_REF, q), True),
        ("v2 sql, ref", "GET",
         "{}/databases/{}/sql?{}".format(V2, PUBLIC_DEMO_DB, demo_ref), True),
        ("v2 branches, auth", "GET",
         "{}/databases/{}/branches".format(V2, PUBLIC_DEMO_DB), True),
        ("v2 branches, anon", "GET",
         "{}/databases/{}/branches".format(V2, PUBLIC_DEMO_DB), False),
    ]
    if args.db:
        owner, db, ref = split_db(args.db)
        r = ref or "main"
        checks.append(("v1 auth {}@{}".format(args.db, r), "GET",
                       "{}/{}/{}/{}?{}".format(V1, owner, db, r, q), True))
        checks.append(("v2 branches {}".format(args.db), "GET",
                       "{}/databases/{}/{}/branches".format(V2, owner, db), True))
    worst = 0
    for label, method, url, auth in checks:
        status, data = _http(method, url, auth=auth, timeout=45)
        note = "ok" if status == 200 else _err(data)[:90]
        print("  {:26s} auth={:5s} HTTP {:>4}  {}".format(label, str(auth), status, note))
        if status == 0:
            worst = 1
    return worst


def cmd_discriminate(args) -> int:
    """Does an endpoint tell a real token apart from a fake one?

    This exists because of a specific reasoning error it is designed to catch. The
    probe shows 'v1 auth, with ref -> HTTP 200', and it is tempting to read that
    either as the token being accepted or as the 200 carrying no information. Both
    readings are guesses until the endpoint is shown to discriminate. So each
    endpoint is called three ways: anonymously, with the stored token, and with a
    synthetic token of the same shape that certainly is not registered.

      stored == synthetic  ->  the endpoint does not check the token, so its
                               status says nothing whatsoever about the stored one
      stored != synthetic  ->  the endpoint does check, so its status is evidence

    A malformed third string separates 'unknown token' from 'unparseable token'.
    If the error text for a well-formed fake matches the text for the stored one,
    the stored one is being looked up and missed, not rejected as garbage.
    """
    tok = token()
    if not tok:
        print("no token stored: nothing to discriminate against")
        return 2
    q = urllib.parse.urlencode({"q": "SELECT 1 AS ok"})
    endpoints = [
        ("v1 sql, with ref",
         "{}/{}/{}?{}".format(V1, PUBLIC_DEMO_DB, PUBLIC_DEMO_REF, q)),
        ("v2 branches",
         "{}/databases/{}/branches".format(V2, PUBLIC_DEMO_DB)),
    ]
    # as_token=None with auth=False means no header at all; the stored token is
    # sent by reference and never materialises in this function's output.
    arms = [
        ("anonymous", False, None),
        ("stored token", True, None),
        ("synthetic, right shape", True, FAKE_WELLFORMED),
        ("synthetic, malformed", True, FAKE_MALFORMED),
    ]
    verdicts = {}
    results = {}
    for label, url in endpoints:
        print("{}".format(label))
        seen = results[label] = {}
        for arm, auth, fake in arms:
            status, data = _http("GET", url, auth=auth, timeout=45, as_token=fake)
            _log("discriminate", status, endpoint=label, arm=arm)
            msg = "ok" if status == 200 else _err(data)[:80]
            print("  {:24s} HTTP {:>4}  {}".format(arm, status, msg))
            seen[arm] = (status, msg)
        stored = seen["stored token"]
        fake_ok = seen["synthetic, right shape"]
        anon = seen["anonymous"]
        # Three distinct things an endpoint can be doing, and only the third one
        # produces evidence about whether this token is registered. Reacting to a
        # fake is not enough: an endpoint can reject unparseable header syntax and
        # still never authorize anything, which is what v1alpha1 does on a public
        # database. The test for real authorization evidence is whether sending the
        # token changed the outcome relative to sending nothing.
        if stored == fake_ok:
            verdicts[label] = "blind"
            print("  -> BLIND: the stored token and a token that cannot possibly be "
                  "valid get identical answers, so this endpoint says nothing about "
                  "the stored token either way.")
        elif stored == anon:
            verdicts[label] = "parse-only"
            print("  -> PARSE-ONLY: the header is syntax-checked, since a synthetic "
                  "string is turned away, but the stored token produces exactly the "
                  "anonymous result. Authorization did not change the outcome, so "
                  "this 200 is not evidence the token was accepted.")
        else:
            verdicts[label] = "authorizing"
            direction = "succeeds" if stored[0] == 200 else "fails"
            print("  -> AUTHORIZING: sending the stored token changes the outcome "
                  "versus sending nothing, so this endpoint's answer is real "
                  "evidence, and here the stored token {}.".format(direction))
        if stored[0] in (401, 403) and "no token found" in stored[1].lower() \
                and "invalid authorization header" in fake_ok[1].lower():
            print("     The two failures differ in kind: the synthetic string dies at "
                  "the parser, the stored token gets parsed and then misses a lookup.")

    print("")
    authorizing = [k for k, v in verdicts.items() if v == "authorizing"]
    accepted = [k for k, v in verdicts.items()
                if v == "authorizing" and results[k]["stored token"][0] == 200]
    if not authorizing:
        print("CONCLUSION: no endpoint tested here lets authorization change the "
              "outcome, so none of them can confirm the token. Acceptance stays "
              "unproven; an authenticated write against a database this account owns "
              "would settle it.")
        return 1
    if not accepted:
        print("CONCLUSION: the only endpoint where authorization changes the outcome "
              "({}) rejects this token, and rejects it at the lookup stage rather "
              "than the parser. Nothing here accepts it.".format(
                  ", ".join(authorizing)))
        return 1
    print("CONCLUSION: authorization succeeds at {}.".format(", ".join(accepted)))
    return 0


def cmd_selftest(args) -> int:
    ok = True
    print("1. token by reference only (value never printed)")
    print("   {}".format("present" if token() else "ABSENT - public reads only"))

    print("2. v1alpha1 anonymous read of a public database: {}".format(PUBLIC_DEMO_DB))
    data = sql(PUBLIC_DEMO_DB, "SHOW TABLES")
    print("   ref={} fields={}".format(data.get("commit_ref"), sorted(data.keys())))
    print("   " + rows_table(data, 5).replace("\n", "\n   "))

    print("3. v1alpha1 authenticated read (needs an explicit ref)")
    d3 = sql("{}@{}".format(PUBLIC_DEMO_DB, PUBLIC_DEMO_REF), "SELECT 1 AS ok")
    print("   status={!r} rows={}".format(d3.get("query_execution_status"),
                                          d3.get("rows")))

    # A failing step must not abort the remaining steps: the point of a selftest
    # is to report every check, and step 5 is the one that explains a step-4 401.
    print("4. v2 read (ref required, rows come back as arrays)")
    try:
        p = sql_v2("{}@{}".format(PUBLIC_DEMO_DB, PUBLIC_DEMO_REF), "SHOW TABLES")
        print("   columns={} rows={}".format(
            [c["name"] for c in p.get("columns") or []], p.get("rows")))
    except SystemExit as e:
        print("   FAILED: {}".format(e))
        ok = False

    print("5. is the token actually accepted")
    if cmd_authcheck(args) == 1:
        ok = False

    # Step 5 says whether a 401 came back. Step 6 says whether any of these
    # endpoints can be trusted to mean anything by it, which step 5 cannot know.
    print("6. does any endpoint tell a real token from a fake one")
    cmd_discriminate(args)

    print("7. local ledger")
    print("   " + DailyQuota("dolthub", SELF_CAP_PER_DAY).summary())
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sql")
    p.add_argument("db")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_sql)

    p = sub.add_parser("v2sql")
    p.add_argument("db")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_v2sql)

    p = sub.add_parser("tables")
    p.add_argument("db")
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(fn=cmd_tables)

    p = sub.add_parser("write")
    p.add_argument("db")
    p.add_argument("query")
    p.add_argument("--from", dest="from_branch", default="main")
    p.add_argument("--to", dest="to_branch", default="main")
    p.add_argument("--wait", type=int, default=120)
    p.set_defaults(fn=cmd_write)

    p = sub.add_parser("merge")
    p.add_argument("db")
    p.add_argument("--from", dest="from_branch", required=True)
    p.add_argument("--to", dest="to_branch", default="main")
    p.set_defaults(fn=cmd_merge)

    p = sub.add_parser("branches")
    p.add_argument("db")
    p.set_defaults(fn=cmd_branches)

    p = sub.add_parser("authcheck")
    p.set_defaults(fn=cmd_authcheck)

    p = sub.add_parser("whoami")
    p.set_defaults(fn=cmd_whoami)

    p = sub.add_parser("probe")
    p.add_argument("--db")
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("discriminate")
    p.set_defaults(fn=cmd_discriminate)

    p = sub.add_parser("selftest")
    p.set_defaults(fn=cmd_selftest)

    args = ap.parse_args(argv[1:])
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
