# Architecture — how `/implement-feature` works inside

Reference for the moving parts. Orientation (repo layout, one run end to end) is in
[`jumpstart.md`](jumpstart.md). Why each part is shaped this way is in [`adr/`](adr/README.md).
[`SKILL.md`](../sdlc-lite-plugin/skills/implement-feature/SKILL.md) is authoritative for gate
behavior; this file is the map.

---

## 1. Four parts, no orchestration code

| Part | File(s) | Job |
|---|---|---|
| Skill | `skills/implement-feature/SKILL.md` | the ordered script of gates, loops, stop conditions |
| Agent defs | `agents/*.md` | pin each isolated gate's model, effort, tools |
| Guard hook | `hooks/hooks.json` → `hooks/scripts/guard.py` + `policy.py` | enforce isolation on every tool call |
| Analyzer | `analyzer/` + `agentdefs.py` | measure what actually happened, after the run |

- The agent is the runtime: it reads `SKILL.md` and executes it.
- Code may **enforce** or **measure**, never orchestrate (ADR-5).

---

## 2. Conductor + isolated gates

| Role | What it is | Runs |
|---|---|---|
| **[C] conductor** | the interactive session running the skill; talks to the human | human-facing gates |
| **[I] isolated subagent** | fresh context, pinned model/effort, file-only inbox | bias-sensitive gates |

- Spawn by the **plugin-namespaced** type: `sdlc-lite:test-writer`, never `test-writer`.
- Isolation fixes **anchoring** (fresh context per critic). Model pins fix **monoculture** (reviews
  on a stronger model).

### The twelve gates

| # | Gate | Runs as | Model / effort | Approver |
|---|---|---|---|---|
| 0 | CLASSIFY + model plan + preflight | [C] | session | human |
| 1 | INTERVIEW | [C] | session (wants Opus) | human |
| 2 | DESIGN / SPEC | [C] | session (wants Opus) | human |
| 3 | WRITE-TESTS | [I] `test-writer` | `sonnet` / medium | machine (suite red) |
| 4 | TEST-REVIEW | [I] `test-reviewer` | `claude-opus-4-8` / medium | machine (verdict) |
| 5 | IMPLEMENT | [I] `implementer` | `sonnet` / medium | machine (green) |
| 6 | VERIFY | [I] `verifier` | `sonnet` / medium | machine (observed pass) |
| 7 | CODE-REVIEW | [I] `code-reviewer` | `claude-opus-4-8` / medium | machine (verdict) |
| 8 | REVIEW-GUIDE | [C] | session (Sonnet/Haiku ok) | — |
| 9 | HUMAN REVIEW | [C] | session | **human (ship)** |
| 10 | COMMIT | [C] | session (Sonnet/Haiku ok) | — |
| 11 | REPORT | [C] | session | — |

- **Loops:** TEST-REVIEW ↔ WRITE-TESTS; VERIFY / CODE-REVIEW ↔ IMPLEMENT.
- Every loop is **bounded**: no progress after N rounds → stop and ask the human.
- CODE-REVIEW tags each finding `→IMPLEMENT` (code defect) or `→TESTS` (weak test).

---

## 3. Handoff: files, not transcripts

### Two trees (ADR-4)

| Tree | Where | Isolation |
|---|---|---|
| Product | repo's own `<code_root>` / `<tests_root>` (confirmed at Gate 0) | git branch |
| Process | `.implement-feature/<run>/` (gitignored) | one dir per run |

```
.implement-feature/
  .active-run                    # pointer + single-run lock (Gate 0 → Gate 10)
  <NN-slug-YYYYMMDDHHMM>/
    handoff/
      draft/                     # unapproved drafts (ADR-8); no subagent may read
      01-requirements.md … 08-code-review-findings.md
      run-log.jsonl              # audit log: guard (per tool call) + conductor (per gate)
    run-report.md                # Gate 11
```

- Files are numbered in reading order; a loop overwrites its file, so numbers stay stable.

### Inbox / outbox per isolated gate

| Gate | Reads | Writes |
|---|---|---|
| WRITE-TESTS | `01` + `02-design-interface` + `04-test-plan` — **never `03-design-internal`** | tests + `05-test-intent` |
| TEST-REVIEW | `01` + full design + tests + `05` | `06-test-review-findings` |
| IMPLEMENT | `01` + tests + full design | `<code_root>/…` |
| VERIFY | `01` (ACs + boundary inventory) + `<code_root>/` | `07-verify-report` |
| CODE-REVIEW | `01` + full design + whole diff | `08-code-review-findings` |

- Blind the producer, inform the critic (ADR-3).

---

## 4. Model & effort pins

Each isolated gate's frontmatter in `agents/<role>.md` pins its identity; the spawn brief passes
per-run paths.

```yaml
---
name: code-reviewer
model: claude-opus-4-8        # dated pin (ADR-2)
effort: medium
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
---
```

