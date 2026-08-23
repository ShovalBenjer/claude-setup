---
name: whatsapp-query
description: Decrypt and query the local WhatsApp Desktop (Windows) message store as a searchable corpus. Full history the linked device holds, by contact / date / text, with contact-name resolution. Triggers on "search my whatsapp", "query whatsapp history", "what did <name> say about X", "decrypt my whatsapp", "when did I talk to <name> about Y". Local-only, read-only queries, never sends anything out.
model: opus
---

# WhatsApp Query

Turn the local WhatsApp Desktop store into a queryable corpus: decrypt once, then
search messages by contact, date, or text, with names resolved from the contacts DB.

This runs entirely on the user's own machine, in the user's own security context,
against their own data. It is a personal recall tool, not surveillance of anyone
else.

## Hard boundaries

- **Local only.** Never upload, paste, commit, or send the decrypted store or its
  contents anywhere. It contains every message the user has. Treat it like a
  password vault.
- **Read-only.** Queries never write to the live WhatsApp store; decryption works
  on a snapshot copy and only writes decrypted output to a local temp dir.
- **Surface, don't dump.** When answering a question, return the specific messages
  that answer it, not the whole corpus. Keep other people's chat contents out of
  memory files, commits, reports, and any third-party tool or model call.
- **Do not commit this skill's output** or point it at a repo path. Decrypted DBs
  belong under a local temp dir, gitignored by location.

## Prerequisites

- Windows, WhatsApp Desktop (WebView2 build, i.e. package `*WhatsAppDesktop*` with
  a `LocalCache\EBWebView` dir) installed and **linked** (logged in).
- Run as the same Windows user that WhatsApp runs as (DPAPI-NG unwraps per-user).
- `uv` available; the decryptor needs the `cryptography` package.

## Step 1: decrypt (once, or to refresh)

```
uv run --with cryptography python ~/.claude/skills/whatsapp-query/wa_decrypt.py [OUTPUT_DIR]
```

- Default `OUTPUT_DIR` is `%LOCALAPPDATA%\Temp\wa-decrypted`.
- Writes `genericStorage.dec.db` (messages) and `contacts.dec.db` (names) there.
- Works while WhatsApp is running (reads files with shared access). It never
  modifies the live store.
- Re-run to pick up newer messages (the store updates as the linked device syncs).

## Step 2: query (read-only)

```
uv run python ~/.claude/skills/whatsapp-query/wa_query.py [--db DIR] <command>
```

Commands:

| Command | What it does |
| --- | --- |
| `contacts [substr] [--limit N]` | list chats/groups by volume, with names and IDs |
| `stats [name]` | message count + date range (a contact, or all chats) |
| `search <term> [--contact name] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--limit N]` | full-text search |
| `thread <name> [--from] [--to] [--limit N]` | dump a thread chronologically |

`name` matches a contact by exact name first, then substring; the busiest matching
thread wins ties. Pass a raw `chatId` (e.g. `53403707257078@lid`) for precision.

Examples:

```
wa_query.py contacts עידו
wa_query.py stats עידו
wa_query.py search "איטליה" --contact עידו --from 2025-08-01 --limit 40
wa_query.py thread עידו --from 2026-07-25
```

## What the data is, and isn't

- **Coverage** is what the linked device has synced, not necessarily all history.
  Report the range `stats` shows; do not claim completeness beyond it. If a
  message predates the earliest timestamp, it is simply not in this copy.
- **No sender direction.** This linked-device store's `message` table is
  `(rowid, id, chatId, timestamp, text)` with no per-row from-me flag. Thread
  output is chronological text without a ME/THEM column. To attribute a specific
  line, read it in WhatsApp Web (`data-pre-plain-text`) or infer from context, and
  say which you did.
- **Media** (photos, voice notes) are not in this DB, and WhatsApp strips EXIF/GPS
  from sent photos, so a received image has no location metadata to recover.
- **Group chats** (`chatId` ending `@g.us`) may carry a `~Sender:` prefix inside
  the text; individual chats do not.

## When answering from this corpus

- Name the evidence: quote the dated message(s), and say the contact and date.
- State coverage: "in the synced window (X to Y)…", never "you never said" from
  absence alone.
- If attribution matters and the DB can't give it, say so rather than guessing who
  said what.

## How the decryption works (provenance)

WebView2 WhatsApp Desktop encrypts its SQLite DBs at rest. The chain, all local:
ODUID from `clipc.dll`; `staticKey` sealed via DPAPI-NG `NCryptProtectSecret`
(`LOCAL=user`) seeds `session.db`; `clientKey` is carved from `session.db-wal`;
`sha1(clientKey)` names the session dir (an integrity check the decryptor asserts);
PBKDF2-HMAC-SHA256 + AES-256-CBC over the staticKey derives the `nativeSettings`
key; per-type keys there (type 1 = messages/`genericStorage`, type 2 = contacts)
decrypt the AES-OFB page-encrypted databases. Reverse-engineering per Kim et al.,
*FSI: Digital Investigation* v52 (2025), and the ZAPiXDESK write-up; reimplemented
here in Python (no third-party binary is executed).
