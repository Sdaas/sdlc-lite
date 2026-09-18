"""Leaf utilities shared by both readers.

This is a LEAF dependency: runlog.py and transcript.py may both import it, but
that does NOT couple them to each other. It contains only pure, stateless
helpers (no I/O, no model calls).
"""
from __future__ import annotations

import datetime as _dt


def parse_ts(value: str) -> _dt.datetime | None:
    """Parse an ISO-8601 timestamp into a tz-AWARE UTC datetime, tolerantly.

    Handles the two clocks the analyzer meets:
      - the run-log:    UTC, tz-aware  ("2026-09-09T07:39:48+00:00")
      - the transcript: UTC, "Z" suffix ("2026-09-09T06:12:53.445Z")

    Robustness (second line of defense, on top of the guard.py UTC fix): a naive
    timestamp is ASSUMED to be UTC rather than rejected, so an older run-log or a
    differently-configured host still correlates instead of silently mismatching.
    Returns None on anything unparseable (callers skip such lines).
    """
    if not value or not isinstance(value, str):
        return None
    v = value.strip().replace("Z", "+00:00")  # fromisoformat accepts "+00:00", not "Z"
    try:
        dt = _dt.datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)  # assume UTC, don't reject
    return dt.astimezone(_dt.timezone.utc)
