# Developer Guide — architecture, decisions, and how to work on the plugin

This guide is for someone improving `implement-feature`. It explains the architecture, the two pieces
of real code (the guard hook and the analyzer), the design decisions and *why* they were made (ADRs),
the design principles distilled from building it, and the testing methodology. If you only want to
*run* the plugin, read the [README](../README.md); for the underlying concepts start with the
[Tutorial](tutorial.md). For **versioning, issue triage, and how a release is cut and consumed**, see
[`RELEASING.md`](RELEASING.md).

---

## 0. Recommended reading order

A new developer should read the sections below in this order rather than top-to-bottom on a first
pass:

1. **§1 The core idea** — the declarative-workflow premise everything else assumes.
2. **§2 Architecture** — the conductor/isolated-subagent split and the handoff contract.
3. **§6 ADRs** — *why* the architecture landed where it did; skip this on a skim, but read it before
   proposing a structural change.
4. **§4 The guard hook** — the enforcement mechanism behind the isolation guarantees.
5. **§3 Model & effort pinning** — how gates get their model/effort, and where that's declared.
6. **§5 The analyzer** — how a run is measured after the fact.
7. **§7 Design principles** and **§8 Testing & dry-run methodology** — read once you're ready to make
   a change and need to know how it'll be validated.
8. **§9 When you edit the product** — the checklist to follow while actually making the change.

---

## 1. The core idea: a declarative workflow, no orchestration code

The whole product is expressed **declaratively**. There is no hand-written driver that calls "phase 1,
phase 2." Instead:

- a **skill** (`skills/implement-feature/SKILL.md`) is the conductor's *score* — an ordered English
  script of gates, loops, and stop conditions;
- **agent-definition files** (`agents/*.md`) pin each isolated gate's model, effort, and tools;
- a **hook** (`hooks/hooks.json` → `hooks/scripts/guard.py`) enforces isolation at the tool-call level;
- an **analyzer** (`analyzer/`) measures, after the fact, what actually happened.

The agent is the runtime: it reads the score and executes it conversationally. **The behavior lives in
Markdown.** The only real code is `guard.py` (enforcement) and `analyzer/` (measurement) — both
permitted precisely because they *enforce or measure*, never *orchestrate* (see the ADR on
observability). Editing the workflow means editing Markdown, not writing code.

### Repository layout of the product

```
sdlc-lite-plugin/
├── .claude-plugin/plugin.json          # identity metadata
├── commands/
│   └── analyze-run.md                  # standalone re-analysis command
│                                       # (NO implement-feature.md — it would shadow the
│                                       #  skill below; see ADR-14)
├── skills/implement-feature/
│   ├── SKILL.md                        # the conductor's score (all gates) AND the
│   │                                   # /implement-feature entry point itself
│   └── references/
│       ├── quality-standards.md        # single source of truth for "green" + thresholds
│       ├── requirements-template.md
│       ├── design-interface-template.md
│       ├── design-internal-template.md
│       └── test-plan-template.md
├── agents/                             # one file per isolated gate; pins model/effort/tools
│   ├── test-writer.md  test-reviewer.md  implementer.md  verifier.md  code-reviewer.md
├── hooks/
│   ├── hooks.json                      # registers the PreToolUse guard
│   ├── scripts/guard.py                # the enforcement code
│   └── tests/test_guard.py
├── analyzer/                           # deterministic after-the-fact reporter
│   ├── analyze_run.py runlog.py transcript.py report.py _util.py
│   └── tests/
└── toolchain/requirements-dev.txt      # pinned dev tools
```

---

## 2. Architecture: conductor + isolated gates

The system is a **conductor [C]** plus **isolated subagents [I]**.

- **Conductor [C]** — the interactive session running the skill. It holds the through-line, talks to
  the human, and walks the gates in order. Human-facing gates (interview, design, review) run here.
- **Isolated subagents [I]** — bias-sensitive gates run as *separate* agents: fresh context, a pinned
  model/effort, and a curated file-only inbox. They are spawned via the Agent tool using the
  **plugin-namespaced** `subagent_type` — `sdlc-lite:test-writer`, never the bare name.

**Why isolate?** "Bias" is two distinct problems:

1. **Anchoring** — a reviewer who watched the code get written shares the author's blind spots. Fixed
   by giving each critic a **fresh context**.
2. **Model monoculture** — one model's blind spot recurs at every gate. Fixed by **model diversity**:
   reviews run on a stronger model than implementation.

The human is the **continuity thread** integrating independent specialists.

### The two trees: product vs process

The workflow keeps two things strictly apart:

- **Product** — the source and tests that ship. They live in the repo's own layout (`<code_root>`,
  `<tests_root>`), detected and confirmed at Gate 0. Feature-to-feature isolation is a **git branch**
  concern, not a filesystem one — code is written in place.
- **Process artifacts** — the handoff files and audit logs. They live in a per-run, **gitignored**
  directory, never mixed with shippable code:

```
.implement-feature/                       # gitignored artifact root
  .active-run                             # pointer + single-run lock (Gate 0 → Gate 10)
  <NN-slug-YYYYMMDDHHMM>/                 # one dir per run
    handoff/
      draft/                              # unapproved drafts; never read by a subagent
      01-requirements.md … 08-code-review-findings.md
      run-log.jsonl                       # conductor's per-gate orchestration log
    run-report.md                         # written by Gate 11
```

### The handoff contract

Every gate reads a **curated inbox** and writes a **defined outbox**, both as files — a gate **never**
sees a prior gate's raw transcript. Handoff files are numbered by human read-order (browse `handoff/`
top-to-bottom to replay the run); numbers are stable under loops (a re-review overwrites its file).

| Gate | Reads (inbox) | Writes (outbox) |
|---|---|---|
| WRITE-TESTS [I] | `01-requirements` + `02-design-interface` + `04-test-plan` (**never** `03-design-internal`) | tests + `05-test-intent` |
| TEST-REVIEW [I] | `01` + full design + tests + `05-test-intent` | `06-test-review-findings` |
| IMPLEMENT [I] | `01-requirements` + tests + full design | `<code_root>/…` |
| VERIFY [I] | `01-requirements` (ACs + boundary inventory) + `<code_root>/` | `07-verify-report` |
| CODE-REVIEW [I] | `01` + full design + whole diff | `08-code-review-findings` |

The **interface/internal design split** is the mechanism that keeps the test-writer algorithm-blind:
it is handed `02-design-interface.md` (the public contract) but **never** `03-design-internal.md` (the
algorithm). The critic gates *do* see the internal design — asymmetric inboxes, blind the producer,
inform the critic.

### The twelve gates

| # | Gate | Runs as | Model / effort | Approver |
|---|---|---|---|---|
| 0 | CLASSIFY + model plan + preflight | [C] | session | human |
| 1 | INTERVIEW | [C] | session (wants Opus) | human |
| 2 | DESIGN / SPEC | [C] | session (wants Opus) | human |
| 3 | WRITE-TESTS | [I] `test-writer` | `sonnet` / medium | machine (suite red) |
| 4 | TEST-REVIEW | [I] `test-reviewer` | `claude-opus-4-8` (pinned) / medium | machine (verdict) |
| 5 | IMPLEMENT | [I] `implementer` | `sonnet` / medium | machine (green) |
| 6 | VERIFY | [I] `verifier` | `sonnet` / medium | machine (observed pass) |
| 7 | CODE-REVIEW | [I] `code-reviewer` | `claude-opus-4-8` (pinned) / medium | machine (verdict) |
| 8 | REVIEW-GUIDE | [C] | session (Sonnet/Haiku ok) | — |
| 9 | HUMAN REVIEW | [C] | session | **human (ship)** |
| 10 | COMMIT | [C] | session (Sonnet/Haiku ok) | — |
| 11 | REPORT | [C] | session | — |

Human gates bookend (0–2, 9); machine-condition gates run the middle (3–7) unattended. The loops —
TEST-REVIEW ↔ WRITE-TESTS, and VERIFY/CODE-REVIEW ↔ IMPLEMENT — are all **bounded**: after N rounds
with no progress they STOP and surface to the human. CODE-REVIEW tags each finding with a repair
target (`→IMPLEMENT` for code defects, `→TESTS` for weak tests) because the two repair paths route to
different gates.

The authoritative, prose-level description of every gate is `SKILL.md` itself. This section is the map;
`SKILL.md` is the territory.

---

## 3. Model & effort pinning (agent-definition files)

