# Developer Guide — architecture, decisions, and how to work on the plugin

This guide is for someone improving `implement-feature`. It explains the architecture, the two pieces
of real code (the guard hook and the analyzer), the design decisions and *why* they were made (ADRs),
the design principles distilled from building it, and the testing methodology. If you only want to
*run* the plugin, read the [User Guide](user-guide.md); for the underlying concepts start with the
[Tutorial](tutorial.md).

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
implement-feature-plugin/
├── .claude-plugin/plugin.json          # identity metadata
├── commands/
│   ├── implement-feature.md            # thin entry point → loads the skill
│   └── analyze-run.md                  # standalone re-analysis command
├── skills/implement-feature/
│   ├── SKILL.md                        # the conductor's score (all gates)
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
  **plugin-namespaced** `subagent_type` — `implement-feature:test-writer`, never the bare name.

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
| 4 | TEST-REVIEW | [I] `test-reviewer` | `claude-opus-4-8` (pinned) / low | machine (verdict) |
| 5 | IMPLEMENT | [I] `implementer` | `sonnet` / medium | machine (green) |
| 6 | VERIFY | [I] `verifier` | `sonnet` / medium | machine (observed pass) |
| 7 | CODE-REVIEW | [I] `code-reviewer` | `claude-opus-4-8` (pinned) / high | machine (verdict) |
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
effort: high
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

The invariant these pins enforce: **design and every review use a higher model (or effort) than
implementation.** The two reviewers pin the *dated* `claude-opus-4-8` for reproducibility; the
producer gates (`test-writer`, `implementer`, `verifier`) pin the floating `sonnet` alias.

