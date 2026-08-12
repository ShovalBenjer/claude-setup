"""The decrypted WhatsApp store expires and is deleted, tested off Windows.

The component these guard cannot run on this host at all: `wa_decrypt.py` needs
DPAPI-NG, `clipc.dll` and a linked WhatsApp Desktop install. `wa_store.py`
exists as a separate module precisely so the half that decides whether a
plaintext copy of every message survives on disk is pure Python over a
directory, and can therefore be tested on the machine the work happens on
rather than asserted about.

What these do NOT prove: that decryption works, that the store `wa_decrypt.py`
writes is the one `wa_query.py` opens, or anything at all about the Windows
path. They prove the lifetime rules, which is the defect
`docs/prior-art/dot-claude-skills-whatsapp-query.json` named on 2026-07-31.
"""
from __future__ import annotations

import os
import sys

import pytest

SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "dot-claude", "skills", "whatsapp-query")
sys.path.insert(0, SKILL)

import wa_store  # noqa: E402


@pytest.fixture
def store(tmp_path):
    d = tmp_path / "wa-decrypted"
    d.mkdir()
    (d / "genericStorage.dec.db").write_bytes(b"messages")
    (d / "contacts.dec.db").write_bytes(b"names")
    return str(d)


def test_purge_removes_the_store_and_counts_what_went(store):
    assert wa_store.purge(store) == 2
    assert not os.path.exists(store)


def test_purge_on_an_absent_store_is_zero_not_an_error(tmp_path):
    assert wa_store.purge(str(tmp_path / "never-existed")) == 0


def test_a_stamped_store_is_fresh_inside_its_ttl(store):
    wa_store.stamp(store, now=1000.0)
    assert wa_store.expired(store, ttl=3600, now=1000.0 + 60) is False
    assert wa_store.purge_if_expired(store, ttl=3600, now=1000.0 + 60) is None
    assert os.path.exists(store)


def test_a_stamped_store_expires_past_its_ttl_and_is_deleted(store):
    wa_store.stamp(store, now=1000.0)
    assert wa_store.expired(store, ttl=3600, now=1000.0 + 3601) is True
    # 3 files, not 2: the stamp itself is in the directory and goes with it.
    assert wa_store.purge_if_expired(store, ttl=3600, now=1000.0 + 3601) == 3
    assert not os.path.exists(store)


def test_an_unstamped_store_is_expired_rather_than_fresh(store):
    """The defect being fixed produced exactly this: a store nobody stamped.

    Treating unknown age as fresh would let every store written before this
    module existed survive forever, which is the whole exposure.
    """
    assert wa_store.age_seconds(store) is None
    assert wa_store.expired(store) is True
    assert wa_store.purge_if_expired(store) == 2


def test_an_unreadable_stamp_is_unknown_age_not_zero_age(store):
    """A corrupt stamp must fail towards deletion, not towards keeping."""
    with open(os.path.join(store, wa_store.STAMP), "w", encoding="utf-8") as fh:
        fh.write("not a number")
    assert wa_store.age_seconds(store) is None
    assert wa_store.expired(store) is True


def test_an_absent_store_is_not_expired_so_a_query_reports_its_own_error(tmp_path):
    """expired() answers about a store that exists.

    A missing directory returning True would make wa_query print the deletion
    message for a store that was never there, which reads as though something
    was removed. The absent case belongs to open_msgs, which already has its own
    message for it.
    """
    d = str(tmp_path / "gone")
    assert wa_store.expired(d) is False
    assert wa_store.purge_if_expired(d) is None


def test_stamp_then_age_round_trips_on_the_real_clock(store):
    wa_store.stamp(store)
    age = wa_store.age_seconds(store)
    assert age is not None and 0 <= age < 60


def test_a_future_dated_stamp_is_disbelieved_and_the_store_deleted(store):
    """A stamp far enough ahead would otherwise keep a store alive indefinitely.

    Reachable without malice: a clock correction between the write and the read.
    """
    wa_store.stamp(store, now=1000.0 + 7200)
    assert wa_store.expired(store, ttl=3600, now=1000.0) is True


def test_small_skew_does_not_delete_a_fresh_store(store):
    """The other side of the same knob.

    The first version of stamp() rounded to the millisecond and could write a
    time a fraction of a second in the future, so a zero tolerance here would
    delete a store that had just been written.
    """
    wa_store.stamp(store, now=1000.0 + 5)
    assert wa_store.expired(store, ttl=3600, now=1000.0) is False


def test_the_ttl_default_is_an_hour_and_is_the_one_both_callers_use():
    """Pins the number the CLI messages quote.

    wa_decrypt prints "expires in N minutes" and wa_query quotes the same N in
    its refusal. If the constant moves and a message does not, the tool lies to
    the operator about how long their messages sit in plaintext.
    """
    assert wa_store.DEFAULT_TTL_SECONDS == 3600
