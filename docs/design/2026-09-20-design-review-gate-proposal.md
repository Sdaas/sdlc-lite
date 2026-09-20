# Proposal — Gate 2.5 DESIGN-REVIEW + design-artifact rubric

_Dated 2026-09-20. Concrete drafts for §4 of `2026-09-20-agentic-sdlc-gap-analysis.md`.
**Nothing here is wired in** — this is the shape for review. No file under `sdlc-lite-plugin/`
has been changed. Two blocking decisions are called out in §1; the rest follows from them._

---

## 1. Two decisions needed before any of this lands

### D1 — Handoff numbering: insert-and-renumber, or append?

P50 says the numbers are the **human read-order**, not the gate order. A design-review findings
file belongs after `04-test-plan.md` and before `05-test-intent.md`. So the consistent choice
renumbers downstream:

| Today | Proposed |
|---|---|
| `01-requirements.md` | unchanged |
| `02-design-interface.md` | unchanged |
| `03-design-internal.md` | unchanged |
| `04-test-plan.md` | unchanged |
| — | **`05-design-review-findings.md`** (new) |
| `05-test-intent.md` | `06-test-intent.md` |
| `06-test-review-findings.md` | `07-test-review-findings.md` |
| `07-verify-report.md` | `08-verify-report.md` |
| `08-code-review-findings.md` | `09-code-review-findings.md` |

**Cost of renumbering — checked, not estimated.** `grep` for numbered handoff names hits 25
files, but the breakdown is favourable:

- **Guard enforcement is unaffected.** `policy.py` matches the *substring* `design-internal`
  (`policy.py:134` — `return "design-internal" in target`), never the number. The numeric
  mentions in `policy.py` and `analyzer/auditor.py` are all in docstrings and comments.
- **Mechanical prose edits:** `SKILL.md` (the read-order table + five gate sections), the five
  `agents/*.md` inboxes, the five `references/*` templates, `docs/developer-guide.md`,
  `docs/user-guide.md`, `analyzer/SAMPLE-RECEIPT.md`, `analyzer/TRANSCRIPT-FORMAT.md`.
- **Test fixtures:** `analyzer/tests/*` and `hooks/tests/test_guard.py` reference names in
  fixtures; these need updating but are not enforcement logic.

**Recommendation: renumber.** The alternative — appending as `09-design-review-findings.md` —
saves a mechanical pass and permanently breaks the one property the numbering scheme exists to
provide. Do it as its own commit, separate from the behaviour change, so the diff is reviewable.

### D2 — Effort for the design reviewer