**The pins are the SSOT for the receipt (#22).** [`agentdefs.py`](../implement-feature-plugin/agentdefs.py)
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
e.g. `implement-feature:test-writer`) and `agent_id` carried on stdin. Five jobs:

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
  [`implement-feature-plugin/policy.py`](../implement-feature-plugin/policy.py) — shared predicates
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
([`analyzer/auditor.py`](../implement-feature-plugin/analyzer/auditor.py)) fingerprints each
content-protected artifact (e.g. `03-design-internal.md`) and scans each subagent transcript's **tool
output** for it. Because a leak lands in *some* string leaf of the transcript's `toolUseResult` (Read
→ `file.content`, Bash → `stdout`, Edit → `originalFile`) *however* it was read, this catches the
glob/indirect leak the command-string legs cannot see, and it is **method-agnostic**. A hit is
**trust-voiding**: the Gate-11 report prints `THIS RUN IS UNTRUSTED` and the receipt's *Files seen*
column shows `❌ LEAK`. *Which* artifact a role is forbidden is decided by `policy.decide()`, so the
auditor and the guard agree on "protected" by construction. (On-disk record shapes: see
[`analyzer/TRANSCRIPT-FORMAT.md`](../implement-feature-plugin/analyzer/TRANSCRIPT-FORMAT.md) §5.)

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
[`design/audit-observability-findings.md`](../design/audit-observability-findings.md); the audit
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
[`implement-feature-plugin/analyzer/TRANSCRIPT-FORMAT.md`](../implement-feature-plugin/analyzer/TRANSCRIPT-FORMAT.md).

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
  *requested* model/effort from the agent-def pins ([`agentdefs.py`](../implement-feature-plugin/agentdefs.py))
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
`/implement-feature:analyze-run`. Full detail: `analyzer/README.md`.

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
declarative per-agent policy ([`policy.py`](../implement-feature-plugin/policy.py) — a data rule table
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
pins come from one SSOT ([`agentdefs.py`](../implement-feature-plugin/agentdefs.py)), so what is
promised and what is verified cannot drift — the discipline ADR-11 gives the isolation rules via
`policy.py`.

*Why bare dispatch, not a dispatch-time enforcement hook:*
- **A frontmatter model pin is honored on a bare dispatch** — verified across four real sessions in
  [`model-pinning-findings.md`](../design/model-pinning-findings.md) §2 and re-probed 2026-09-14 (§7):
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

---

## 7. Design principles (distilled)

The full running catalog lived in the retired `PATTERNS.md`; these are the load-bearing principles for
anyone changing the plugin.

**Skills & workflow**
- **Trigger-oriented descriptions.** A skill's `description` decides *when* it activates — write it
  about situations/phrasings, not just what it is.
- **Thin command, heavy skill.** A command file is *always* resident in context; a skill body loads
  on demand. Keep commands near-empty (just load the skill); put the heavy prose in `SKILL.md`.
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
provisioning — is in **[DEVCONTAINER.md](../DEVCONTAINER.md)**.

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
5. **Install plugin** — inside that `claude` session: `/plugin install implement-feature@daas-plugins`
   (or `claude plugin install implement-feature@daas-plugins` from a container shell) — **known gap:**
   `postStartCommand` registers the `daas-plugins` marketplace (a `directory` source pointing at the
   bind-mounted `/workspaces/sdlc-lite`, per `.devcontainer/claude/settings.json`) but does not install
   the plugin itself on a fresh volume — this step is required once per fresh volume. This installs
   from the **local workspace**, not GitHub — see "Install-from-GitHub verification" below for the
   separate real-user path.
6. **Verify** — `/plugin` or `/plugin list` inside Claude — confirms `implement-feature` shows enabled.

To rename the container, set `runArgs: ["--name", "<name>"]` in `.devcontainer/devcontainer.json`
before step 2 — `devcontainer` CLI has no `--name` flag of its own.

**Clarification — step 5 installs from the local workspace, not GitHub.** The container's
`settings.json` pre-registers the `daas-plugins` marketplace as a `directory` source pointing at
`/workspaces/sdlc-lite` (the bind-mounted repo, source `./implement-feature-plugin` in
`.claude-plugin/marketplace.json`). `/plugin install implement-feature@daas-plugins` just resolves
that name against the already-known marketplace and copies it into `~/.claude/plugins/cache/`. This
is the dev path — the "Install-from-GitHub verification" note below documents the *separate*
real-user path (`claude plugin marketplace add Sdaas/sdlc-lite`, a real GitHub clone) as something
checked once, not the path used here.

Two harnesses:

- **Host unit tests** — `guard.py` and `analyzer/` have real unit tests (synthetic stdin, synthetic
  run-logs + transcripts including both degradation modes). Run them in-container against the pinned
  toolchain: `python -m pytest implement-feature-plugin -q`. `guard.py`'s tests cover every deny/allow
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

### The plugin loads from the workspace

In the container, the directory-source marketplace loads the plugin **from the mounted workspace**
(`/workspaces/.../implement-feature-plugin/**`), *not* the `~/.claude/plugins/cache` copy (which is
vestigial there). So editing the plugin needs **no cache-sync step** — a workspace edit takes effect on
a **fresh container Claude session restart** (SKILL/agents load at startup; the guard hook reloads per
tool call). Note this differs from a *real end-user* install, which hits the cache path — the User
Guide documents that distinction.

### Install-from-GitHub verification (real user path, checked)

The **real end-user path** — `claude plugin marketplace add Sdaas/sdlc-lite` +
`claude plugin install implement-feature@daas-plugins` — was verified for real on 2026-09-12,
inside the dev container but from `/tmp` (outside the bind-mounted workspace, so `marketplace add`
had no local copy to fall back to):

- `claude plugin marketplace add Sdaas/sdlc-lite` logged `cloning via HTTPS:
  https://github.com/Sdaas/sdlc-lite.git` and `Clone complete, validating marketplace…` — a genuine
  network clone, not the directory source.
- `claude plugin install implement-feature@daas-plugins` succeeded; `claude plugin list` showed it
  `✔ enabled`.
- The installed cache (`~/.claude/plugins/cache/daas-plugins/implement-feature/0.1.0/`) was
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
