#!/usr/bin/env python3
"""Append-only usage ledger and daily ceiling for free-tier APIs.

OpenRouter gives 50 requests/day on :free models below $10 lifetime credit, and
20 requests/minute. Blowing through either is not a soft failure: the account
starts returning 429 and the channel is dead for the rest of the day, which is
exactly when a verifier is most wanted. So the ceiling is enforced locally,
before the request goes out, rather than discovered from an error.

The ledger is append-only JSONL. Nothing here ever rewrites or deletes a row,
per the standing rule that conversation and call history is raw material to mine
later, not scratch state. A separate counter file would be a second source of
truth that can drift from the log; counting the log is slow in theory and free
in practice at 50 rows a day.

Day boundary is UTC, because OpenRouter's documented daily limits reset at
midnight UTC, not local time. Getting this wrong in the other direction would be
the dangerous one: a local-midnight reset would let the counter go to zero while
the provider still counts the earlier calls.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = Path(os.environ.get("CLAUDE_API_LEDGER", ROOT / "state" / "api-usage.jsonl"))


def utc_day(ts: float | None = None) -> str:
    return datetime.fromtimestamp(
        ts if ts is not None else time.time(), tz=timezone.utc
    ).strftime("%Y-%m-%d")


class QuotaExhausted(RuntimeError):
    pass


class DailyQuota:
    def __init__(self, api: str, limit: int, ledger: Path | None = None) -> None:
        self.api = api
        self.limit = limit
        self.ledger = Path(ledger) if ledger else LEDGER

    def _rows(self):
        if not self.ledger.exists():
            return
        with self.ledger.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # A truncated tail row must not hide the rows above it, and
                    # must not be silently counted as a call either.
                    continue

    def rows_today(self) -> list[dict]:
        day = utc_day()
        return [r for r in self._rows() if r.get("api") == self.api and r.get("utc_day") == day]

    def used(self) -> int:
        # A 429 was refused by the provider and does not consume the daily
        # allowance, so it is logged but not counted. Every other attempt that
        # reached the provider does count, including 4xx from a bad request.
        return sum(1 for r in self.rows_today() if r.get("counted", True))

    def remaining(self) -> int:
        return max(0, self.limit - self.used())

    def guard(self) -> int:
        left = self.remaining()
        if left <= 0:
            raise QuotaExhausted(
                "{} daily free ceiling reached: {}/{} used today (UTC day {}). "
                "Resets at 00:00 UTC.".format(self.api, self.used(), self.limit, utc_day())
            )
        return left

    def last_ts(self) -> float:
        ts = [float(r.get("ts", 0)) for r in self._rows() if r.get("api") == self.api]
        return max(ts) if ts else 0.0

    def pace(self, min_interval: float) -> float:
        """Sleep just enough to respect a per-minute ceiling. Returns slept secs."""
        gap = time.time() - self.last_ts()
        if 0 <= gap < min_interval:
            time.sleep(min_interval - gap)
            return min_interval - gap
        return 0.0

    def record(self, *, counted: bool = True, **fields) -> dict:
        now = time.time()
        row = {"ts": round(now, 3), "utc_day": utc_day(now), "api": self.api,
               "counted": counted}
        row.update(fields)
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def summary(self) -> str:
        return "{}: {}/{} used on UTC day {}, {} left".format(
            self.api, self.used(), self.limit, utc_day(), self.remaining()
        )


if __name__ == "__main__":
    import sys

    api = sys.argv[1] if len(sys.argv) > 1 else "openrouter"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    q = DailyQuota(api, limit)
    print(q.summary())
    print("ledger: {}".format(q.ledger))