| Setting | Where it can be set | Notes |
|---|---|---|
| Model | inline at spawn → frontmatter → `CLAUDE_CODE_SUBAGENT_MODEL` → session → account | highest wins; inline takes aliases only |
| Effort | frontmatter **only** | unset → inherits the parent's |
| Tools | frontmatter allow/deny | hard, per call — but do not confine reads (ADR-1) |
| Conductor model | nowhere (plugin can't pin it) | Gate 0 warns if below design-grade |

- **Invariant:** design and every review run on a higher model than implementation.
- Reviewers pin dated `claude-opus-4-8`; producers pin `sonnet` (ADR-2). Effort is `medium`
  everywhere (#28, #35).
- Gates are dispatched **bare** (no inline `model`) so the pin holds; the receipt verifies it
  (ADR-12).

---

## 5. Guard hook — enforcement

- `hooks.json` registers `guard.py` as **PreToolUse** for the conductor **and every subagent**.
- Matched tools: `Read`, `Bash`, `Grep`, `Glob`, `Edit`, `Write`, `NotebookEdit`, `Task`, `Agent`,
  `Skill`.
- Keys on `agent_type` (namespaced) and `agent_id` from stdin. Rules live in
  [`policy.py`](../sdlc-lite-plugin/policy.py).
- Deny = `deny` decision + exit code 2. Each rule is also stated in the agent's brief
  (defense-in-depth).

| # | Rule | Applies to | Denies |
|---|---|---|---|
| 1 | Audit | all | nothing — appends `{ts, agent_type, agent_id, tool, target}` (UTC) to the run-log |
| 2 | Secrets | all | `.env`, keys, credentials, `~/.ssh/` — path-component match, tool-split (ADR-10) |
| 3 | Algorithm-blind | test-writer | reading `03-design-internal.md` (Read **and** Bash) |
| 4 | Draft-confinement | every subagent | reading under `handoff/draft/` |
| 5 | Test-integrity | implementer | editing or writing any test file |
| 6 | Write-confinement | test-reviewer, verifier, code-reviewer | writes outside their outbox + scratch dir |
| 7 | Explicit-entry | all | any `Skill` call to this plugin's skills (ADR-14) |

**How the hook finds the run.** A hook doesn't inherit the conductor's env.
- It reads `.implement-feature/.active-run` to find the run-log.
- Before Gate 0 writes it / after Gate 11 removes it → falls back to `if-runlog.jsonl` at the repo
  root (gitignored at Gate 0).

**Why a plugin hook.** A project `.claude/settings.json` hook did not fire in headless (`claude -p`)
runs; the plugin hook does (ADR-1).

**Bash is best-effort (#30).**
- Precise for single-target tools (`Read`, `Write`, `Glob`, `Grep`).
- For Bash it resolves `>`/`>>`/`tee`, `sed -i`/`cp`/`mv`, and bans algorithm-blind wildcard reads
  over `handoff/`.
- Indirect reads (`python -c …`, `xargs`, `cd handoff && cat *`) can slip through → the analyzer's
  auditor catches the *effect* (ADR-11).

---

## 6. Analyzer — measurement

Deterministic Python over a finished run. Never calls a model or drives a gate (ADR-5).

**It proves two promises per run:**
1. Every gate was **isolated** (read only its curated files).
2. Every gate ran at its **pinned model/effort**.

**It is not a cost cap.** Model/effort can't be enforced at dispatch (ADR-12) and Bash prevention is
best-effort (ADR-11). It is a record, with an **untrusted** mark on any violation.

| Module | Status | Job |
|---|---|---|
| `runlog.py` | load-bearing | run-log → per-agent activity + intent verdicts (blocked attempts). Imports `policy.py`; no transcript dependency |
| `auditor.py` | authoritative | fingerprints protected files; scans subagent tool *output*. Hit → `THIS RUN IS UNTRUSTED`, receipt `❌ LEAK` |
| `transcript.py` | best-effort | per-model tokens, main + `subagents/*.jsonl`. Fails as **absent** (soft note) or **drifted** (loud alarm) |
| `receipt.py` | headline | one row per agent: pin ([`agentdefs.py`](../sdlc-lite-plugin/agentdefs.py)) vs actual. Model mismatch = FAIL, effort = WARN |
| `report.py`, `_util.py` | — | Markdown rendering; tolerant UTC parsing |

- No transcript → auditor reports **UNKNOWN**, never PASS.
- Alias pin (`sonnet`) accepts any same-family id; dated pin demands an exact id.
- Run-log and transcript share no code; they join on the run-log's `[min ts, max ts]` window ±5 min.

**When it runs**

| When | Pass |
|---|---|
| Just before Gate 9 | fast, `--no-transcript` (intent only) — human sees breaches before shipping |
| Gate 11 | full, including the auditor |
| Any time | `/sdlc-lite:analyze-run` on a past run |

**More:** verdicts, CLI, failure handling → [`analyzer/README.md`](../sdlc-lite-plugin/analyzer/README.md).
Transcript shapes → [`TRANSCRIPT-FORMAT.md`](../sdlc-lite-plugin/analyzer/TRANSCRIPT-FORMAT.md).
Which field proves which claim → [`audit-observability-findings.md`](findings/audit-observability-findings.md).
