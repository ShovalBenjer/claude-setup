# -*- coding: utf-8 -*-
"""Lifetime of the decrypted WhatsApp store: stamp it, expire it, delete it.

`wa_decrypt.py` writes a full plaintext copy of every message the operator has
into a temp directory and, until this module existed, nothing anywhere removed
it. `docs/prior-art/dot-claude-skills-whatsapp-query.json` recorded that on
2026-07-31 as the component's one named defect, and set the terms plainly: a
tool that silently creates a permanent unencrypted copy of every message you
have is worse than not having the tool, so if the defect is still open at the
October recheck the verdict moves to replace-or-delete. This is the fix, not a
mitigation of it.

Deleting the store immediately would break the only workflow it exists for,
since `wa_query.py` is a separate process that reads what `wa_decrypt.py` wrote.
The store is therefore given a lifetime instead of a lifespan: `wa_decrypt.py`
purges anything already there before it writes and stamps what it writes, and
`wa_query.py` refuses to read a store older than the TTL and deletes it on the
way to refusing. An abandoned store expires on the next use of the skill rather
than sitting on disk until someone remembers it.

Every function here is pure Python over a directory path with no Windows API,
no DPAPI-NG and no `cryptography` import, which is what makes `tests/
test_wa_store.py` runnable on the Linux host where the rest of this component
cannot execute at all.
"""
from __future__ import annotations

import os
import shutil
import time

STAMP = ".wa-decrypted-at"

# One hour. The store's value is answering a question the operator is asking
# now, and the SKILL's own flow is decrypt-then-query within one session. An
# hour covers a long session with room to spare while bounding how long a
# forgotten store survives. Nothing measured this; it is a judgement, and the
# knob is here so it can be argued with rather than buried in a call site.
DEFAULT_TTL_SECONDS = 3600


def stamp(dbdir: str, now: float | None = None) -> str:
    """Record when this store was written, and return the stamp path."""
    path = os.path.join(dbdir, STAMP)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(repr(float(time.time() if now is None else now)) + "\n")
    return path


def age_seconds(dbdir: str, now: float | None = None) -> float | None:
    """Seconds since this store was written, or None if it carries no stamp.

    An unstamped directory is not treated as fresh. Every caller reads None as
    unknown-age and purges, because the only ways to get one are a store written
    before this module existed and a store somebody hand-assembled, and both are
    exactly the abandoned plaintext this exists to remove.
    """
    path = os.path.join(dbdir, STAMP)
    try:
        with open(path, encoding="utf-8") as fh:
            written = float(fh.read().strip())
    except (OSError, ValueError):
        return None
    return (time.time() if now is None else now) - written


def purge(dbdir: str) -> int:
    """Delete the store. Returns how many files went with it, 0 if absent.

    The count is returned rather than printed so a caller can say whether
    anything was actually there, which is the difference between a cleanup that
    ran and a cleanup that had nothing to do.
    """
    if not os.path.isdir(dbdir):
        return 0
    removed = sum(len(files) for _, _, files in os.walk(dbdir))
    shutil.rmtree(dbdir)
    return removed


# How far into the future a stamp may sit before it is disbelieved. A stamp is
# written by one process and read by another, so a little skew is ordinary. A
# lot of it means a clock moved or the file was edited, and a store stamped an
# hour ahead would otherwise read as fresh for an hour longer than it should,
# or forever if the stamp is far enough out. Found by the round-trip test, which
# measured a NEGATIVE age of 0.14ms because the first version rounded the stamp
# up to the millisecond with "{:.3f}".
FUTURE_TOLERANCE_SECONDS = 60


def expired(dbdir: str, ttl: float = DEFAULT_TTL_SECONDS,
            now: float | None = None) -> bool:
    """True when the store must not be read: too old, future-dated, or unstamped."""
    if not os.path.isdir(dbdir):
        return False
    age = age_seconds(dbdir, now)
    if age is None:
        return True
    return age > ttl or age < -FUTURE_TOLERANCE_SECONDS


def purge_if_expired(dbdir: str, ttl: float = DEFAULT_TTL_SECONDS,
                     now: float | None = None) -> int | None:
    """Delete an expired store. Returns files removed, or None if it was fresh."""
    if not expired(dbdir, ttl, now):
        return None
    return purge(dbdir)
