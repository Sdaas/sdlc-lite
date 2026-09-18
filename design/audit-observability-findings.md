# Finding: the session transcript + `.meta.json` make model **and effort** per-turn auditable

**Date:** 2026-09-12 · **Branch:** `main` · **Status:** ✅ VERIFIED against a real run

Feeds the **post-run audit phase** (Gate 11 analyzer) and its two capabilities —
isolation (#30) and model/effort integrity (#22). Companion to
[`model-pinning-findings.md`](./model-pinning-findings.md), which established that the
resolved `message.model` is ground truth; this doc adds **effort** and the launch-time
`.meta.json`, and maps every audit claim to the field that proves it.

---

## 1. Conclusion (settled)

The plugin can **prove, per turn, both the actual model and the actual effort** each
agent (conductor and every isolated subagent) ran at — not a proxy, not an inference.
An earlier working assumption that "effort is not observable" was **wrong**; effort is
stamped on every assistant record. Combined with the launch-time `.meta.json`, this gives
the audit two independent records:

- **intent / request** — what was asked for (`.meta.json` + the agent-def frontmatter), and
- **effect / actual** — what actually ran (the transcript's per-turn `model` + `effort`).

Deviation detection (requested vs actual) is therefore fully supported for model **and**
effort. The value proposition of `/implement-feature` — (a) each gate is isolated and (b)
each gate runs at a pinned model/effort so cost stays bounded — is **runtime-verifiable**,
not merely claimed.

## 2. Ground-truth evidence (a real run on this repo)

Sample: `~/.claude/projects/-Users-sdaas-dev-sdlc-lite/4667b56e-…` (conductor transcript +
one subagent under `…/4667b56e-…/subagents/agent-ad150d6e7fc9df44b.jsonl`).

### 2a. Launch-time request — the sibling `.meta.json`

Claude Code writes one `<agent>.meta.json` next to each subagent transcript. Observed schema:

```json
{
  "agentType": "general-purpose",
  "description": "Audit Phase 5 completeness",
  "toolUseId": "toolu_01TA6spFqhMRzUjYEsPn6gpA",
  "spawnDepth": 1,
  "model": "opus"
}
```

- `model` here is the **requested alias** (`"opus"`), *not* the resolved id.
- **There is no `effort` field in `.meta.json`.** Requested effort is only knowable from the
  agent-def frontmatter (static config), not the meta. (This is the observability half of #28.)
- `agentType` is how the analyzer attributes a subagent transcript to a gate today.

### 2b. Runtime actual — the transcript assistant records

Every `type:"assistant"` record — in the conductor transcript **and** each subagent
transcript — carries, at the **top level** (siblings of `message`, not inside it):

| Field | Example (conductor) | Example (subagent) | Meaning |
|---|---|---|---|
| `effort` | `"medium"` (×92) | `"medium"` (×35) | **actual effort the turn ran at** |
| `message.model` | `claude-sonnet-5` | `claude-opus-5` | **actual resolved model** |
| `message.usage` | tokens block | tokens block | input/output/cache/thinking tokens |
| `isSidechain` | `false` | `true` | subagent vs main-thread |
| `agentId` / `attributionAgent` | — | set | which agent produced the turn |

Confirmed placement: `effort` appears **only on assistant records** (not `user`/`attachment`),
once per turn, matching the assistant-turn count exactly (35/35 subagent, 92/92 conductor).
`message.model` is the resolved id (`claude-opus-5`), distinct from the meta's `"opus"` alias.

## 3. The proof model — what proves what, from where

| Claim | Requested (intent) | Actual (effect) | Deviation policy |
|---|---|---|---|
| **Model** | agent-def frontmatter · `.meta.json.model` (alias) | transcript `message.model` (resolved) | enforce at launch (#22); **FAIL** on mismatch |
| **Effort** | agent-def frontmatter (meta has none) | transcript top-level `effort` | **report-only** (effort is the cost knob, never trust-voiding): **any deviation from the pin — either direction, a downgrade *or* an upgrade — is a WARN** (#31) |
| **File content that entered an agent's context** | run-log (guard, intent) | transcript (effect) | corroborate; **UNKNOWN** (never PASS) if the transcript is blind |
| **Command granted / denied** | run-log `guard_decision` (**only** source) | — (a denied call has no effect) | log the guard's own decision |
| **Tokens** | — | transcript `message.usage` | observability only |

## 4. How the audit leverages this

- **Attribution.** Key each subagent transcript to a gate via `.meta.json.agentType`; fall
  back to the file stem. (Already done in `analyzer/transcript.py`.)
- **Model integrity (#22).** Compare the agent-def pin / `.meta.json.model` (request) against
  every turn's `message.model` (actual). Mismatch ⇒ FAIL. `message.model` is ground truth —
  never the conductor's self-report (see `model-pinning-findings.md`).
- **Effort integrity (#22/#28).** Compare the agent-def pinned effort against every turn's
  top-level `effort`. Mismatch ⇒ report. `analyzer/transcript.py` does **not** read the
  top-level `effort` today — that is a required new extraction.
- **File-content access (#30).** The transcript is the authoritative *effect* record of what
  content an agent actually saw; the run-log is the *intent* record. Note "content that
  entered context" excludes side-effect file opens (e.g. `pytest tests/` returns results, not
  test source) — those are not audit-relevant reads.
- **Grant/deny (new).** The guard currently writes its audit line *before* the deny check with
  no decision field, so granted and denied calls are indistinguishable in the run-log. Add a
  `guard_decision: allow|deny` field (the guard can only report *its own* decision, fired
  pre-execution — not the platform's final verdict or the command's exit status).

## 5. Caveats / fragility

- The transcript format is **officially unstable** and is treated as a quarantined satellite
  (`analyzer/transcript.py`). Model **and** effort proof both ride on it, so a format change
  blinds both at once. Contract: degrade to **UNKNOWN**, never a silent PASS.
- `.meta.json`'s schema is likewise not guaranteed; treat missing keys as best-effort.
- The sample `.meta.json` above was a `general-purpose` agent, but the schema (`model`, no
  `effort`) and the transcript's per-turn `effort` / `message.model` are **harness-level**,
  so they apply identically to the `implement-feature:*` gates.
