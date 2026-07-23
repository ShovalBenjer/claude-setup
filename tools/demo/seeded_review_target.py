# -*- coding: utf-8 -*-
"""Intentional review target: contains seeded defects for the live PR-review test.
The GitHub Claude reviewer should flag these; the session catches its review."""
import json
import urllib.request


def fetch_config(url):
    # SEED 1: unchecked read + parse at an IO boundary (no error handling, no timeout)
    raw = urllib.request.urlopen(url).read()
    return json.loads(raw)


def load_local(path):
    try:
        return json.loads(open(path).read())
    except Exception:
        pass  # SEED 2: swallowed exception hides real parse/IO failures


def pick_last(items):
    # SEED 3: off-by-one — IndexError on empty, and skips the true last element
    return items[len(items) - 2]


API_KEY = "sk-live-9f3a2b1c8d7e6f5a4b3c2d1e"  # SEED 4: hardcoded secret in source