Each isolated gate is a named agent type defined in `agents/<role>.md`. Its YAML frontmatter pins the
role's static identity; the spawn brief passes the per-run specifics (paths, inbox).

```yaml
---
name: code-reviewer
model: claude-opus-4-8       # dated pin — see the model-pinning ADR
effort: medium
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit  # read-only critic
---
```

Key facts (all empirically verified — see the ADRs and §7):

- **Model** can be set in frontmatter *or* overridden inline at spawn. Resolution is highest-wins:
  per-invocation param → frontmatter `model:` → `CLAUDE_CODE_SUBAGENT_MODEL` env → session → account.
- **Effort** can be set **only** in frontmatter — there is no spawn-time override. If unset, the
  subagent inherits the parent's effort.
- **Tools** allow/deny are hard restrictions enforced at the tool-call level.
- The **conductor's own model cannot be pinned** by a plugin — it runs on whatever the session was
  launched with. Gate 0 therefore self-checks and warns if the conductor is below design-grade.

The invariant these pins enforce: **design and every review use a higher model than
implementation.** The two reviewers pin the *dated* `claude-opus-4-8` for reproducibility; the
producer gates (`test-writer`, `implementer`, `verifier`) pin the floating `sonnet` alias. Effort is
uniform (`medium`) across every gate — a deliberate dev-only spread (`test-reviewer` `low`,
`code-reviewer` `high`) proved the receipt's effort audit end-to-end before release; real-world
config differentiates on model, not effort (#28, #35).

**The pins are the SSOT for the receipt (#22).** [`agentdefs.py`](../sdlc-lite-plugin/agentdefs.py)
reads this frontmatter and hands the model/effort pins to the analyzer's receipt — the same
seam-not-two-copies discipline `policy.py` gives the isolation rules. **Pinned gates are dispatched
bare** (no inline `model`) so the frontmatter pin — including the *dated* reviewer pin — is honored;
the receipt then **verifies** the actual resolved model against the pin (a mismatch is a FAIL). #22
originally also *enforced* the model at dispatch (deny a dispatch that names no model), on the premise
that a frontmatter pin is silently droppable; **that premise is false** — a bare-dispatch frontmatter
pin is honored — and the deny-if-unnamed hook broke the *dated* reviewer pins by forcing an alias-only
inline model that overrode them, so #36 reverted it. See the ADR-12 correction and
[#36](https://github.com/Sdaas/sdlc-lite/issues/36). **Effort** has no rank-1 lever (frontmatter only,
verified above), so it is audit-only: the receipt WARNs on any deviation, either direction.

---

## 4. The guard hook — isolation is enforced, not requested

`hooks/hooks.json` registers a **PreToolUse** hook (`hooks/scripts/guard.py`) that fires for the
conductor **and every subagent**, on every
`Read`/`Bash`/`Grep`/`Glob`/`Edit`/`Write`/`NotebookEdit`. It keys on the `agent_type` (namespaced,
e.g. `sdlc-lite:test-writer`) and `agent_id` carried on stdin. Five jobs:

1. **Audit** — appends `{ts, agent_type, agent_id, tool, target}` per tool call — a tamper-evident,
   per-agent record of exactly what each agent read. Timestamps are logged **UTC/tz-aware** so they
   line up with the transcript's `Z` stamps (the analyzer correlates by time window).
2. **Secrets guardrail** — denies reading `.env` / keys / credentials / `~/.ssh/` for **any** agent.
   Matching is **path-component-aware and tool-split** (see the secrets ADR) so a benign Bash command
   containing `os.environ` isn't false-denied.
3. **Algorithm-blind** — denies the **test-writer** reading `03-design-internal.md`, Read *and* Bash.
4. **Draft-confinement** — denies **any subagent** reading under `handoff/draft/`.
5. **Test-integrity** — denies the **implementer** editing/writing any test file; and confines the
   **test-reviewer**'s writes to its outbox + a scratch dir.

A `deny` decision + exit code 2 hard-blocks the call. Each rule is **defense-in-depth** with the
agents' own role instructions (the agent usually declines on its own; the hook is the backstop).

**How per-run config reaches the hook:** a hook is a separate process and does *not* inherit env the
conductor exports. The conductor writes a fixed-path pointer, `.implement-feature/.active-run`,
containing the current run's artifact dir; the hook reads it to find the run-log. That same file
doubles as the **single-run lock**. When the pointer doesn't exist yet (pre-workdir Gate-0 preflight)
or no longer exists (post-commit Gate-11), the hook falls back to writing `if-runlog.jsonl` at the repo
root — which Gate 0 also gitignores.

**Why a *plugin* hook, not project settings:** a project `.claude/settings.json` PreToolUse hook did
**not** fire in headless (`claude -p`) runs; the plugin-shipped hook fires for the conductor and every
subagent. Reliability-critical config ships with the plugin.

Keep `guard.py` and the analyzer's isolation predicates in sync — they implement the same secret /
test-path / reviewer-write rules (preventive vs detective).

### Bash enforcement is best-effort — and the transcript auditor closes it (#30)

The guard is a **string-inspecting PreToolUse hook**, not an OS-level sandbox. For `Read`, `Write`,
`Glob`, and `Grep` the tool names a single, inspectable target, so the allow/deny rules are precise.
For **`Bash` the *real-time* enforcer is best-effort** — inherently, because you cannot know from a
shell string the full set of files a `python -c …`, an `xargs` pipeline, or a `cd handoff && cat *`
will actually touch. The design accepts this and closes it with a second, independent leg. Two things
changed from the earlier enforcer-only state:

- **One policy, two legs, no drift (the SSOT).** The per-agent allow/deny rules now live once in
  [`sdlc-lite-plugin/policy.py`](../sdlc-lite-plugin/policy.py) — shared predicates
  (`looks_secret`, `is_test_path`, the design-internal/draft tests, the Bash parsing) plus a
  data-driven rule table and a single `decide(agent_type, access, path)` authority. **Both** the
  in-hook enforcer (`guard.py`) and the detective analyzer (`runlog.py`) *import* it. Previously each
  kept its own copy under a "KEEP IN SYNC" comment, so a single Bash trick bypassed both at once —
  they shared one blind spot. They can no longer disagree.
- **The enforcer got wider, but is still not airtight.** It now resolves the in-place/copy write
  *forms* (`sed -i`, `cp`, `mv`) as well as `>`/`>>`/`tee` redirects, and it **bans** an
  algorithm-blind agent's wildcard read over `handoff/` (`cat handoff/*.md` could expand to
  `03-design-internal.md`). Write-confinement covers all three read-only critics (test-reviewer,
  verifier, code-reviewer). But an indirect read or a segment-hiding `cd` still slips the *real-time*
  check — by design, because the backstop is the auditor, not more parsing.

**The authoritative leg reads the *effect*, not the intent.** The analyzer's transcript auditor
([`analyzer/auditor.py`](../sdlc-lite-plugin/analyzer/auditor.py)) fingerprints each
content-protected artifact (e.g. `03-design-internal.md`) and scans each subagent transcript's **tool
output** for it. Because a leak lands in *some* string leaf of the transcript's `toolUseResult` (Read
→ `file.content`, Bash → `stdout`, Edit → `originalFile`) *however* it was read, this catches the
glob/indirect leak the command-string legs cannot see, and it is **method-agnostic**. A hit is
**trust-voiding**: the Gate-11 report prints `THIS RUN IS UNTRUSTED` and the receipt's *Files seen*
column shows `❌ LEAK`. *Which* artifact a role is forbidden is decided by `policy.decide()`, so the
auditor and the guard agree on "protected" by construction. (On-disk record shapes: see
[`analyzer/TRANSCRIPT-FORMAT.md`](../sdlc-lite-plugin/analyzer/TRANSCRIPT-FORMAT.md) §5.)

