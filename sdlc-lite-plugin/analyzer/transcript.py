"""Transcript reader — the BEST-EFFORT satellite.

Parses the Claude Code session transcript JSONL
(~/.claude/projects/<slug>/*.jsonl) for per-model token usage, split main-thread
vs subagent. This is the ground-truth model/token/cost source.

The isolated gates run as subagents, and Claude Code writes their transcripts NOT
inline in the main file but under a sibling directory
(~/.claude/projects/<slug>/<uuid>/subagents/*.jsonl, each with a .meta.json). Reading
only the top-level file reported "subagents: none" and hid the per-gate model split —
the analyzer's primary purpose (#15). parse_subagents() now discovers and folds them in.

Its format is officially UNSTABLE (LAUNCHING-SUBAGENTS.md / PLAN.md), so this
module is treated as fragile and QUARANTINED. It raises exactly two typed
errors, and the caller (report.py) turns them into two different degradation
messages — it never lets a transcript problem break the run-log analysis:

  - TranscriptAbsent      soft: no transcript file overlaps the run window
                          (e.g. run outside the sandbox). Expected; skip quietly.
  - TranscriptFormatError loud: a transcript WAS found but the fields we depend
                          on are gone -> Claude Code changed the format and THIS
                          PARSER needs updating. Fail loudly, never guess.

This module has ZERO knowledge of runlog.py. The only thing that crosses the
boundary is a time window (two datetimes), passed in by the caller.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path

from ._util import parse_ts

# Padding on the correlation window: absorbs clock skew and the guard hook's
# seconds-precision rounding so a turn right at the edge is still matched.
WINDOW_PAD = _dt.timedelta(minutes=5)


class TranscriptAbsent(Exception):
    """No transcript file overlaps the run window. Soft, expected degradation."""


class TranscriptFormatError(Exception):
    """A transcript was found but its schema no longer matches. Loud alarm."""


@dataclass
class ModelUsage:
    model: str
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    thinking_tokens: int = 0

    def add(self, usage: dict) -> None:
        self.turns += 1
        self.input_tokens += int(usage.get("input_tokens") or 0)
        self.output_tokens += int(usage.get("output_tokens") or 0)
        self.cache_read_tokens += int(usage.get("cache_read_input_tokens") or 0)
        self.cache_creation_tokens += int(usage.get("cache_creation_input_tokens") or 0)
        details = usage.get("output_tokens_details") or {}
        self.thinking_tokens += int(details.get("thinking_tokens") or 0)


def _bump(counts: dict[str, int], key: str | None) -> None:
    """Count one observation of a top-level per-turn field (e.g. effort). None/empty
    is skipped so a turn that simply lacks the field never invents a bucket (#31 R3)."""
    if key:
        counts[key] = counts.get(key, 0) + 1


@dataclass
class SubagentUsage:
    """One isolated-gate subagent run: its transcript file, the agent it was (from the
    sibling .meta.json, best-effort), and its per-model token usage."""
    agent_label: str
    session_file: str
    by_model: dict[str, ModelUsage] = field(default_factory=dict)
    # effort value -> turn count, from each assistant record's top-level `effort` (#31 R3).
    # The actual effort each gate ran at; #22 compares it against the agent-def pin.
    efforts: dict[str, int] = field(default_factory=dict)

    @property
    def total_turns(self) -> int:
        return sum(m.turns for m in self.by_model.values())


@dataclass
class TranscriptAnalysis:
    session_file: str
    turns_in_window: int
    main: dict[str, ModelUsage] = field(default_factory=dict)       # model -> usage
    sidechain: dict[str, ModelUsage] = field(default_factory=dict)   # model -> usage
    # Per-turn top-level `effort`, aggregated as effort -> turn count, split the same way
    # as the model buckets (main thread vs sidechain). The actual effort observed; #22
    # compares it against the pin. Absent field => empty (verdict degrades to UNKNOWN). (#31 R3)
    main_efforts: dict[str, int] = field(default_factory=dict)
    sidechain_efforts: dict[str, int] = field(default_factory=dict)
    # Per-subagent breakdown, parsed from <uuid>/subagents/*.jsonl (#15). This is the
    # per-gate model/token split — the analyzer's primary purpose. Best-effort satellite:
    # a missing/malformed subagents dir leaves this empty, never raises.
    subagents: list[SubagentUsage] = field(default_factory=list)


def find_transcript(projects_dir: Path, window_start, window_end) -> Path:
    """Pick the transcript file whose assistant turns overlap the run window (b).

    Correlating by time window (not just "newest file") is robust to stray
    concurrent sessions in the same project dir. Raises TranscriptAbsent if the
    dir is missing/empty or no file overlaps.
    """
    if window_start is None or window_end is None:
        raise TranscriptAbsent("run-log has no usable timestamps to correlate against")
    if not projects_dir.is_dir():
        raise TranscriptAbsent(f"transcript dir not found: {projects_dir}")

    lo, hi = window_start - WINDOW_PAD, window_end + WINDOW_PAD
    candidates = sorted(projects_dir.glob("*.jsonl"))
    if not candidates:
        raise TranscriptAbsent(f"no *.jsonl transcripts in {projects_dir}")

    best: tuple[int, Path] | None = None  # (overlap_count, path)
    for path in candidates:
        overlap = 0
        for ts in _iter_assistant_timestamps(path):
            if lo <= ts <= hi:
                overlap += 1
        if overlap and (best is None or overlap > best[0]):
            best = (overlap, path)

    if best is None:
        raise TranscriptAbsent(
            f"no transcript in {projects_dir} overlaps the run window "
            f"[{window_start:%Y-%m-%d %H:%M}Z .. {window_end:%H:%M}Z]"
        )
    return best[1]


def parse_transcript(path: Path, window_start, window_end) -> TranscriptAnalysis:
    """Aggregate per-model token usage from assistant turns inside the window.

    Runs a schema self-check first: if assistant turns exist but NONE carry the
    model/usage fields we depend on, that is format drift -> TranscriptFormatError
    (loud), never silently-empty output.
    """
    lo = (window_start - WINDOW_PAD) if window_start else None
    hi = (window_end + WINDOW_PAD) if window_end else None

    analysis = TranscriptAnalysis(session_file=str(path), turns_in_window=0)
    assistant_turns = 0
    usable_turns = 0

    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        # Present in the listing but unreadable now: treat as absent, not drift.
        raise TranscriptAbsent(f"could not read transcript {path}: {e}") from e

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "assistant":
            continue
        assistant_turns += 1

        ts = parse_ts(str(rec.get("timestamp") or ""))
        if ts is not None and lo is not None and hi is not None and not (lo <= ts <= hi):
            continue

        msg = rec.get("message") or {}
        model = msg.get("model")
        usage = msg.get("usage")
        if not model or not isinstance(usage, dict):
            continue  # this turn lacks the fields; self-check below catches total drift
        usable_turns += 1
        analysis.turns_in_window += 1

        is_side = bool(rec.get("isSidechain"))
        bucket = analysis.sidechain if is_side else analysis.main
        mu = bucket.get(model)
        if mu is None:
            mu = bucket[model] = ModelUsage(model=model)
        mu.add(usage)
        # #31 R3: the top-level `effort` (sibling of `message`, not inside it) is the actual
        # effort this turn ran at. Count it into the same split as the model.
        _bump(analysis.sidechain_efforts if is_side else analysis.main_efforts, rec.get("effort"))

    # Schema self-check: assistant turns present but none parseable => drift.
    if assistant_turns > 0 and usable_turns == 0:
        raise TranscriptFormatError(
            f"{assistant_turns} assistant turn(s) in {path.name} but none carried "
            f"the expected message.model / message.usage fields. The Claude Code "
            f"transcript format has likely changed; update analyzer/transcript.py."
        )
    if assistant_turns == 0:
        # A file that matched by name but has no assistant turns in window.
        raise TranscriptAbsent(f"no assistant turns found in {path.name}")

    # #15: the isolated gates run as subagents, whose transcripts Claude Code writes NOT
    # inline here but under a sibling dir <uuid>/subagents/*.jsonl. Fold them in so the
    # per-gate model split is actually reported. Extra-best-effort: never raises.
    analysis.subagents = parse_subagents(path)
    for sub in analysis.subagents:
        for model, mu in sub.by_model.items():
            agg = analysis.sidechain.get(model)
            if agg is None:
                agg = analysis.sidechain[model] = ModelUsage(model=model)
            agg.turns += mu.turns
            agg.input_tokens += mu.input_tokens
            agg.output_tokens += mu.output_tokens
            agg.cache_read_tokens += mu.cache_read_tokens
            agg.cache_creation_tokens += mu.cache_creation_tokens
            agg.thinking_tokens += mu.thinking_tokens
        for effort, n in sub.efforts.items():  # #31 R3: fold effort into the aggregate too
            analysis.sidechain_efforts[effort] = analysis.sidechain_efforts.get(effort, 0) + n

    return analysis


def _subagents_dir(main_transcript: Path) -> Path:
    """Claude Code writes subagent transcripts under <dir>/<uuid>/subagents/, where the
    main transcript is <dir>/<uuid>.jsonl (so the dir is named by the file's stem)."""
    return main_transcript.parent / main_transcript.stem / "subagents"


def _agent_label_from_meta(jsonl: Path) -> str:
    """Best-effort agent label from the sibling <name>.meta.json. Its schema is not
    guaranteed, so try several likely keys; fall back to the file stem."""
    meta = jsonl.with_suffix(".meta.json")
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return jsonl.stem
    if isinstance(data, dict):
        for key in ("agent_type", "subagent_type", "agentType", "subagentType",
                    "type", "name", "agent"):
            val = data.get(key)
            if isinstance(val, str) and val:
                return val.split(":", 1)[-1]  # strip any plugin namespace
    return jsonl.stem


def parse_subagents(main_transcript: Path) -> list[SubagentUsage]:
    """Parse each <uuid>/subagents/*.jsonl into per-model usage, attributed via the
    sibling .meta.json. EXTRA best-effort: a missing/unreadable/malformed file or dir is
    skipped silently — it must never break the load-bearing run-log analysis (P42), and a
    subagent-transcript hiccup should not even mark the main transcript section as drift."""
    sdir = _subagents_dir(main_transcript)
    if not sdir.is_dir():
        return []
    out: list[SubagentUsage] = []
    for jsonl in sorted(sdir.glob("*.jsonl")):
        by_model: dict[str, ModelUsage] = {}
        efforts: dict[str, int] = {}
        try:
            raw_lines = jsonl.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict) or rec.get("type") != "assistant":
                continue
            msg = rec.get("message") or {}
            model = msg.get("model")
            usage = msg.get("usage")
            if not model or not isinstance(usage, dict):
                continue
            mu = by_model.get(model)
            if mu is None:
                mu = by_model[model] = ModelUsage(model=model)
            mu.add(usage)
            _bump(efforts, rec.get("effort"))  # #31 R3: per-gate actual effort
        if by_model:  # skip files with no usable assistant turns
            out.append(SubagentUsage(
                agent_label=_agent_label_from_meta(jsonl),
                session_file=str(jsonl), by_model=by_model, efforts=efforts))
    return out


def _iter_assistant_timestamps(path: Path):
    """Yield tz-aware timestamps of assistant turns in a file (best-effort)."""
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and rec.get("type") == "assistant":
                    ts = parse_ts(str(rec.get("timestamp") or ""))
                    if ts is not None:
                        yield ts
    except OSError:
        return