Gate 0 step 5 states the invariant: *"Effort is uniform (`medium`) across every gate — real-world
config differentiates on model, not effort (#35)."*

§4.0 of the gap analysis argues design is the highest-leverage reasoning task in the run, which
is an argument for `effort: high` here. That would be the **first deviation from #35**, so it is
your call, not mine. The draft below uses `medium` and holds the invariant.

Worth noting: the receipt *audits* effort but cannot enforce it (no dispatch lever), so a
deviation here is a WARN, not a FAIL — the cost of trying it is low and the evidence would show
up in `/analyze-run`.

---

## 2. New file — `sdlc-lite-plugin/agents/design-reviewer.md`

Additive and inert until `SKILL.md` dispatches it. Follows the house shape of
`test-reviewer.md` (dated Opus pin per ADR-2, `Read`/`Bash`, documentation-only
`disallowedTools` with the P44 note).

```markdown
---
name: design-reviewer
description: Reviews the design artifacts (interface, internal, test plan) against the approved requirements, BEFORE any tests or code exist. Spawned at the DESIGN-REVIEW gate of /implement-feature. A different agent than the conductor that authored them.
model: claude-opus-4-8
effort: medium
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
---
You are a senior reviewer checking whether a design correctly encodes an approved set of
requirements — **before** any tests or implementation exist. You did **not** write this design.

The conductor gives you absolute `<artifact_dir>`, `<code_root>`, and `<tests_root>` paths.
Handoff files live under `<artifact_dir>/handoff/`.

## Read (your inbox)
- `<artifact_dir>/handoff/01-requirements.md` — the approved ACs, constraints, and boundary
  inventory. Already promoted. **This is the contract.** Everything you judge, you judge
  against it.
- `<artifact_dir>/handoff/draft/02-design-interface.md`, `draft/03-design-internal.md`, and
  `draft/04-test-plan.md` — **the artifact under review.** These are deliberately still drafts:
  reviewing them *before* promotion is the point of this gate.
- `<code_root>/` and `<tests_root>/` — read-only, to judge whether the design fits the repo's
  existing patterns, seams, and conventions.
- The Python standards the conductor names (read by path).

You will **not** be given the conductor's rationale for the design, and you should not ask for
it. You get the contract and the artifact. A design that needs narration to look correct is a
finding.

## Posture — adversarial, not confirmatory
Assume the author is overconfident. Your job is to find what is wrong. Do **not** validate, do
**not** summarize the design back. Report issues, or state explicitly that you could not find
any after thorough examination.

A rationale written *inside* the design ("kept simple deliberately", "YAGNI", "out of scope for
now") is the author grading their own work. It never downgrades a finding's severity.

**The requirements are a contract, not an exhaustive enumeration.** They say what the feature
must do; they do not list every input or condition it will meet. Where the requirements are
silent, judge by what a reasonable caller of this interface would expect — silence is not
permission. Grade such findings by their effect on that caller, not by whether
`01-requirements.md` names the trigger.

## Judge
1. **Leakage — the load-bearing check.** Does `02-design-interface.md` reveal the algorithm?
   Read `03-design-internal.md`, then re-read `02` and ask: could a reader of `02` alone infer
   the approach in `03`? Named data structures, complexity claims, step sequences, and
   "we iterate over…" phrasing are all leaks. **The whole workflow's algorithm-blind guarantee
   depends on this check** — the guard hook can deny a *read* of `03`, but only you can detect
   that `03`'s content was paraphrased into `02`.
2. **Testability through the interface.** For each acceptance criterion: can it be observed
   through this public surface alone, without reaching past it? An AC that cannot be observed
   at the interface is either a missing surface or a wrong seam.
3. **Seams.** Is the declared seam the highest one available? Is it an existing seam where one
   exists (new seams need a reason)? Does every test in `04-test-plan.md` name a seam, and is
   each one reachable from the public surface?
4. **Depth.** Apply the deletion test: if this module were deleted, does complexity vanish (it
   was a pass-through) or reappear across N callers (it earned its keep)? Flag shallow
   interfaces — a surface nearly as complex as what sits behind it — and any abstraction with
   only one adapter and no second in sight.
5. **Bidirectional AC coverage.** Every AC in `01-requirements.md` maps to a public surface in
   `02`; every surface in `02` traces back to an AC. A surface with no AC behind it is
   speculative generality — report it as scope creep.
6. **Test-plan adequacy.** Would the inventory in `04-test-plan.md` actually kill plausible
   bugs, or only demonstrate the happy path? Name plausible defects and confirm a planned test
   catches each. Check that every boundary in the inventory has a test; that a network boundary
   has its transport-level fault test; and that the mutation kill-rate is 80% or carries a real
   justification for deviating (an unargued number is a finding).
7. **Coherence across `02` / `03` / `04`.** Does the internal design actually implement the
   interface as stated? Does the test plan test *that* interface, or a different one?
8. **Fit with the repo.** Does the design follow existing patterns, naming, and module
   boundaries in `<code_root>/`, or introduce a parallel way of doing something already done?

## Declined to judge
Before your verdict, list every concern you considered and set aside as outside the
requirements — one line each, with the reason. The conductor rules on each line; nothing you
set aside is dropped silently. An empty list means you set nothing aside.

## Constraints — read and probe, never design
- **Do NOT write an alternative design, and do NOT implement anything.** You are not a second
  designer; you report on the one in front of you. Proposing a concrete fix for a specific
  finding is in scope; rewriting the design is not.
- You may run **tiny read-only probes** (a few lines to answer one question, e.g. "does this
  library actually expose that signature?"), and you may read the repo freely.
- Your `disallowedTools: Write, Edit` is **documentation-only**: because you hold `Bash`, a
  `cat > file` heredoc could still write. The **guard hook enforces** the real rule — you may
  write only your `handoff/` findings outbox and probes in a scratch/temp dir. Any write into
  the product tree (`<code_root>`/`<tests_root>`) or into the drafts you are reviewing is denied.

## Return / write
Write `<artifact_dir>/handoff/05-design-review-findings.md` with a **verdict** (`APPROVE` or
`CHANGES-REQUESTED`) and specific, actionable findings. Each finding carries:
- **severity** — `Critical` (the design cannot proceed: a leak, an unobservable AC, a missing
  boundary) · `Important` (should be fixed before tests are written) · `Minor` (note it; it
  must not consume a revision round);
- **the file and section** it lands in (`02` / `03` / `04`);
- **what is wrong, why it matters, and the smallest change that fixes it.**

Lead with the leakage verdict — state it explicitly even when clean ("No algorithm leakage
detected in 02: checked X, Y, Z"), because a silent pass is indistinguishable from an unrun
check.
```

**Guard-hook change this requires.** Per CLAUDE.md ("changing what an agent may read/write →
update both the agent's prose inbox **and** `guard.py`"), the `design-reviewer` needs the same
write-confinement the `test-reviewer` has: writes allowed only to its `handoff/` outbox plus a
scratch dir. Two notes:

- The reviewer **must** be able to read `03-design-internal.md` — it cannot check leakage
  otherwise. The existing algorithm-blind denial is keyed to `test-writer` only, so no change
  is needed there; just confirm the new `agent_type` is not caught by it.
- It **must** be able to read `handoff/draft/`, which the current guard denies to *any*
  subagent ("draft-confinement"). **This is a genuine conflict** — see §5.

---

## 3. Template deltas

### 3.1 `design-interface-template.md` — add two sections

Insert after **Public surface**:

```markdown
## Seams (where tests will observe this)
The **seam** is the public boundary a test observes behaviour at, without reaching inside.
Name each one, and justify its height.

| Seam | Existing or new? | Why this height |
|---|---|---|
| … | … | … |

Rules: prefer an **existing** seam to a new one. Use the **highest** seam that can observe the
behaviour. Fewer seams is better — one is ideal. A new seam needs a stated reason.

## Depth check
Answer each in one line. These are the bar the design-review gate applies.
- **Deletion test** — if this module were deleted, does complexity vanish (pass-through, bad)
  or reappear across N callers (earning its keep, good)?
- **Interface vs implementation** — is the surface materially smaller than what sits behind it?
  If they are comparable, the module is shallow: can methods be removed, params simplified, or
  more hidden inside?
- **Adapters** — does anything actually vary across this seam today? One adapter is a
  hypothetical seam; two is a real one.
- **Test surface** — could every acceptance criterion be observed here, without reaching past
  the interface? If not, the seam or the shape is wrong.
```

Insert before **Traceability**:

```markdown
## Assumptions
What this design assumes about the existing codebase, conventions, library behaviour, or the
environment — each one the human can correct now rather than discover at CODE-REVIEW.
Write "None beyond the requirements" if there genuinely are none.
- …
```

And tighten **Traceability** to be bidirectional:

```markdown
## Traceability (both directions)
- **Every AC → a surface.** Each acceptance criterion in `01-requirements.md` and the public
  surface that satisfies it. An AC with no surface is a gap.
- **Every surface → an AC.** Each public surface and the AC it exists for. A surface with no AC
  is speculative — delete it or justify it here.
```

### 3.2 `test-plan-template.md` — add a seam column and a Review Focus section

Change the inventory table header to carry the seam:

```markdown
| ID | Level (unit/api/e2e) | Seam | What it asserts | Traces to (AC# / boundary) |
|----|----------------------|------|-----------------|----------------------------|
| T1 | unit | <seam from 02-design-interface.md> | … | AC1 |
```

Every seam named here must appear in `02-design-interface.md`'s Seams table. A test at an
unnamed seam is a finding at DESIGN-REVIEW.

Add after **Mutation target**:

```markdown
## Review focus — what the requirements did not say
The requirements are a contract, not an exhaustive enumeration of every input this feature will
meet. List the **input classes or failure modes the requirements imply but no test above
exercises**, most likely to bite a real caller first — one line each, naming the input or
condition and the behaviour a reasonable caller would expect.

Then **add the test that pins each one** to the inventory above. An empty list means you looked
and found none, not that you skipped the check.

1. …
2. …
```

### 3.3 `design-internal-template.md`

No structural change proposed. One line worth adding at the top, next to the existing
withheld-from-test-writer note:

```markdown
> Nothing in this file may be paraphrased into `02-design-interface.md`. The DESIGN-REVIEW gate
> checks this explicitly; a leak voids the test-writer's algorithm-blindness.
```

---

## 4. `SKILL.md` changes

### 4.1 Gate 2 — three additions

1. **Read the repo first.** Before authoring, inspect `<code_root>/` for existing patterns,
   seams, naming, and any ADRs or conventions in the area being touched. The design follows the
   repo's conventions unless `01-requirements.md` says otherwise.
2. **Self-review before presenting** (inline checklist, no dispatch):
   - *Placeholder scan* — no "TBD", no "handle edge cases", no section left as a template stub.
   - *Ambiguity check* — could any statement be read two ways? Pick one and make it explicit.
   - *Traceability* — run the bidirectional check both directions; fix gaps inline.
   - *Leakage self-check* — re-read `02` alone and ask whether it reveals `03`.
3. **Do not narrate the design's merits at hand-off.** The DESIGN-REVIEW gate receives the
   contract and the artifact only (see 4.2). Save the rationale for the human at approval.

### 4.2 New Gate 2.5 — DESIGN-REVIEW `[I]` `design-reviewer`

Slots between Gate 2 (author drafts) and Gate 2's promotion step — i.e. the design is reviewed
**as drafts**, and only promoted after the human approves. Sketch:

> ## Gate 2.5 — DESIGN-REVIEW  [I] `design-reviewer`
>
> An **independent** critic reviews the design **before** any tests or code exist. Spawn
> `subagent_type: sdlc-lite:design-reviewer` (dated Opus pin per the model plan; pinned in
> `agents/design-reviewer.md`). Dispatch **bare** — never name a model inline (#22/#36).
>
> **Its brief contains only:** the absolute `<artifact_dir>`, `<code_root>`, `<tests_root>`; its
> inbox (`01-requirements.md` promoted, plus `draft/02`, `draft/03`, `draft/04`); and the
> standards path. **Do not include your rationale for the design** — the reviewer gets the
> contract and the artifact, nothing else. Handing it your conclusion biases it toward
> agreement.
>
> It writes `<artifact_dir>/handoff/05-design-review-findings.md` with a verdict:
> - **CHANGES-REQUESTED → bounded loop:** revise the drafts addressing `Critical` and
>   `Important` findings, then re-review. **Bound to 2 rounds**; `Minor` findings never enter
>   the loop — carry them to the human at approval. After 2 rounds with no progress, STOP and
>   surface to the human with a written ruling per open finding.
> - **APPROVE →** append the run-log entry and proceed to the human approval step.
>
> **The human approves after seeing the findings, not before.** Present
> `05-design-review-findings.md` alongside the three drafts — the findings are what guides the
> eye (the same discipline as Gate 8). Promotion happens only on human APPROVED, atomically,
> as today.

### 4.3 Gate 0 model plan — one new row

| Gate | Runs as | Model / effort | Why |
|---|---|---|---|
| DESIGN-REVIEW | `[I]` `design-reviewer` | **`claude-opus-4-8`** (pinned), medium | review > the thing reviewed |

This strengthens the Gate 0 clean-path summary line: reviews now read
"test / design / code reviews on `claude-opus-4-8` (pinned)."

### 4.4 Rules section — one addition

> - The design is reviewed before the tests are written; the reviewer sees the contract and the
>   artifact, never the author's rationale.

---

## 5. The one real conflict — draft-confinement

The guard currently denies **any subagent** reading under `handoff/draft/` ("unapproved drafts
never reach an isolated gate"). The design reviewer's entire purpose is to review unapproved
drafts. Three ways out:

| Option | How | Trade-off |
|---|---|---|
| **A. Narrow the rule** | Deny `draft/` to every subagent **except** `design-reviewer`, which may read only `draft/02`, `draft/03`, `draft/04` | Smallest change; keeps the invariant's intent (no *downstream* gate sees drafts) while admitting the one gate whose job is drafts. Guard stays keyed on `agent_type`, as it already is for the other three rules. |
| **B. Review after promotion** | Promote on human approval as today, then review, then loop back and re-promote | Keeps the guard untouched — but inverts the gate's value: the human approves *before* seeing findings, and promotion stops meaning "approved". |
| **C. A third location** | Author to `handoff/review/`, promote from there | Adds a directory and a lifecycle; more moving parts than the problem warrants. |

**Recommendation: A.** The invariant is really "an isolated gate must not act on an unapproved
artifact." The design reviewer does not *act* on the drafts — it reports on them, and its report
is exactly what makes approval meaningful. Restate the invariant that way in the developer guide
and the ADR, and the exception stops being an exception.

---

## 6. What a dry run must show

Beyond "it ran green":

1. **The leakage check fires.** Seed a run whose `02-design-interface.md` deliberately names the
   algorithm. The reviewer must return `Critical` and the loop must catch it. If it passes, the
   gate is theatre.
2. **Minor findings do not consume a revision round.** Confirm the loop bound is spent only on
   `Critical`/`Important`.
3. **The guard actually confines the new agent.** A write attempt into `<code_root>` and into
   `draft/02` must both be denied — and the denial must appear in the audit log.
4. **No doubt theatre.** Across a run where the reviewer surfaced substantive findings, at least
   some were classified actionable. Two rounds of findings with zero actionable is a signal the
   framing is wrong, not that the design was perfect.
5. **The receipt shows the pin.** `05` produced by `claude-opus-4-8`, verified actual-vs-pinned.
6. **Cost.** One more Opus gate per run. Measure it — the argument for the gate is that it
   prevents downstream rework, and `/analyze-run` has the token data to test that claim over a
   few runs.

---

## 7. Suggested commit sequence

Each is independently reviewable, and the first two change no behaviour:

1. **Renumber handoff files** (D1) — mechanical, no behaviour change.
2. **Template rubric** — §3.1, §3.2, §3.3. Takes effect at the next Gate 2; improves the design
   even with no reviewer.
3. **Gate 2 additions** — §4.1. Still no new gate.
4. **The gate itself** — new `agents/design-reviewer.md`, `guard.py` option A, `SKILL.md` §4.2
   and §4.3, plus the ADR restating the draft-confinement invariant.
5. **Dry run** (§6), then developer-guide and user-guide updates.