**Honesty over false comfort.** The content audit needs the session transcript (it reads tool output),
so when the transcript is absent/drifted the audit renders **UNKNOWN — not run**, never a silent PASS:
absence of the transcript is absence of proof, not proof of innocence. The bar for this plugin is
*best-effort prevention + authoritative detection*, not cryptographic airtightness — the guard is
still defense-in-depth (each agent's role body also tells it what it may touch), and the auditor turns
a Bash bypass from an invisible gap into a caught, trust-voiding finding. (#30 subsumed the earlier
ad-hoc findings #27 and #29.)

---

## 5. The analyzer — measurement, never orchestration

`analyzer/` is a deterministic Python reporter for a finished run. It reads the two pieces of evidence
a run leaves behind and prints a Markdown report. It **never** calls a model, makes a decision, or
drives a gate.

**Why it exists — the receipt for the two guarantees.** `/implement-feature` makes two promises:
**(a)** every gate is *isolated* — a subagent reads only the files curated for its role — and **(b)**
every gate runs at a *pinned model/effort* so cost stays bounded. The guard hook prevents isolation
violations in real time (best-effort for `Bash`); the **model/effort** pins are governed by the
honored frontmatter (bare dispatch, #22/#36) and **proven** by the analyzer — the **detective** half
that reads the transcript after the fact and turns both guarantees from claims into per-run, checkable
facts. Both
are runtime-verifiable from the session transcript: the resolved `message.model` and a per-turn
top-level `effort` field are ground truth (conductor and every subagent). The field-by-field proof
model — which transcript / `.meta.json` field substantiates which claim — is recorded in
[`findings/audit-observability-findings.md`](findings/audit-observability-findings.md); the audit
phase as a first-class feature is tracked in [issue #31](../../issues/31) (with #30 and #22 as its
isolation and model/effort-integrity capabilities).

**What the receipt is — and is not.** It is **observability plus best-effort prevention, not a hard
cost cap.** The guard prevents in real time where it can (isolation, best-effort for `Bash`), and the
receipt then *verifies* the model/effort/isolation from ground truth and marks the run **untrusted**
on any violation. It does **not** guarantee a run cannot exceed a token/dollar budget — neither model
nor effort has a dispatch-time enforcement lever (ADR-12), and Bash isolation is best-effort (ADR-11).
The model pin is honored by the *bare* dispatch and the model guarantee is what the receipt
**verifies** — not something the dispatch hook forces (#22 once tried; that leg rested on a false
premise and was reverted in [#36](https://github.com/Sdaas/sdlc-lite/issues/36)). The value
is a per-run, checkable record of exactly what the barriers and the reasoning budget actually did — the
thing a person deciding whether to trust a run's output needs — not a promise the platform can't keep.

For the concrete on-disk layout and record
shapes those fields live in — main transcript, `<uuid>/subagents/*.jsonl`, and the `.meta.json`
sidecar, with real snippets — see the field guide
[`sdlc-lite-plugin/analyzer/TRANSCRIPT-FORMAT.md`](../sdlc-lite-plugin/analyzer/TRANSCRIPT-FORMAT.md).

Two independent readers, with the fragile one quarantined behind a boundary:

- **`runlog.py`** — **load-bearing**. Parses `handoff/run-log.jsonl` (or the `if-runlog.jsonl`
  fallback) → per-agent activity + the *intent-level* isolation verdicts (attempts the guard recorded).
  Imports `policy.py` for its predicates (the same SSOT the guard enforces). Zero knowledge of the
  transcript; cannot be broken by it.
- **`auditor.py`** — the **authoritative isolation leg** (#30 R3). Fingerprints each content-protected
  artifact and scans each subagent transcript's *tool output* for it — catching the glob/indirect Bash
  leak the run-log's command-string view cannot see. A hit voids trust. Best-effort satellite (it needs
  the transcript), so no transcript → UNKNOWN, never a false PASS.
- **`transcript.py`** — **best-effort satellite**. Parses the Claude Code session transcript for
  per-model tokens (main thread + each subagent under `<uuid>/subagents/*.jsonl`, attributed via the
  sibling `.meta.json`). The transcript format is officially internal/unstable, so this reader is
  wrapped in `try/except` at a single boundary in `analyze_run.py` and degrades two clearly-different
  ways: **absent** (soft "skipped" note) vs **drift/broken** (loud "format changed, update the parser"
  alarm). A schema self-check deliberately raises the loud error if the depended-on fields vanish.
- **`receipt.py`** — the **headline**: one per-agent record attesting both guarantees. It fills the
  *requested* model/effort from the agent-def pins ([`agentdefs.py`](../sdlc-lite-plugin/agentdefs.py))
  and the *actual* from the transcript, then verdicts them — a model mismatch is trust-voiding (**FAIL**),
  an effort deviation is a **WARN** (the cost knob, not trust). The match is alias/dated-aware: an alias
  pin (`sonnet`) accepts any same-family resolved id; a dated pin (`claude-opus-4-8`) demands an exact id.
- **`report.py`** pure Markdown rendering; **`_util.py`** tolerant UTC timestamp parsing.

The two readers are correlated only by a **value** — the run-log's `[min ts, max ts]` window (padded
±5 min) selects the overlapping transcript file — not by shared code or imports.

Two kinds of verdict, by which evidence backs them. **Intent-level**, from the run-log alone
(`runlog.py`) — these record *attempts* the guard logged before it could deny them, so a forbidden
entry means an agent *tried* and the guard blocked it live:

1. test-writer never *attempted* to read `03-design-internal.md`;
2. implementer never *attempted* to write/edit a test file (incl. Bash `sed -i`/`cp`/`mv` forms);
3. no agent *attempted* to read secrets/`.env`;
4. the read-only critics (test-reviewer, verifier, code-reviewer) never *attempted* to write into the
   product tree (anchored to *this* run's handoff outbox, not a loose substring);
5. the distinct expected subagents actually ran.

**Effect-level / authoritative**, from the transcript (`auditor.py`): did any content a gate was
forbidden to see actually *reach* it? This is the only leg that catches a Bash glob/indirect leak, and
a finding is trust-voiding — the report prints `THIS RUN IS UNTRUSTED` and the receipt's *Files seen*
column flips to `❌ LEAK`.

The analyzer runs automatically at Gate 11 (full pass, incl. the transcript auditor), and its fast
intent-level pass runs again just before Gate 9 (`--no-transcript`, so a breach is surfaced for
explicit human acknowledgement before shipping). It can also be run on any past run via
`/sdlc-lite:analyze-run`. Full detail: `analyzer/README.md`.

---

## 6. Architecture decision records (ADRs)

Condensed rationale for the load-bearing decisions. The design-principles list (§7) is the fuller
catalog.

### ADR-1 — Isolation is enforced by a plugin PreToolUse hook

*Decision:* enforce read-confinement and secrets protection with a plugin-shipped PreToolUse hook keyed
on `agent_type`, rather than tool-removal or a working-directory fence alone.
*Why:* experiments (§7 sources) showed `disallowedTools: Write` does **not** confine reads, and a
critic that keeps `Bash` can write files via `cat >`/heredocs regardless of `disallowedTools` — so
"read-only" and "algorithm-blind" cannot be bought by tool-removal. A `blockReadsOutsideWorkingDirectories`
fence works but is all-or-nothing. The hook does audit + secrets + per-agent blindness in one place,
fires for subagents, and fires in headless (a project-settings hook did not). Defense-in-depth: the
role instruction stays in each agent's body as a backstop.

### ADR-2 — Reviewers pin a *dated* model; producers pin the floating alias

*Decision:* the two reviewer gates pin the explicit dated `claude-opus-4-8`; the producer gates pin the
`sonnet` alias.
*Why:* reproducible review behavior — a floating `opus` alias would silently change the reviewer as new
Opus tiers ship, so the same code could get a different review months apart. Producers ride the latest
Sonnet on purpose (implementation benefits from currency; it isn't the reproducibility-sensitive step).
*Evidence (verified from raw subagent transcripts, four dev-container runs):* after the pin landed,
both reviewer gates report `message.model = claude-opus-4-8` in every run (including the committed
Phase 4 async-fetcher run); the `sonnet` gates resolve to `claude-sonnet-5`. No fallback, no override
env var. Before the pin, the reviewers used the `opus` alias → `claude-opus-5`, which was also correct
*for that time*.
*Lesson worth keeping:* when auditing model usage from transcripts, always tie a session to its run by
grepping the feature identity / workdir slug / commit SHA in the *main* transcript first — a reused
project dir mixes sessions from multiple runs, and file mtime alone is not proof. (An earlier draft of
this finding wrongly concluded the pin was *not* honored, purely by misattributing a pre-pin session to
the post-pin run.)

### ADR-3 — The interface/internal design split makes the test-writer algorithm-blind

*Decision:* split the design into a public-contract `02-design-interface.md` (shared with the
test-writer) and an algorithm `03-design-internal.md` (withheld), enforced by the guard hook.
*Why:* if the algorithm leaks into the interface, the test-writer derives tests *from the algorithm* —
so a wrong implementation that shares those assumptions still passes. Splitting forces tests to encode
the **contract**, so they can fail a bad implementation. Rejected alternatives are recorded in the
internal design as an ADR the code-reviewer can check against.

### ADR-4 — Separate product from process by lifecycle

*Decision:* shipping code/tests live in the repo's own layout (branch = feature isolation); process
artifacts live in a per-run, gitignored `.implement-feature/<run>/`.
*Why:* fusing them (workdir == repo root) collides the moment a second feature exists, and risks
committing process artifacts. Config reaches the out-of-band guard hook via a **pointer file**, not env
(a hook doesn't inherit the conductor's env); the pointer doubles as a single-run lock.

### ADR-5 — Observability measures; it never orchestrates

*Decision:* the analyzer is deterministic Python that runs *after* a run and only *reads*; it is never
a summarizer subagent.
*Why:* (1) *trust* — "did the forbidden read happen?" is a grep-and-count fact; an LLM summarizer is
non-deterministic and can *hallucinate a compliance pass*. (2) *architecture* — an analyzer agent would
be a second AI acting inside the system, silently re-introducing a driver and breaking the "driverless"
claim. The rule: **code is allowed when it measures (analyzer) or enforces (guard), never when it
orchestrates.** A monitoring tool must also **fail loud** — route even unknown failures to a visible
alarm, because a silent hollow report is corrosive while a false-but-loud alarm is self-correcting.

### ADR-6 — A shipped workflow uses the ambient environment, never the author's

*Decision:* Gate 10 resolves `user.name`/`user.email` from ambient git config (no `--author`, no
`git config`); if none is set it STOPs and asks the human.
*Why:* the plugin ships to other users. Hardcoding the author would attribute a customer's commits to
the plugin's author. General rule: separate *meta-authorship* (who builds the tool) from *runtime
behavior* (what the tool does in someone else's environment) — the tool inherits the host's identity,
secrets, toolchain, and conventions.

### ADR-7 — Never commit on the default branch (non-overridable)

*Decision:* Gate 0 assesses triviality and recommends stay-vs-new-branch, but if HEAD is the default
branch a new `feature/<NN-slug>` branch is *required* regardless. Re-checked at Gate 10.
*Why:* a hard guardrail against clobbering `main`. The human may override the triviality call, never
this invariant.

### ADR-8 — Draft → review the real file → promote

*Decision:* human-approval gates author a **draft** the human reads (and may hand-edit), then
**promote** it to the approved handoff on approval; downstream gates read only the promoted file.
*Why:* the old "don't write before approval" rule protected the handoff contract but blinded the
reviewer to the real artifact. Splitting authoring from finalizing lets the human approve what they
actually saw (P47 — never ask a human to approve an artifact they haven't seen in full), while the
guard keeps drafts out of every subagent's reach.

### ADR-9 — Grilling reaches clarity, not maximal scope

*Decision:* Gate 1 first proposes a one-paragraph *minimal* version + an explicit out-of-scope list and
gets the scope boundary confirmed, *then* grills within it; recommended answers default to the smaller
option.
*Why:* a thorough interview has a completeness bias — left unchecked it enumerates every mode/format and
the feature balloons (a dry-run "minimal `parse_duration`" grew into a 3-format parser). Each added mode
must be an explicit scope decision the human opts into.

### ADR-10 — Secrets match on path components, tool-split

*Decision:* the secrets guardrail splits by tool. For file-target tools the target *is* a path → match
by path component (over-broad is fine). For Bash, tokenize and flag only tokens that clearly denote a
secret *file* — never a bare identifier.
*Why:* substring-matching `.env`/`key`/`credentials` against a Bash command's whole string false-denies
`python -c "os.environ.get('X')"`, and one false hit flips the analyzer's whole-run verdict to
VIOLATION, burying real signal. Guard and analyzer must share the identical predicate, tool included.

### ADR-11 — Isolation is proven by intent *and* effect: one policy, two legs

*Decision:* isolation is not a single mechanism but a **policy** feeding two independent legs. One
declarative per-agent policy ([`policy.py`](../sdlc-lite-plugin/policy.py) — a data rule table
plus `decide(agent_type, access, path)`) is imported by **both** a real-time in-hook *enforcer*
(`guard.py`, prevention, best-effort for Bash) and a post-hoc *auditor* (`analyzer/`, detection). The
auditor itself uses two signals with fixed roles: the transcript **content-fingerprint** (reads each
gate's tool *output*) is **authoritative / trust-voiding**; path extraction + literal-glob "unglob"
(reads the command *intent*) is **corroborating only**.
*Why:*
- **One SSOT kills the shared blind spot.** The enforcer and detective used to keep hand-copied
  predicates under "KEEP IN SYNC" comments, so a single Bash trick bypassed both at once — they were
  the *same* check twice, not two checks. Importing one definition means they cannot drift, and the
  policy becomes the seam where a role's rules are tightened once.
- **Best-effort Bash prevention is a real boundary, not a bug.** A string-inspecting hook cannot know
  what a `python -c …` or a `cd handoff && cat *` actually reads. Rather than pretend otherwise, the
  design pairs best-effort *prevention* with authoritative *detection*.
- **Effect beats intent for the trust claim.** The command string (what the run-log and guard see) is
  blind to a glob/indirect read; the tool *output* (what the transcript records) is not. Fingerprinting
  the protected artifact against each subagent's `toolUseResult` string leaves is **method-agnostic** —
  a leak via Bash `stdout`, Read `file.content`, or Edit `originalFile` all land in one scan — which is
  why it, not the path heuristic, is the authority. The path/unglob signal is kept only to *name* which
  file leaked; it shares the command-string blind spot, so it never stands alone.
- **Absence of proof is not proof of innocence.** The content audit needs the transcript, so without
  one it renders **UNKNOWN**, never PASS — the receipt stays honest about what was actually verified.

### ADR-12 — Model and effort integrity: honored pins, verified by the receipt

*Decision:* both model and effort are governed by the **agent-def frontmatter pin** and **proven**
by the post-run receipt — neither is enforced at dispatch. Pinned gates are dispatched **bare** (no
inline `model`); the frontmatter pin — including the *dated* reviewer pin `claude-opus-4-8` — is
honored, and the analyzer compares the transcript's *actual* resolved model against the pin: a
mismatch is a **FAIL**, a resolved model that matches is a PASS. **Effort** is likewise audit-only:
the receipt WARNs on any deviation from the pin, in either direction, but nothing prevents it. Both
pins come from one SSOT ([`agentdefs.py`](../sdlc-lite-plugin/agentdefs.py)), so what is
promised and what is verified cannot drift — the discipline ADR-11 gives the isolation rules via
`policy.py`.

*Why bare dispatch, not a dispatch-time enforcement hook:*
- **A frontmatter model pin is honored on a bare dispatch** — verified across four real sessions in
  [`model-pinning-findings.md`](findings/model-pinning-findings.md) §2 and re-probed 2026-09-14 (§7):
  a `claude-opus-4-8`-pinned agent dispatched by `subagent_type` alone ran on exactly
  `claude-opus-4-8` while its parent ran `claude-sonnet-5`. The documented resolution order is inline
  (1) > **frontmatter (2)** > `CLAUDE_CODE_SUBAGENT_MODEL` (3) > session (4) > account (5); with 1
  and 3 absent, the frontmatter pin governs.
- **Naming a model inline would break the dated pins.** The inline `model` slot is enum-restricted to
  family aliases `{sonnet, opus, haiku, fable}` — it cannot carry a dated id. Forcing a
  `claude-opus-4-8` reviewer to be named inline collapses it to the `opus` alias (a rank-1 argument
  that *overrides* the rank-2 frontmatter pin) → the floating `claude-opus-5`, destroying the
  exact-version reproducibility the dated pin exists for (ADR-2). Bare dispatch is the only way to
  honor a dated pin.
- **Historical note (#22 → #36).** #22 originally added a `PreToolUse` deny-if-unnamed hook (the
  Thomas-Witt technique, `guard.py::_dispatch_deny_reason`) on the premise that a frontmatter pin is
  *"silently dropped if the dispatch omits a model."* That premise is **false** on this platform (see
  above), and the hook was not merely redundant but **counterproductive for dated pins** — it forced
  the alias-only inline model that overrode them, re-creating the very wrong-model failure it meant to
  prevent (observed live in the #31b-i acceptance run). [#36](https://github.com/Sdaas/sdlc-lite/issues/36)
  reverted it: pinned gates dispatch bare.
- **The receipt is the guarantee, and it stays honest.** Model integrity is what the analyzer
  **verifies** from ground truth (the transcript's resolved `message.model`), not what a hook forces.
  Match is alias/dated-aware: a dated pin demands an exact id (ADR-2), an alias accepts any same-family
  tier. The receipt reports the *actual* resolved model/effort regardless, so a broken pin is never
  hidden — observability holds even where prevention is not possible (effort has no rank-1 lever at
  all, so it can only ever be proven, never forced).

### ADR-13 — One `sdlc-lite` plugin; two channels are two marketplaces in two repos

> **Status (2026-09-18):** **proven.** `1.0.0-beta.1` and `1.0.0-beta.2` were cut with `release.sh`
> (tag in this repo + umbrella repoint) and verified by an automated clean-room run
> (`release-verify.sh`, 17/17): from an isolated `CLAUDE_CONFIG_DIR` with no dev marketplace,
> `marketplace add Sdaas/claude-plugins` → `install sdlc-lite@sdaas` fetched the tagged commit via a
> **git-subdir** source (cached version matching `plugin.json`), passed Gate 0 preflight + Gate 1
> interview headless, and a `/plugin update` step advanced beta.1 → beta.2. `release.sh`,
> `RELEASING.md` §2/§4/§5, and the customer install commands are now authoritative.
>
> *Supersedes an earlier draft of this ADR* (a single repo carrying two catalog entries —
> `implement-feature` github-pinned + `implement-feature-dev` directory). That approach worked but was
> abandoned once we chose separate repos per plugin (below); the two-marketplace split is cleaner and is
> the ecosystem's documented pattern.

*Decision — the product is one plugin, `sdlc-lite`.* The plugin bundles the whole SDLC workflow — the
commands `/implement-feature` and `/analyze-run` today, `/plan-feature` next — over **one** shared
guard hook, **one** set of five model-pinned isolated gates, and **one** quality-standards SSOT. The
plugin folder is `sdlc-lite-plugin/`; `plugin.json` `name` is `sdlc-lite`; the isolated gates dispatch
as `sdlc-lite:<agent>` (e.g. `sdlc-lite:test-writer`). **Command names are independent of the plugin
name** and do not change. *Boundary rule:* a new command joins `sdlc-lite` **iff** it uses that shared
isolation infrastructure; an unrelated tool (say a personal-finance plugin) becomes a **separate plugin
in its own repo**.

*Decision — two channels, two marketplaces, two repos.* A Claude marketplace is exactly **one catalog
(`.claude-plugin/marketplace.json`) in one repo**, and a directory source loaded in place is **never
version-pinned**. So the channels are physically separate catalogs:

| Channel | Lives in | Catalog `name` | `sdlc-lite` entry source | Audience |
|---|---|---|---|---|
| **dev** | **this repo** (`Sdaas/sdlc-lite`) root catalog | `sdlc-lite-dev` | **directory** `./sdlc-lite-plugin` (live) | dev container only — enables `sdlc-lite@sdlc-lite-dev` |
| **release** | **umbrella repo** `Sdaas/claude-plugins` | `sdaas` | **git-subdir** (explicit https url to `Sdaas/sdlc-lite`, `path: sdlc-lite-plugin`), pinned `ref: vX.Y.Z` + `sha` | customers — `marketplace add Sdaas/claude-plugins` → `install sdlc-lite@sdaas` |

**Why `git-subdir`, not `github` (caught in the clean-room verify).** The plugin lives in the
`sdlc-lite-plugin/` **subdirectory** of `Sdaas/sdlc-lite`, but a plain `github` marketplace source can
only target a repo **root** — so the customer install resolved the repo root, found no `plugin.json`,
and loaded **zero commands**. The fix is a **`git-subdir`** source with `path: sdlc-lite-plugin`,
which targets the subdir. Its url must be an **explicit https url** (`https://github.com/Sdaas/sdlc-lite`),
not the `owner/repo` shorthand, because the shorthand defaulted to an **SSH** clone that failed in the
credential-less clean-room environment. Same tag/sha as the first cut — this was a catalog-source fix,
not a re-release.

The **umbrella** repo (`Sdaas/claude-plugins`, catalog `sdaas`) is the maintainer's cross-product
marketplace: each future plugin (in its **own** repo) gets one pinned git-subdir entry here, so `sdaas`
*honestly* aggregates plugins that live in different repos — which a single per-product catalog cannot.
This repo's root catalog is now **dev-only** (the container reads it via a directory source; it also
lists `toy-greet` for the Tutorial). Customers never read it — a README pointer routes them to the
umbrella so nobody accidentally `marketplace add Sdaas/sdlc-lite` and gets an unpinned live install.

A **release** is cut by `release.sh` (cross-repo): **bump `plugin.json` `version`** → **tag `vX.Y.Z`**
in this repo → **repoint the umbrella's `sdlc-lite` entry** `ref`/`sha` to that tag. All three are
required (see below). Verification is the gate — see the last bullet.

*Why:*

- **The bug, concretely.** A directory source *loaded in place* is never version-pinned. If customers
  installed off such an entry: they install Monday; you push a broken experiment to `main` Tuesday;
  Wednesday their tool re-resolves against `main` HEAD and runs your broken code — you never
  "released," yet their install moved under them. `plugin.json`'s `"version"` does no work for a
  directory source, so you **cannot freeze customers at a version**. That is #41 in one sentence.
- **The fix, concretely.** Customers install `sdlc-lite@sdaas`, whose source is the umbrella's
  `git-subdir` entry pinned to `v1.0.0-beta.1`'s commit — and *stop there*. Your Tuesday push to
  `Sdaas/sdlc-lite` `main` doesn't touch them; meanwhile the dev container, on the directory-source
  `sdlc-lite@sdlc-lite-dev`, *does* see Tuesday's code live — exactly what a developer wants. Customers
  move only when *you* cut the next release and they run `plugin update`.
- **Why separate repos + an umbrella, not one repo.** The maintainer will ship unrelated plugins
  (agentic-coding tools here, a finances plugin elsewhere) that shouldn't share a repo. Since one
  marketplace = one repo, aggregating across products *requires* a dedicated umbrella repo whose
  entries are pinned git-subdir sources into each product repo. Doing this now — at **zero customers** — avoids a
  customer-breaking marketplace migration later. It also matches the ecosystem's documented
  "separate stable/canary marketplaces at different refs" pattern and pins to a **commit SHA, not a
  moving tag** (`sha` wins over `ref` when both are set).
- **The version bump is the update trigger.** `/plugin update` compares the resolved `version` and
  **skips if it is unchanged** — so a release is `version` bump **+** tag **+** umbrella repoint, all
  three. (Set `version` in `plugin.json` only, never also in the marketplace entry — the platform
  silently prefers `plugin.json`.)
- **The dev container is a development harness, not a customer simulator.** It wears two hats: the
  pinned toolchain (a customer needs this too) *and* a directory-source marketplace that loads the
  plugin live (the opposite of a customer). That second hat sabotages a naive customer test — an
  install run while the dev marketplace is active can resolve the *local* copy and "pass" without
  proving anything. So #41's verify runs from an **isolated Claude config with no dev marketplace**:
  with no directory source to fall back to, `marketplace add Sdaas/claude-plugins` → `install
  sdlc-lite@sdaas` *must* fetch the tagged commit — making the customer path un-fudgeable and leaving
  dev state pristine. Only after that clean-room install runs `/implement-feature` end-to-end is a tag
  a real release.

---

### ADR-14 — One name, one surface; and a workflow is entered explicitly

> **Status (2026-09-23):** **measured, then fixed** (#55). Evidence:
> [`findings/2026-09-23-skill-suppression-findings.md`](findings/2026-09-23-skill-suppression-findings.md)
> — 3 load paths x 2 arms x 2 runs, 12/12 unambiguous.

*Decision — a command and a skill may never share a name.* `sdlc-lite-plugin/commands/<x>.md`
alongside `sdlc-lite-plugin/skills/<x>/` **shadows the skill**. Measured on **all three** load paths
(directory marketplace, `--plugin-dir`, installed-from-umbrella): `Skill(sdlc-lite:implement-feature)`
injects the *command's* markdown in place of `SKILL.md` and then reports *"the skill instructions were
previously loaded"*, so a re-invocation cannot recover. The conductor — holding a 12-line file that says
"load the skill" — improvises gate prose that resembles the real workflow. In one run it dispatched a
subagent to go find `SKILL.md` on disk.

*Decision — the shim was deleted, not renamed.* A skill registers **its own** slash command from its
`name:` frontmatter: with `commands/implement-feature.md` gone, `sdlc-lite:implement-feature` still
appears in the session's `slash_commands`, and typing the bare `/implement-feature` interactively
resolves and injects the score (verified in a pty-driven container session). The command file added
**no reachability** — only shadowing. That also retires the old *"thin command, heavy skill"* principle
(7 below): its premise was that a command buys lazy loading, and here it cost the body entirely.

*Decision — this plugin's skills are **explicit-entry only**, and that is enforced.* The two ways into a
skill are mechanically distinct:

| | the human types `/implement-feature` | the model auto-invokes from a phrasing match |
|---|---|---|
| interactive | CLI expands the slash command, injects `SKILL.md` directly — **no `Skill` tool call** | goes through the **`Skill` tool** |
| headless `-p` | identical — also expands, no `Skill` tool call | goes through the **`Skill` tool** |

The two call sequences, which is the whole mechanism:

```
you type /implement-feature   ──►  CLI expands the slash command
                                   ──►  <command-name> + SKILL.md injected as a user message
                                   ──►  conductor starts at Gate 0
                                   (no tool call  ──►  no PreToolUse  ──►  the guard never runs)

model decides from phrasing    ──►  Skill tool call {"skill": "sdlc-lite:implement-feature"}
                                   ──►  PreToolUse fires  ──►  guard DENIES
                                   ──►  model tells the user to type /implement-feature
```

The guard does **not** distinguish intent — it cannot see any. It denies *every* `Skill` call in the
`sdlc-lite:` namespace, unconditionally. The human's command survives only because it never makes
such a call. Because the human's path never touches the `Skill` tool, denying that tool yields
explicit-only entry **exactly**, with no need to infer intent. `hooks.json` therefore matches `Skill`, and
`policy.skill_invoke_decision()` denies the call, naming the slash command in the denial so the model
can tell the user what to type. The rule is **plugin-wide, not per-skill**: every skill this plugin ships
is a gated, repo-mutating workflow a human starts deliberately, so a future skill inherits the policy
instead of having to remember it.

The denial has **two legs** (#56), because the namespace is a harness convention and not a guarantee:
any `sdlc-lite:`-prefixed id (covering skills not yet written), **plus** any *bare* id naming a skill this
plugin actually ships — `policy.PLUGIN_SKILL_NAMES`, hand-maintained because `policy.py` is pure and
does no I/O, with `tests/test_entry_points.py` asserting it still matches `skills/`. A bare id we do
*not* ship stays allowed: it belongs to someone else. The skill `description` says the same thing in
prose — the usual defense-in-depth pair, role instruction *and* hook.

*Known fragility (accepted).* This brake rests on an assumption about **Claude Code's**
implementation, not on an invariant we control: that a typed slash command keeps expanding without
being routed through the `Skill` tool. If a future version routed it through that tool, the guard
would deny the human's own command too. It would fail **loudly** — a visible denial naming the slash
command — and `release-verify.sh`'s body canary catches it at the next release cut, so the failure
mode is a blocked workflow with a clear message, never a silent improvisation. Re-measure this
whenever Claude Code's skill/command resolution changes.

*Why it matters beyond tidiness.* Auto-invocation is not hypothetical: the prompt *"I want to add a
`to_roman(n)` helper to this python repo, built test-first with staged approvals"* loaded the entire
score, unasked. And a shadowed body fails **silently**: with the shim present, the typed slash
expands to the shim, the follow-up skill load answers *"already loaded"*, and the conductor recovers
by **searching the filesystem and `Read`ing `SKILL.md` itself** — still printing `Preflight passed`
and still announcing gates, so every downstream signal looks healthy. Two regression
checks exist because of that: `tests/test_entry_points.py` (structural — the name collision, host-only,
no model call) and a behavioral canary asserting `SKILL.md`-only text, since gate markers prove nothing.

---

## 7. Design principles (distilled)

The full running catalog lived in the retired `PATTERNS.md`; these are the load-bearing principles for
anyone changing the plugin.

**Skills & workflow**
- **Trigger-oriented descriptions.** A skill's `description` decides *when* it activates — write it
  about situations/phrasings, not just what it is.
- **One name, one surface (ADR-14).** A command and a skill must never share a name — the command
  shadows the skill and the `SKILL.md` body never loads, on every load path. A skill registers its own
  slash command, so a "thin command that just loads the skill" buys no reachability; it only shadows.
  *(This replaces the former "thin command, heavy skill" principle, whose premise #55 disproved.)*
- **A workflow is entered explicitly (ADR-14).** This plugin's skills run when the human types the
  slash command, never from a phrasing match. Enforced by the guard hook denying `Skill` calls in the
  `sdlc-lite:` namespace — the typed slash command bypasses that tool entirely — and stated in prose in
  the skill `description`.
- **Driverless workflow.** The skill body is an ordered English script; numbered gates + machine
  conditions + "repeat until" loops replace orchestration code.
- **Gate = approval checkpoint.** The approver is a human (STOP-until-APPROVED, worded imperatively) or
  a machine-checkable condition ("until all tests pass"). Choose per phase.
- **Bound every automated loop** and surface to the human on no progress.

**Subagents & handoff**
- **Context-as-files handoff.** Each gate reads a defined inbox and writes a defined outbox as files —
  durable, single-source-of-truth, and the mechanism that lets you *choose* what an agent sees.
- **Asymmetric inboxes** — blind the producer (test-writer), inform the critic (test-reviewer).
- **Standards live in one file, not in each brief.** Briefs *load* `quality-standards.md`; to raise the
  bar, edit that file. Per-feature *numbers* (coverage/mutation) live in the test plan; universal
  *commands* + the definition of "green" live in `quality-standards.md`.
- **Anchored defaults beat free-pick.** Ship a documented anchor (mutation kill-rate 80%) and require
  justification to deviate, surfaced at approval — an agent handed a metric with no anchor drifts.

**Quality gating**
- **Split checks by speed.** Fast checks (`ruff` + `mypy` + `pytest`) define the implementer's
  inner-loop "green"; slow checks (`pytest-cov` + `mutmut`) gate CODE-REVIEW.
- **Situational checks are boundary-driven.** Concurrency testing is mandated only when the boundary
  inventory shows the feature is concurrent/async — otherwise skipped with a stated reason.
- **VERIFY ≠ green tests.** Drive the *real* feature on each AC and exercise every boundary un-mocked —
  a mocked test only proved the mock. Nested loop: unit-green inside (IMPLEMENT), observed-behavior
  outside (VERIFY, a fresh read-only agent).
- **Mutation grades tests retroactively.** A surviving mutant is an injected bug no test caught → a
  weak/tautological test, so mutation at CODE-REVIEW grades the test-writer + test-reviewer as a number.
- **A critic may probe, never implement.** A reviewer may write tiny throwaway probes but must not
  build a reference implementation; empirical mutation is implementation-specific and belongs at
  CODE-REVIEW against the real code, not before it.
- **Stop the producer grading its own homework.** When an agent's acceptance criteria live in files it
  could technically edit (the implementer & the tests), deny it write access to those files by role.

**Enforcement & observability**
- **Defense-in-depth** — role instruction *and* hook.
- **Ship reliability-critical config with the plugin**, not project settings (headless-fire).
- **Verify runtime behavior; don't trust docs/config** — model, tool blocks, hook firing, and agent
  naming were all confirmed empirically (the docs were wrong on plugin-agent naming — it's namespaced,
  `plugin:agent`, not bare — and unsure on headless hooks).
- **Attribute every tool call** via `agent_type`/`agent_id` for per-agent rules and a trustworthy audit.

---

## 8. Testing & dry-run methodology

**The plugin is never installed into the developer's global `~/.claude`.** It's installed and run
inside a **dev container** with its own isolated `~/.claude` (login persisted in the named volume
`sdlc-lite-claude`) and the pinned Python toolchain. The container is both the blast-radius
boundary (the product *writes and commits code*) and the environment where Gate 0's preflight passes.
Full lifecycle — build, shell in, teardown levels, VS Code palette commands, the container's Claude UX
provisioning — is in **[DEVCONTAINER.md](DEVCONTAINER.md)**.

### Fresh setup from zero (no container, image, or volume yet)

1. **Docker up** — `docker ps` — confirms Docker Desktop is running.
2. **Build + start** — `devcontainer up --workspace-folder .` — builds the image (first time only)
   and starts the container, named per `runArgs` in `.devcontainer/devcontainer.json`. Creates the
   `sdlc-lite-claude` volume if absent.
3. **Verify toolchain** — `devcontainer exec --workspace-folder . bash -c "python --version && ruff
   --version && mypy --version && pytest --version && python -c \"import importlib.metadata as m;
   print('mutmut', m.version('mutmut'))\" && claude --version"` — confirms the pinned toolchain
   (`postCreateCommand`) installed cleanly.
4. **Login** — `devcontainer exec --workspace-folder . claude` (interactive) — first run on a fresh
   volume needs OAuth login; persists into the `sdlc-lite-claude` volume.
5. **Install plugin** — inside that `claude` session: `/plugin install sdlc-lite@sdlc-lite-dev`
   (or `claude plugin install sdlc-lite@sdlc-lite-dev` from a container shell) — **known gap:**
   `postStartCommand` registers the `sdlc-lite-dev` marketplace (a `directory` source pointing at the
   bind-mounted `/workspaces/sdlc-lite`, per `.devcontainer/claude/settings.json`) but does not install
   the plugin itself on a fresh volume — this step is required once per fresh volume. This dev catalog
   holds a **single directory-source entry** (`sdlc-lite` → `./sdlc-lite-plugin`), so the install loads
   from the **local workspace**, not GitHub. The tag-pinned *customer* channel lives in a separate
   umbrella repo (`Sdaas/claude-plugins`, `sdlc-lite@sdaas`) — see the channels table in ADR-13 and the
   clean-room verification note below.
6. **Verify** — `/plugin` or `/plugin list` inside Claude — confirms `sdlc-lite` shows enabled.

To rename the container, set `runArgs: ["--name", "<name>"]` in `.devcontainer/devcontainer.json`
before step 2 — `devcontainer` CLI has no `--name` flag of its own.

**Clarification — step 5 installs from the local workspace, not GitHub.** The container's
`settings.json` pre-registers the `sdlc-lite-dev` marketplace as a `directory` source pointing at
`/workspaces/sdlc-lite` (the bind-mounted repo). It resolves `sdlc-lite` — the sole directory-source
entry (`./sdlc-lite-plugin`) in `.claude-plugin/marketplace.json` — and copies it into
`~/.claude/plugins/cache/`. The github-tag-pinned *customer* channel is **not in this repo's catalog**;
it lives in the umbrella repo `Sdaas/claude-plugins` (`sdlc-lite@sdaas`) — ADR-13. This is the dev
path — the "Clean-room verification" note below documents the *separate* real-user path
(`claude plugin marketplace add Sdaas/claude-plugins` → install `sdlc-lite@sdaas`, a real GitHub clone).

Two harnesses:

- **Host unit tests** — `guard.py` and `analyzer/` have real unit tests (synthetic stdin, synthetic
  run-logs + transcripts including both degradation modes). Run them in-container against the pinned
  toolchain: `python -m pytest sdlc-lite-plugin -q`. `guard.py`'s tests cover every deny/allow
  branch; the analyzer's cover both transcript-degradation modes.
- **End-to-end dry runs** — a human drives an actual `/implement-feature` run in a container terminal
  (a TTY constraint), then the analyzer is run over the resulting logs and the fallout is fixed.

**Reviewing handoff files mid-run, from the Mac.** When a run happens against a fixture's scratch
repo (`/workspaces/<slug>-run/`, see "Standard fixtures" below), its `.implement-feature/` artifacts
are **container-only** — they're outside the `sdlc-lite` bind mount, so they don't exist on the Mac's
filesystem and a normal Mac editor/Finder can't see them. Three ways to read a gate's draft/handoff
file at a STOP:
1. **`devcontainer exec` + `cat`** — quickest, no GUI: `devcontainer exec --workspace-folder . cat
   /workspaces/<slug>-run/.implement-feature/<run>/handoff/draft/<file>.md`.
2. **VS Code, attached to the container** — Command Palette → **"Dev Containers: Attach to Running
   Container"** → pick the container → open `/workspaces/<slug>-run`. This differs from "Reopen in
   Container," which only ever shows the bind-mounted `sdlc-lite` folder — *Attach* opens a window on
   the container's whole filesystem, so fixture scratch repos are visible too.
3. **`docker cp`** — pull a copy onto the Mac as a real local file: `docker cp
   <container>:/workspaces/<slug>-run/.implement-feature/<run>/handoff/draft/<file>.md ./review.md`.

**A dry run is a bug-finding machine.** The first full run (`parse_duration`) validated the core design
*and* shook out ~13 concrete improvements. Subsequent runs (`slugify`, and the async `CachedFetcher`
with a fault-injection pass) confirmed the fixes and the invariants: model pinning splits exactly as
designed (reviews on Opus, producers on Sonnet — transcript-proven), isolation holds (the test-writer
stayed algorithm-blind, the implementer never touched a test file), and the pipeline commits.

### Two Claude profiles in one container (`CLAUDE_CONFIG_DIR`)

`CLAUDE_CONFIG_DIR` is where Claude Code keeps a **per-user profile** (default `~/.claude`): the
login/credentials, `settings.json` (model, permissions, hooks, `enabledPlugins`,
`extraKnownMarketplaces`), the installed-plugin cache, and which marketplaces are registered. Point
that variable at a **different directory** and you get a **completely separate Claude profile** — a
different login, different marketplaces, different installed plugins — on the **same machine, same
filesystem, same toolchain**. That one lever lets a single dev container be **two environments at
once**:

| | `~/.claude` (default) — **DEV** | `~/.claude-*` — **CUSTOMER / clean-room** |
|---|---|---|
| Marketplace | `sdlc-lite-dev` (directory source) | `sdaas` (umbrella, `git-subdir` from GitHub) |
| Plugin source | **live from the workspace** | **the real GitHub release** (tag-pinned) |
| Purpose | iterate on the plugin | simulate exactly what a stranger installs |
| Python toolchain | **shared** — installed system-wide (`uv pip install --system`) | **shared** — the same one |

The toolchain is installed at the OS level, so the customer profile inherits it for free; the
isolation is **purely the config layer**. The dev profile answers *"does my edit work live?"*; a
fresh clean-room profile (no dev marketplace) answers *"does the shipped artifact work for someone
who's never seen my workspace?"* — which is exactly what the release gate (#41 Phase E) needs. No
second container required.

### Automated clean-room verification (`release-verify.sh`)

`release-verify.sh` (repo root) automates the customer path end-to-end — *"automate whatever can be
automated"* — and hands off only the irreducibly-human step. It spins up a **fresh isolated
`CLAUDE_CONFIG_DIR`** (no dev marketplace), installs `sdlc-lite@sdaas` from the umbrella on GitHub,
asserts a genuine `git-subdir` install (cached version == `plugin.json` version, commands/agents/hooks
present), then runs a **headless two-call Gate 0/Gate 1 smoke** on a fresh fixture:

- **call 1** — `claude -p "/implement-feature <request>"` → asserts **Gate 0 "Preflight passed"** and
  the confirm-STOP (`.active-run` written);
- **call 2** — `claude --continue -p "APPROVED …"` → asserts the **Gate 1 interview** started.

Finally it proves **`/plugin update`** (git/fs only, no model calls): it reconstructs the umbrella
catalog **as of the previous tag** (rewriting the entry's `ref`/`sha` to `v<prev>` in a throwaway
clone), installs that older release, then advances the catalog to the current pin and runs
`marketplace update` + `plugin update <plugin>` — asserting the installed version moves `<prev>` →
`<current>`. Skipped automatically on the first release (no previous tag).

Last, it runs the **milestone eval suite** — T1 of the
[verification ladder](verification-ladder.md): `claude plugin eval` over `sdlc-lite-plugin/evals/`
with both arms, a pinned `--model`, and `--threshold 0.8`. This step grades the plugin **source at
the checkout** (the tag, at release time), not the installed copy. The whole run is **18/18** when a
previous tag exists.

The full gated run past Gate 1 stays a **human** step (approval gates; never commits before a human
approves), which the script prints as a handoff.

**Auth — `.env` (git-ignored).** The `claude -p` calls run **inside the container** (that's where the
toolchain and the clean-room profile live), so they need non-interactive auth. Supply it via a
repo-root `.env` that the script `source`s *inside* the container (bind-mounted at
`/workspaces/sdlc-lite/.env`, so the token never appears in host process args, and `*.env` is
git-ignored so it can't be committed). One line:

```dotenv
CLAUDE_CODE_OAUTH_TOKEN=<token>
```

Mint the token **once on the Mac** with **`claude setup-token`** (a long-lived, Claude-subscription
token — it doesn't expire like a session login) and paste its output. An `ANTHROPIC_API_KEY=…`
(Console key, API-billed) works instead. Copy `.env.example` → `.env` to start. Run:
`./release-verify.sh` (add `--keep` to retain the config/fixture, `--no-smoke` for install-verify only,
`--no-evals` to skip the ~15-minute eval suite, `--evals-only` to run just that suite).

### The plugin loads from the workspace

In the container, the directory-source marketplace loads the plugin **from the mounted workspace**
(`/workspaces/.../sdlc-lite-plugin/**`), *not* the `~/.claude/plugins/cache` copy (which is
vestigial there). So editing the plugin needs **no cache-sync step** — a workspace edit takes effect on
a **fresh container Claude session restart** (SKILL/agents load at startup; the guard hook reloads per
tool call). Note this differs from a *real end-user* install, which hits the cache path — the User
Guide documents that distinction.

### Install-from-GitHub verification (real user path, checked)

> **⚠️ Superseded by the umbrella design (ADR-13, #41).** The run below verified the *old* single-repo
> path (`marketplace add Sdaas/sdlc-lite` → `install implement-feature@sdaas-sdlc-lite`), which no
> longer exists — the customer channel moved to the umbrella repo `Sdaas/claude-plugins`
> (`sdlc-lite@sdaas`). Kept as a historical record that a github-clone install works end to end; the
> **new** customer path is verified by the automated **`release-verify.sh`** clean-room run (see the
> CLAUDE_CONFIG_DIR two-profile section below) — 17/17, incl. a `/plugin update` bump.

The **real end-user path** — `claude plugin marketplace add Sdaas/sdlc-lite` +
`claude plugin install implement-feature@sdaas-sdlc-lite` — was verified for real on 2026-09-12,
inside the dev container but from `/tmp` (outside the bind-mounted workspace, so `marketplace add`
had no local copy to fall back to):

- `claude plugin marketplace add Sdaas/sdlc-lite` logged `cloning via HTTPS:
  https://github.com/Sdaas/sdlc-lite.git` and `Clone complete, validating marketplace…` — a genuine
  network clone, not the directory source.
- `claude plugin install implement-feature@sdaas-sdlc-lite` succeeded; `claude plugin list` showed it
  `✔ enabled`.
- The installed cache (`~/.claude/plugins/cache/sdaas-sdlc-lite/implement-feature/0.1.0/`) was
  spot-checked for completeness: `skills/implement-feature/SKILL.md` (615 lines, 53 `Gate`
  mentions) and all five `agents/*.md` files were present and intact.
- The test marketplace/plugin were removed afterward so they don't linger in the persisted
  `sdlc-lite-claude` login volume.

### Fault injection (the un-mocked resiliency check)

For a feature with a network boundary, the VERIFY gate and the resiliency review dimension must be
exercised against *real* faults, not just asserted. The async `CachedFetcher` run used
**`httpx.MockTransport`** through the feature's transport-injection seam — deterministic, no network,
no extra process — to inject:

- transport-level faults (a handler that *raises* `ReadTimeout`/`ConnectTimeout` *before* any response
  exists — a different code path from `raise_for_status()`);
- response-level faults (a handler returning a 5xx `Response`);
- both under `asyncio.gather(...)` to exercise request-coalescing under fault.

The feature proved resilient (timeouts/5xx propagate the right exception type and are **not cached**; a
coalesced wave issues exactly one request and all callers observe the same fault; a fresh call after
recovers). **No bug** — but the pass surfaced a real methodology trap worth internalizing:

> **Transport-level faults ≠ response-level faults.** The run's test plan and resiliency review
> enumerated only *response-level* faults (non-2xx status, malformed body). It conflated "no
> *configurable* timeout" (a correct scope decision) with "no need to *test* timeout behavior at all"
> (a coverage gap). Timeouts and connection failures are a real runtime fault path for any network
> call, on a different code path from status errors. The plugin now nudges: **for any feature whose
> boundary inventory includes a network boundary, require at least one transport-level fault test** —
> a timeout/connection failure raised before a response — asserting it *propagates* and is *not
> cached*, distinct from response-level faults. (Applied to `quality-standards.md`,
> `test-plan-template.md`, `test-writer.md`, and `code-reviewer.md`.)

### Standard fixtures — `test-fixtures/python-starter/`

**Why a committed template, not a generator script.** An empty-folder dry run lets the conductor
improvise the code layout, which tests nothing about whether `/implement-feature` integrates into a
*real* codebase — an empty repo is the easy case. A fixture must also be **non-empty**: a small,
pre-existing package with its own module + tests, so a run genuinely exercises whether the
implementer places new code correctly alongside code that was already there. Generating that content
fresh each run (via `uv init` or similar) would make runs non-reproducible — "what did the generator
do today" becomes a confound in whatever the run is supposed to be testing. So each fixture is
**committed, versioned, and byte-identical** across runs; a script only *copies* it into a scratch
location, never invents its content.

**Layout, per fixture** (`test-fixtures/python-starter/<slug>/`):
- `pyproject.toml` — src-layout, package name derived mechanically from the slug
  (`roman-numeral` → `src/roman_numeral/`).
- `src/<pkg>/greet.py` + `tests/test_greet.py` — the **shared pre-existing module**, identical bytes
  in every fixture: `greet(name) -> f"Hello, {name}!"`, raising `ValueError` on empty/whitespace
  input. It exists purely as inert "already there" scaffolding for the implementer to coexist with —
  deliberately boring, so the one thing that varies between fixtures is the feature under test, not
  the noise around it.
- `BRIEF.md` — the literal, one-line `/implement-feature` prompt for that fixture, stored verbatim so
  the invocation is byte-identical run to run. A paraphrased prompt would be a second, invisible
  variable — if a receipt looks different, you want that to mean the *workflow* changed, not that the
  wording changed.

**Fixtures today:** `roman-numeral` (int ↔ Roman numeral, both directions, validates malformed
input). `parse-duration` and `async-cached-json-fetcher` — the pair used in the plugin's earliest dry
runs — are the next two planned, built the same way once this mechanism is proven.

**What happens when you run one.** `test-fixtures/setup-fixture.sh <slug>`, run **on the Mac**:
```bash
test-fixtures/setup-fixture.sh roman-numeral
```
It shells into the container and: refuses if `/workspaces/<slug>-run` already exists (a stale
scratch dir is removed by hand — `rm -rf /workspaces/<slug>-run` — never silently wiped, same
philosophy as the workflow's own `.active-run` lock); copies the template to
`/workspaces/<slug>-run/`; `git init`s it fresh on branch `main` and commits the copied baseline
(so `/implement-feature`'s "never commit on default branch" rule forces the run onto its own
feature branch); `pip install -e .` so Gate 0's importability preflight passes.

**What a developer does next:**
```bash
devcontainer exec --workspace-folder . bash -c "cd /workspaces/roman-numeral-run && claude --model opus"
```
then, inside that session, paste `BRIEF.md`'s content after `/implement-feature`. Everything from
there — layout confirmation, interview, gates — proceeds exactly as any other run, just against a
known, reproducible starting point instead of an ad hoc one.

**What this is not.** This script only creates the scratch repo — it doesn't drive the workflow's
gate prompts or destroy/rebuild the container. Those are separate, larger, not-yet-built pieces:
**#21** (destroy + rebuild the container fresh per run, deterministic setup) is expected to wrap this
script rather than reinvent it; **#34** (an agent driving the gates unattended, with the receipt —
never the driver's judgment — as the pass/fail oracle) consumes a fixture's `BRIEF.md` as its input
prompt. Both are v1.1/v2, independent of this script, and neither blocks using it by hand today.

---

## 9. When you edit the product

- **Behavior lives in Markdown** — `SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`. Editing the
  workflow means editing these, not writing code.
- **Change a gate's model/effort/tools** → edit the matching `agents/*.md` frontmatter (effort is
  frontmatter-only).
- **Change what an agent may read/write** → update *both* the agent's prose inbox **and** `guard.py`
  (defense-in-depth), and keep the analyzer's mirrored predicate in sync.
- **Change "green" or a threshold policy** → edit `references/quality-standards.md` (the single source
  of truth), not individual briefs.
- **Verify before you rely on runtime behavior** — do a container dry run; the transcript and the
  guard's audit log are your ground truth.
