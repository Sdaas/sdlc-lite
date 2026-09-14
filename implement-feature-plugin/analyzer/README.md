# Observability analyzer

A **deterministic, after-the-fact** reporter for an `/implement-feature` run —
**measurement, never orchestration** (see the Developer Guide → ADR-5 /
"measurement, not orchestration"). It reads the two
pieces of evidence a finished run leaves behind and prints a Markdown report. It
never calls a model, makes a decision, or drives a gate.

## Run it

```bash
# from implement-feature-plugin/ — primary handle is the run's artifact dir:
python -m analyzer.analyze_run --workdir /path/to/.implement-feature/<run>/

# options
--workdir DIR        # the run's artifact dir; run-log = <workdir>/handoff/run-log.jsonl
--runlog PATH        # explicit run-log path (overrides --workdir)
--projects-dir DIR   # Claude Code projects dir (default: ~/.claude/projects)
--slug SLUG          # project subdir under projects-dir (default: derived from cwd)
--no-transcript      # skip the best-effort token/cost analysis
```

The run-log is resolved as: `--runlog` if given, else `<workdir>/handoff/run-log.jsonl`
from `--workdir`, else `$IF_RUNLOG` / `$CLAUDE_PROJECT_DIR/if-runlog.jsonl` / `./if-runlog.jsonl`.
The analyzer **never reads `.active-run`** — knowing the *active* run is a higher-layer
concern (that pointer is the conductor↔guard channel, not the analyzer's).

## Architecture — two independent readers

```
analyze_run.py            entry point; orchestrates + QUARANTINES the satellite
├── runlog.py             LOAD-BEARING. Parses if-runlog.jsonl only.
│                         Per-agent activity + the 4 isolation verdicts.
│                         Zero knowledge of the transcript; cannot be broken by it.
├── transcript.py         BEST-EFFORT satellite. Parses the Claude Code session
│                         transcript for per-model tokens (main thread + each
│                         subagent under <uuid>/subagents/*.jsonl, attributed via
│                         .meta.json). Format is officially unstable -> quarantined.
├── report.py             Pure Markdown rendering (no I/O, no exception handling).
└── _util.py              Leaf helpers (tolerant timestamp parsing). Shared, but
                          does NOT couple the two readers to each other.
```

### Failure handling (fail loud, not silent)
The run-log section is **always** rendered. The transcript section is attempted
inside `try/except` and degrades two ways:

- **absent** (no transcript overlaps the run window) → soft "skipped" note.
- **drift** (a transcript was found but the fields we depend on are gone) → a
  **loud** "format changed, update `analyzer/transcript.py`" alarm. An *unknown*
  exception also routes here — silent degradation is worse than a loud alarm.

`transcript.py` runs a **schema self-check**: assistant turns present but none
carrying `message.model` / `message.usage` ⇒ deliberate `TranscriptFormatError`.

> **Working on `transcript.py`?** [`TRANSCRIPT-FORMAT.md`](TRANSCRIPT-FORMAT.md) is a field guide to
> the on-disk layout and record shapes (main transcript, `<uuid>/subagents/*.jsonl`, and the
> `.meta.json` sidecar), with real snippets and which field proves which claim — start there.

### Transcript↔run selection
The main transcript file is chosen by **time-window correlation** (option *b*):
the file whose assistant turns most overlap the run-log's `[min ts, max ts]`
window (padded ±5 min for skew). Robust to stray concurrent sessions. Requires the
run-log and transcript to share a clock — `guard.py` logs **UTC/tz-aware** on
purpose so it lines up with the transcript's `Z` stamps. The **per-subagent**
transcripts are then read from `<main_stem>/subagents/*.jsonl` beside it (#15) —
extra-best-effort: a missing/malformed subagents dir yields an empty breakdown and
never even marks the main section as drift.

## The isolation verdicts (from the run-log alone)
1. test-writer never *attempted* to read `design-internal.md`
2. implementer never *attempted* to write/edit a test file
3. no agent *attempted* to read secrets/`.env` (tool-aware, mirrors `guard.py`)
4. test-reviewer never *attempted* to write into the product tree (#12)
5. distinct expected subagents actually ran

> The audit records **attempts**, not outcomes: `guard.py` logs every call
> (job #1) *before* it may deny it. A forbidden entry here means an agent *tried*;
> the guard blocks it at runtime. Preventive (guard) + detective (analyzer)
> together. The secret / test-path / reviewer-write predicates here **mirror
> `guard.py`** and must be kept in sync.

## Known minor semantics
`Bash` counts as a "read-ish" tool, so a Bash command target is included in an
agent's "files read" count (the per-tool breakdown column disambiguates). Secret
detection is **tool-split** (#16): a Bash target is the whole command, so it is
tokenized and only path-like secret tokens are flagged — never a raw substring of
the command body (which used to false-flag `os.environ`).

## Tests
`python -m pytest analyzer/tests -q` — synthetic run-logs + transcripts,
including both degradation modes. Run inside the dev container (pinned toolchain).
