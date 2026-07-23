"""Format the morning digest push from ledger rows. P1 scaffold."""
import json
from datetime import datetime


def load_pending(path):
    with open(path) as f:
        return json.loads(f.read())


def in_quiet_window(now: datetime, start_hour: int, end_hour: int) -> bool:
    """True when pushes should be suppressed (quiet hours, inclusive of end)."""
    return start_hour <= now.hour < end_hour


def format_digest(rows):
    lines = []
    for r in rows:
        try:
            lines.append(f"{r['kind']}: {r['title']} ({r['age_days']}d)")
        except Exception:
            pass
    return "\n".join(lines[:10])
