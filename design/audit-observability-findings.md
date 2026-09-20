# Finding: the session transcript + `.meta.json` make model **and effort** per-turn auditable

**Date:** 2026-09-12 · **Status:** ✅ VERIFIED against a real run

Feeds the post-run audit phase (Gate 11 analyzer). Companion to
[`model-pinning-findings.md`](./model-pinning-findings.md), which established that
`message.model` is ground truth for model; this doc adds effort and `.meta.json`.

## Conclusion

The plugin can prove, per turn, both the actual model and the actual effort each agent
(conductor and every isolated subagent) ran at — not a proxy, not an inference. The audit has two
independent records: **intent** (what was requested — agent-def frontmatter + launch-time
`.meta.json`) and **effect** (what actually ran — the transcript's per-turn `model` + `effort`).
Deviation detection (requested vs actual) is fully supported for both.

## Evidence

- `<agent>.meta.json`, written per subagent, carries the **requested** model as a family alias
  (e.g. `"model": "opus"`) — never a resolved ID, and **no `effort` field at all** (requested
  effort is only knowable from agent-def frontmatter).
- Every `type:"assistant"` transcript record (conductor and every subagent) carries, at top level:
  `effort` (actual effort the turn ran at), `message.model` (actual resolved model ID, distinct
  from the meta's alias), `message.usage` (token counts), `isSidechain` (subagent vs main-thread).
  Confirmed present on 100% of assistant turns (35/35 subagent, 92/92 conductor in the sampled
  run), absent from `user`/`attachment` records.

| Claim | Requested (intent) | Actual (effect) | Deviation policy |
|---|---|---|---|
| Model | agent-def frontmatter / `.meta.json.model` (alias) | transcript `message.model` (resolved) | enforce at launch; FAIL on mismatch |
| Effort | agent-def frontmatter (meta has none) | transcript top-level `effort` | report-only; any deviation, either direction, is a WARN |
| File content that entered context | run-log (intent) | transcript (effect) | corroborate; UNKNOWN (never PASS) if transcript is blind |
| Command granted/denied | run-log `guard_decision` (only source) | — | log the guard's own decision |

## How the audit uses this

- **Attribution:** key each subagent transcript to a gate via `.meta.json.agentType`
  (`analyzer/transcript.py`).
- **Model integrity:** compare the agent-def pin / `.meta.json.model` against every turn's
  `message.model`; mismatch ⇒ FAIL. `message.model` is ground truth, never the conductor's
  self-report.
- **Effort integrity:** compare the agent-def pinned effort against every turn's top-level
  `effort`; mismatch ⇒ WARN.
- **File-content access:** the transcript is the authoritative *effect* record of what content an
  agent actually saw. Side-effect file opens (e.g. `pytest tests/` returning results, not source)
  are not audit-relevant reads.

## Caveats

- The transcript format is officially unstable and is treated as a quarantined satellite
  (`analyzer/transcript.py`); a format change should degrade to UNKNOWN, never a silent PASS.
- `.meta.json`'s schema is likewise not guaranteed — treat missing keys as best-effort.
