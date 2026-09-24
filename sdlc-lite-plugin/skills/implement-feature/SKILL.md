---
name: implement-feature
description: EXPLICIT ENTRY ONLY — run this workflow when, and only when, the user types the /implement-feature slash command. Never invoke it yourself from a natural-language request, however closely the request matches; if a request sounds like this workflow, tell the user to type /implement-feature instead. (What it is, for that reply: an interview-driven, test-first, human-in-the-loop workflow that builds a Python feature through staged human approvals and isolated model-pinned review gates, ending in a committed result.)
---

# implement-feature — the conductor's score

You are the **conductor [C]**: the interactive session that holds the through-line,
talks to the human, and delegates bias-sensitive gates to **isolated subagents [I]**.
Walk the gates **in order**. Announce each gate as you enter it. Never let a
downstream gate see a prior gate's raw transcript — only the **curated handoff files**.

**Hard rule:** never commit before the human has reviewed and approved (Gate 9).

## Roles & the handoff contract

- **[C] conductor** — this session. Human-facing gates + orchestration.
- **[I] isolated subagent** — spawned via the Agent/Task tool as a named agent type,
  fresh context, pinned model/effort, sees ONLY its curated inbox. **Plugin agents are
  namespaced by the plugin name**, so the `subagent_type` is
  `sdlc-lite:test-writer`, `sdlc-lite:test-reviewer`,
  `sdlc-lite:implementer`, `sdlc-lite:verifier`,
  `sdlc-lite:code-reviewer` — never the bare name. (Verified empirically.)
- **Dispatch every `[I]` gate bare — never name a model inline (#22, #36).** Do **not** pass a
  `model` argument on the dispatch. The gate's pinned `model` lives in its `agents/*.md`
  frontmatter and **is honored on a bare dispatch** (verified across real sessions); naming a
  model inline is not only unnecessary, it **breaks the dated reviewer pins** — the inline `model`
  slot accepts only family aliases `{sonnet, opus, haiku, fable}`, so naming a `claude-opus-4-8`
  reviewer inline collapses it to the `opus` alias → the floating `claude-opus-5`, losing the
  exact-version reproducibility the dated pin exists for. Let the frontmatter pin govern; the
  post-run receipt **verifies** the actual resolved model against the pin (a mismatch is a FAIL).
  (`effort` likewise has no dispatch lever; it stays frontmatter-only and is audited, not enforced.)

### Two trees: product code vs process artifacts (P48)

The workflow keeps two things strictly apart:

- **Product** — the source and tests that ship. They live in the **repo's own layout**,
  detected and confirmed at Gate 0: `<code_root>` (e.g. `src/`) and `<tests_root>`
  (e.g. `tests/`). Feature-to-feature isolation is a **git branch** concern (Gate 0 / Gate
  10), not a filesystem one — the code is written in place, in the repo.
- **Process artifacts** — the handoff files and the run-log. They live in a **per-run
  artifact dir**, gitignored, never mixed with shippable code:

  ```
  .implement-feature/                       # gitignored artifact root (repo-level)
    .active-run                             # pointer + single-run lock (Gate 0 → Gate 10)
    <NN-slug-YYYYMMDDHHMM>/                 # <artifact_dir>: one per run
      handoff/
        draft/                              # unapproved drafts (Gates 1,2,9); never read by a subagent
        01-requirements.md … 08-code-review-findings.md
        run-log.jsonl                       # the audit/orchestration log for this run
  ```

Pass the absolute **`<artifact_dir>`**, **`<code_root>`**, and **`<tests_root>`** in every
subagent brief so each agent can resolve its inbox/outbox paths.

### Handoff files — numbered by human read-order (P50)

Each handoff doc is prefixed with its **read-order number** so `handoff/` is
self-documenting (browse it top-to-bottom to replay the run). Numbers are the read
sequence, **not** the gate number (IMPLEMENT produces no doc), and are **stable under
loops** — a re-review overwrites its numbered file, never mints a new one.

| # | File | Produced at |
|---|---|---|
| `01-requirements.md` | Gate 1 INTERVIEW |
| `02-design-interface.md` | Gate 2 DESIGN |
| `03-design-internal.md` | Gate 2 DESIGN |
| `04-test-plan.md` | Gate 2 DESIGN |
| `05-test-intent.md` | Gate 3 WRITE-TESTS |
| `06-test-review-findings.md` | Gate 4 TEST-REVIEW |
| `07-verify-report.md` | Gate 6 VERIFY |
| `08-code-review-findings.md` | Gate 7 CODE-REVIEW |

`run-log.jsonl` stays **unnumbered** — it is the audit log spanning all gates, not part of
the read-through narrative.

**Each gate reads a curated inbox, writes a defined outbox:**

| Gate | Reads (inbox) | Writes (outbox) |
|---|---|---|
| WRITE-TESTS [I] | `01-requirements.md` + `02-design-interface.md` + `04-test-plan.md` (**never** `03-design-internal.md`) | `<tests_root>/…` + `05-test-intent.md` |
| TEST-REVIEW [I] | `01-requirements.md` + full design + tests + `05-test-intent.md` | `06-test-review-findings.md` |
| IMPLEMENT [I] | `01-requirements.md` + tests + full design | `<code_root>/…` |
| VERIFY [I] | `01-requirements.md` (ACs + boundary inventory) + `<code_root>/` | `07-verify-report.md` |
| CODE-REVIEW [I] | `01-requirements.md` + full design + whole diff | `08-code-review-findings.md` |

The interface/internal design split (Gate 2) keeps the test-writer blind to the
algorithm. **Never hand `03-design-internal.md` to the test-writer.**

## Quality standards (single source of truth)

The toolchain, the Definition of "green", the coverage/mutation gates, and the
concurrency policy live in **`references/quality-standards.md`** (in this skill's
folder). Pass its **absolute path** to every subagent brief so each gate applies the same
standard. This workflow is **prescriptive about the dev container** — it assumes the
pinned toolchain from `toolchain/requirements-dev.txt` is installed.

> **Reference-file read tax (P53).** The skill's bundled `references/*.md` live in the
> plugin install dir, *outside* the session's working dir, so Claude Code's default
> permissions prompt "read outside working directories" the first time the conductor or a
> subagent opens one. The fix is a one-time `permissions.allow` rule granting reads under
> the plugin dir — a real user adds it at install (see the sdlc-lite README), and our dry-run
> fixture ships it in `.claude/settings.json`. Load-bearing content (the Gate 0 preflight
> command) is kept **inline** here so the hot path needs no such read at all.

## Observability & guardrails (enforced automatically)

Two records, plus a hard guard, run alongside every gate:

1. **Gate run-log (conductor-written).** Append one line to
   `<artifact_dir>/handoff/run-log.jsonl` as each gate completes:
   `{gate, mode, agent, inbox:[...], outbox:[...], result, ts}` — the orchestration story.
   **Do not write `model`/`effort` for an `[I]` gate** — a subagent's *resolved* model/effort
   is unobservable to the conductor, so a written value would be a guess. The receipt sources
   the **requested** model/effort from the agent-def pins (`agents/*.md`) and the **actual**
   from the transcript; the run-log is not a model source. A `[C]` gate *may* add its own
   observed `model` (the conductor runs it, so it knows) — never a guess.
2. **Guard hook audit (automatic).** The plugin ships a **PreToolUse hook**
   (`hooks/hooks.json` → `hooks/scripts/guard.py`) that fires for the conductor **and
   every subagent**, appending `{ts, agent_type, agent_id, tool, target}` for every
   Read/Bash/Grep/Glob — a tamper-evident record of exactly what each agent read. The
   hook finds the run-log via the `.active-run` pointer the conductor writes at Gate 0.
3. **Guard hook enforcement (automatic, verified).** The same hook **denies**:
   - reading `.env` / keys / credentials / ssh keys — for **any** agent (security
     guardrail; path-aware + tool-split so a benign Bash command isn't false-denied);
   - reading `03-design-internal.md` — for the **test-writer** only (algorithm-blind), Read
     *and* Bash;
   - reading anything under `handoff/draft/` — for **any subagent** (unapproved drafts
     never reach an isolated gate);
   - Edit/Write to any **test file** — for the **implementer** only (test-integrity: it
     must pass the tests, not change them); and
   - any write outside its `handoff/` outbox + a scratch dir — for the **test-reviewer**
     (it must not mutate the product tree / build a reference implementation).
   Each is defense-in-depth with the agents' own role instructions. (The guard does **not**
   model-enforce a dispatch: pinned gates dispatch bare and the honored frontmatter pin governs;
   the receipt verifies the actual model after the fact — #22/#36.)

The deterministic analyzer reads the hook audit (stable source of reads) and cross-checks
the session transcript for per-agent **model + token** figures. See the project's
**Developer Guide** (`dev-docs/developer-guide.md` → the guard hook, the analyzer, and the
isolation ADR) for the validation of all of the above.

---

## Output style — every human-facing STOP summary

Render gate summaries **concise but readable, drawing focus to deviations.** The human is
skimming for the one thing that needs a decision — do not bury it in boilerplate.

- **Status glyph leads each line:** **✅** all-good · **⚠️** a deviation the human must decide
  on · **🔴** a hard-fail that STOPs the run.
- **The happy path is terse — one line per fact.** A clean check is a single line; **expand
  only what deviates.** A ⚠️/🔴 earns its detail *and its remedy* (what to do about it);
  everything green stays a one-liner.
- **Never print boilerplate that is identical every run** (e.g. the full 8-row model-plan
  table) unless a deviation makes it worth reading. Collapse it to one line when clean;
  expand it only to show the offending row.
- **State a deviation once.** Carry the ⚠️ + its remedy on the headline line for that fact;
  don't repeat the same warning in a second place.

Gate 0 below is the first application of this style; later STOP gates follow the same rules.

---

## Gate 0 — CLASSIFY + MODEL PLAN + PREFLIGHT  [C] ↔ human

0. **Single-run lock (first action).** Check for `$CLAUDE_PROJECT_DIR/.implement-feature/.active-run`.
   **If it exists, STOP** — a run is already in flight (or was interrupted mid-COMMIT).
   Tell the human its contents (the active `<artifact_dir>`) and ask them to finish or
   abandon that run before starting a new one. (There is no in-workflow resume yet; a
   stale lock is removed by hand.)
1. **Preflight (hard-fail).** Run this **inline** tool check against the target repo's active
   Python environment — the command is reproduced here on purpose so you do **not** open
   `references/quality-standards.md` just to run it (that read trips the "read outside
   working directories" prompt — the reference-file read tax, P53):
   `ruff --version && mypy --version && pytest --version && python -c "import
   importlib.metadata as m; print('mutmut', m.version('mutmut'))"`. **Note:** mutmut is
   version-checked via package metadata, **not** `mutmut --version` — mutmut eagerly loads
   its config on *any* invocation and hard-fails outside a project with a discoverable
   source layout, so `mutmut --version` would false-fail the preflight. **If any tool is
   missing, STOP** and tell the human to install the pinned toolchain
   (`toolchain/requirements-dev.txt`) into this repo's active Python environment — see the
   sdlc-lite README. Do not proceed.
2. Restate the feature in **one sentence**. Confirm the stack is **Python** (this
   workflow targets Python).
3. **Detect the code layout, human confirms.** Inspect `pyproject.toml` / `setup.cfg`,
   the package dir, and `tests/` to propose `<code_root>` and `<tests_root>`. Present them;
   the human confirms or corrects. Record both in the run-log.

   Then **verify the project package is importable (hard-fail).** Determine the top-level
   import package (the dir with `__init__.py` under `<code_root>`, or the `[project].name` /
   `tool.setuptools.packages` mapping) and run `python -c "import <pkg>"`. **If it raises
   `ModuleNotFoundError`, STOP** — a **src-layout** package that was never installed isn't on
   `sys.path`, so the suite would go *falsely* red at Gate 3 and could **never** reach green
   no matter what the implementer writes (a broken harness, not a TDD red). Render the 🔴
   terminal template and do not proceed:
   > 🔴 **`<pkg>` is not importable** — a src-layout package that isn't installed. Run
   > `pip install -e .` in the repo root, then re-run `/implement-feature`. Stopping.

   **Do not install it yourself** — the human owns their environment (the "no workarounds"
   bar; installing your own package editable is *their* one-time setup, not the plugin's).
4. **Create the run's artifact dir + lock.** Derive a run id `<NN-slug-YYYYMMDDHHMM>`:
   `NN` = GitHub issue # (`00` if none), `slug` = a short kebab slug from the feature,
   timestamp = now. Then, **in this order**:
   - `mkdir -p .implement-feature/<run>/handoff/draft`;
   - write `.implement-feature/.active-run` containing the absolute `<artifact_dir>`
     (this is both the guard's run-log pointer **and** the single-run lock);
   - ensure the repo `.gitignore` ignores **both** `.implement-feature/` **and**
     `if-runlog.jsonl` (append whichever is missing; create `.gitignore` if absent).
     Process artifacts must never be committed — `if-runlog.jsonl` is the guard's fallback
     audit file, written to the repo root before this workdir exists and after the lock is
     cleared (the pointer only routes to `handoff/run-log.jsonl` while `.active-run` lives).
5. **Per-gate model/effort plan (canonical).** The invariant: **design and every review use
   a higher model than implementation.** Effort is uniform (`medium`) across every gate —
   real-world config differentiates on model, not effort (#35). This is the reference plan
   — you render it per the display rule in step 8, not verbatim.

   | Gate | Runs as | Model / effort | Why |
   |---|---|---|---|
   | INTERVIEW | [C] | Opus (session), medium | requirements reasoning = strong model |
   | DESIGN / SPEC | [C] | Opus (session), medium | design = strong model |
   | WRITE-TESTS | [I] `test-writer` | `sonnet` alias, medium | writing tests = implementation |
   | TEST-REVIEW | [I] `test-reviewer` | **`claude-opus-4-8`** (pinned), medium | review > implementation |
   | IMPLEMENT | [I] `implementer` | `sonnet` alias, medium | implementation |
   | VERIFY | [I] `verifier` | `sonnet` alias, medium | verification |
   | CODE-REVIEW | [I] `code-reviewer` | **`claude-opus-4-8`** (pinned), medium | review > implementation |
   | REVIEW-GUIDE / COMMIT | [C] | Sonnet or Haiku (session) | mechanical presentation + commit |

   The `[I]` subagent models are pinned in `agents/*.md`, in two different ways: the two
   **reviewers** (`test-reviewer`, `code-reviewer`) pin the **explicit, dated** `claude-opus-4-8`
   — on purpose, for **reproducible review behavior** (a floating alias would silently change the
   reviewer as new Opus tiers ship); `test-writer` / `implementer` / `verifier` pin the **`sonnet`
   alias** (whatever the latest Sonnet tier is). Both are **dispatched bare** so the frontmatter
   pin — including the dated one — is honored (#36). The pin is **verified** (#22): the post-run
   receipt compares the transcript's *actual* model against the pin — a mismatch is a **FAIL**.
   (Effort has no dispatch lever, so it is verified only — a deviation is a WARN, not enforced.)
   **Conductor `[C]` gates run on the
   session's own model** (the plugin cannot pin it), so
   only the three `[C]` rows can be wrong — and only when the session's tier is *below* that
   row's required tier (INTERVIEW/DESIGN want Opus; REVIEW-GUIDE/COMMIT is *correct* on
   Sonnet/Haiku).

6. **Conductor model self-check (P56) — the single deviation notice.** A plugin cannot set
   the conductor's own model. **Detect the model you are running as** and compare it to the
   `[C]` rows. This check owns the model-deviation warning (do not repeat it elsewhere):
   - **Opus-tier** → the ✅ conductor line in the render.
   - **Below Opus-tier** → the ⚠️ conductor line: name the model, state that INTERVIEW/DESIGN
     will run below design-grade strength (DESIGN no stronger than the `implementer`), and
     give the remedy `claude --model opus`. This same condition is what **expands** the model
     table in step 8. Record the actual conductor model in the run-log either way.

7. **Branch decision (never commit on the default branch — P52).** Detect the current branch
   (`git rev-parse --abbrev-ref HEAD`) and the repo's default branch (e.g. `main`/`master`),
   **assess scope**, and decide:
   - **trivial** change *and* not on the default → stay on the current branch;
   - **non-trivial** change → new feature branch `feature/<NN-slug>` (run slug minus the
     timestamp, so branch↔artifacts correspond);
   - **HEAD is the default branch → a new branch is REQUIRED** regardless of triviality
     (**hard invariant**). The human may override the *triviality* call, never this rule.

   On "new branch", the conductor runs `git switch -c feature/<NN-slug>` (or `git checkout
   -b`) and records the branch in the run-log; the commit later lands there (Gate 10). The
   render (step 8) shows the working branch on one line, and a **terse reason only when the
   choice is forced/atypical** (e.g. new branch because HEAD is the default) — no rationale
   on the ordinary case.

8. **Render the Gate 0 summary** per the two templates below. Follow the Output-style rules:
   glyph-led, terse on the happy path, expand only deviations.

   **(a) Preflight failed → terminal render (nothing else prints; the run STOPs):**
   > 🔴 **Preflight failed — `<tool>` not found.** Install the pinned toolchain
   > (`toolchain/requirements-dev.txt`) into this repo's active Python environment — see the
   > sdlc-lite README (https://github.com/Sdaas/sdlc-lite) — then re-run. Stopping.

   **(b) Preflight passed → full Gate 0 summary:**
   > ✅ **Preflight passed** — ruff `<v>`, mypy `<v>`, pytest `<v>`, mutmut `<v>`. No
   > active-run lock.
   >
   > **Gate 0 — layout · model · branch**
   > - **Feature:** `<one-sentence restatement>`
   > - **Code root:** `<code_root>`  ·  **Test root:** `<tests_root>`
   > - `<conductor line>` — ✅ `Conductor model: <model> (Opus-tier) — design/interview at
   >   full strength.` **or** ⚠️ `Conductor model: <model> — INTERVIEW & DESIGN will run below
   >   design-grade (no stronger than the implementer). Relaunch with `claude --model opus`,
   >   or proceed as-is.`
   > - **Branch:** `<working-branch>` `<(new — <reason>) only if forced/atypical>`
   > - `<model-plan line>` — **when the conductor is Opus-tier (clean):** ✅ `Model plan:
   >   reviews on claude-opus-4-8 (pinned) · impl/tests/verify on Sonnet · design/interview on
   >   this Opus session.` **when the conductor is below Opus-tier:** print the full table
   >   instead, showing the *actual* conductor model on the three `[C]` rows and a `⚠️` marker
   >   on the INTERVIEW & DESIGN rows only (no second remedy — it's on the conductor line). The
   >   two reviewer rows always read `claude-opus-4-8` (pinned), never the `opus` alias.
   >
   > **STOP — confirm layout, model plan, and branch before I begin.**

**STOP. Do not begin any work until the human confirms the code layout, the model plan,
and the branch decision.** Record the confirmed plan (with `<code_root>`, `<tests_root>`,
`<artifact_dir>`, and the working branch) into `<artifact_dir>/handoff/run-log.jsonl`
(first entries).

---

## Gate 1 — INTERVIEW  [C] ↔ human

Interview to full clarity using a **grilling** approach. Do NOT guess scope.

**Anchor the scope FIRST — smallest viable (P57).** Grilling reaches *clarity*, not *maximal
scope*; left unchecked its completeness bias enumerates every format/mode/option and the
feature balloons. So before working the frontier: propose a **one-paragraph minimal version**
(the smallest thing that satisfies the core request) and an explicit **deferred / out-of-scope
list**, and get the human to **confirm the scope boundary**. Then grill only *within* that
boundary — each extra format/mode/option is an **explicit scope decision the human opts into**,
never an assumption you resolve toward "more." Your recommended answers (`➡️`) **default to the
smaller option**. (Dry run: a "minimal `parse_duration`" grew into a 3-format parser because the
interview maximized instead of anchoring.)

**Method (design tree, worked in rounds):**
- Map the feature as a tree of decisions. Each round, ask the whole **frontier** —
  every question whose prerequisites are already settled.
- Format each question numbered, with **your recommended answer**:
  ```
  ❓ **Q1** — **<title>**: <question, incl. options>
  ➡️ <your recommended answer>
  ```
- **Facts are your job; decisions are the human's.** If a question needs a fact from the
  environment (existing code, conventions, deps), dispatch a subagent to find it — don't
  ask the human what you can look up. A running lookup is an unsettled prerequisite: ask
  the rest of the frontier now, defer the questions downstream of it.
- Each answer reshapes the tree; recompute the frontier and ask the next round. Done when
  the frontier is empty — **nothing silently assumed**.

**You must reach explicit answers for all four buckets** (see
`references/requirements-template.md`):
1. **Functional ACs** — inputs/outputs, behavior, error conditions, edge cases.
2. **Non-functional ACs** — scale, performance, security (write "N/A — reason" if none).
3. **Constraints** — mandated/forbidden tech, libraries, patterns, style.
4. **Boundary inventory** — external boundaries (network/subprocess/fs/entrypoint/dep),
   each with how it will be exercised un-mocked at VERIFY. "None (pure feature)" is valid.

**Close the gate (review the real artifact, then promote — P47):**
- Author the requirements to a **draft**: `<artifact_dir>/handoff/draft/01-requirements.md`
  (template `references/requirements-template.md`) so the human reviews the **real file**,
  not a summary. Present its path and a short orientation.
- **Bounded review/revise loop:** the human may hand-edit the draft directly and/or ask
  you to revise. After each round **re-read the draft from disk** (hand-edits win). Bound
  to ~3 rounds, then STOP-and-ask.
- **STOP. Do not promote or proceed until the human replies APPROVED.**
- On approval, **promote** (move) the draft to `<artifact_dir>/handoff/01-requirements.md`.
  Downstream gates only ever read `handoff/`, never `handoff/draft/`. Append the run-log entry.

## Gate 2 — DESIGN / SPEC  [C] ↔ human

Read `<artifact_dir>/handoff/01-requirements.md`. Decide the solution's shape and author
**three** draft handoff files under `<artifact_dir>/handoff/draft/` (templates in
`references/`).

**The interface / internal split (the mechanism that keeps the test-writer blind, P15):**
- `draft/02-design-interface.md` — the **public contract only** (signatures, types, I/O,
  observable error/edge behavior, invariants). **Shared** with the test-writer. Template:
  `references/design-interface-template.md`.
- `draft/03-design-internal.md` — the **algorithm**, data structures, alternatives,
  complexity, quality expectations, risks. **Withheld** from the test-writer; seen by
  implementer + reviewers. Template: `references/design-internal-template.md`.
  **Rule: nothing that reveals the algorithm may leak into `02-design-interface.md`.**

**The test plan** (`draft/04-test-plan.md`, template `references/test-plan-template.md`) —
consumed by test-writer, test-reviewer, and code-reviewer:
- Enumerated tests (**unit / api / e2e**), each traced to an **AC or a boundary**;
  cover happy path, edges, negatives, and every boundary in the inventory.
- **Coverage threshold** and **mutation kill-rate threshold** (the numbers Gate 7
  enforces via `pytest-cov` / `mutmut`). **Anchor the mutation kill-rate at 80%** (P46) —
  start there and **justify any deviation in the plan**; do not free-pick. **Surface the
  chosen threshold + justification prominently at approval** so the human can veto it.
- If `01-requirements.md`'s boundary inventory flags the feature concurrent/async, the plan
  MUST include the property/stress/async tests + concurrency review focus (per
  `references/quality-standards.md`); otherwise state "No concurrency surface — skipped."

**Close the gate (review the real artifacts, then promote atomically — P47):**
- Present the approach + alternatives considered, and point the human at the **three real
  draft files** to read (not a summary). (For a complex feature, optionally spawn a fresh
  design-review subagent first.)
- **Bounded review/revise loop**, same as Gate 1: the human hand-edits and/or asks you to
  revise; re-read the drafts from disk each round; bound to ~3 rounds then STOP-and-ask.
  The design split is reviewed and approved **atomically** — interface + internal + plan
  are promoted together on one approval (never a partial/interface-only approval).
- **STOP. Do not promote the handoff files or proceed until the human replies APPROVED.**
- On approval, **promote** all three drafts into `<artifact_dir>/handoff/` and append the
  run-log entry.

## Gate 3 — WRITE-TESTS  [I] `test-writer`

Delegate to the isolated, **algorithm-blind** test-writer. Do NOT write the tests
yourself, and do NOT coach it on the algorithm.

**Spawn it** via the Agent tool with `subagent_type: sdlc-lite:test-writer`
(namespaced by plugin; its model/effort/tools are pinned in `agents/test-writer.md`). The
brief you pass must contain ONLY:
- the absolute `<artifact_dir>`, `<code_root>`, and `<tests_root>`;
- its inbox — read **`01-requirements.md` + `02-design-interface.md` + `04-test-plan.md`**
  (under `<artifact_dir>/handoff/`) and the standards file
  (`references/quality-standards.md`, by the path you resolve);
- the hard rule: **do NOT read `03-design-internal.md` or `<code_root>/`** — encode the
  contract, not an implementation;
- the task: implement the `04-test-plan.md` inventory under `<tests_root>/`, write
  `<artifact_dir>/handoff/05-test-intent.md`, and confirm the suite is red.

**Exit condition (machine, not human):** the returned report must show the suite is
**RED for the right reason** — tests exist and fail because the implementation is *absent*
(a genuine red looks like `ImportError: cannot import name '<symbol>'`, `AttributeError`,
or a plain assertion failure — the package imports, the *symbol* is missing). **Not** every
red counts; two wrong-reason cases are distinct:
- a bad import path / typo / syntax error **inside the tests** → the writer's fault →
  **re-spawn** the writer with the correction;
- **`ModuleNotFoundError: No module named '<project-pkg>'`** → an **environment/setup
  failure, not writer-correctable.** The project package isn't installed, so the suite stays
  red no matter what the implementer writes — re-spawning the writer cannot fix it. **STOP,
  do not proceed:** this means the Gate 0 importability preflight was skipped or the env
  changed mid-run; have the human `pip install -e .` and re-enter the gate.

When genuinely red, append the run-log entry and proceed.

*(This gate is re-entered from Gate 4 on CHANGES-REQUESTED — re-spawn the writer with the
findings file added to its inbox.)*

## Gate 4 — TEST-REVIEW  [I] `test-reviewer`

An **independent** critic reviews the tests **before** any implementation exists. Spawn a
**different** agent than the writer — `subagent_type: sdlc-lite:test-reviewer`
(Opus/medium per the model plan; pinned in `agents/test-reviewer.md`).

**Its inbox (it sees more than the writer):** `01-requirements.md`, the **full** design
(`02-design-interface.md` **and** `03-design-internal.md`), `04-test-plan.md`, the tests,
and `05-test-intent.md`. (Only the *writer* is algorithm-blind; the reviewer is not.)

**It must judge:**
- **Intent match** — does each test assert the requirement, or only a proxy?
- **Non-tautology** — *would a wrong implementation still pass?* Do a mutation-minded
  analysis: name plausible bugs and confirm a test kills each.
- **Coverage** — every acceptance criterion and every boundary in the inventory, per the
  test plan (incl. the mutation cases behind the kill-rate target).
- **No implementation leakage** — tests encode the contract, not one algorithm.

**Analytical review only — no reference implementation (P45).** Gate 4 is a *reasoning*
pass: the reviewer names plausible bugs and argues a test kills each; it may write **tiny
throwaway probes** but must **not** build a reference implementation or run `mutmut`.
Empirical mutation is implementation-specific, so it belongs at **Gate 7 CODE-REVIEW**,
against the real shipped code. The guard confines the reviewer's writes to its outbox +
a scratch dir (a Bash-holding critic can't be made read-only by tool-removal alone, P44).

It writes `<artifact_dir>/handoff/06-test-review-findings.md` with a **verdict**:
- **CHANGES-REQUESTED → bounded loop:** re-spawn `sdlc-lite:test-writer` with the
  findings file added to its inbox; then re-review. **Bound it:** after 2 rounds with no
  progress, STOP and surface to the human.
- **APPROVE →** append the run-log entry and proceed.

The reviewer does **not** edit the tests (read-only) — it only reports; the writer makes
the changes on the next loop.

## Gate 5 — IMPLEMENT  [I] `implementer`  (inner loop)

Delegate to `subagent_type: sdlc-lite:implementer` (Sonnet/medium; has
Write/Edit/Bash, pinned in `agents/implementer.md`). Its inbox is `01-requirements.md` +
the **tests** + the **full** design (`02-design-interface.md` + `03-design-internal.md`) +
the standards file.

**Inner loop (machine condition, no human):**
1. Write the **minimum** implementation under `<code_root>/` per the design; honor the
   constraints in `01-requirements.md`.
2. Run the **fast checks** until all pass — **"green" = `pytest` passes AND `ruff` clean
   AND `mypy` clean** (per `references/quality-standards.md`).
3. Refactor while keeping green.

**Load-bearing rule: make the code pass the tests — NEVER weaken or edit the tests to
pass.** The tests are the approved, independently-reviewed contract (Gates 3–4). Enforced
in depth: (a) the **guard hook denies the implementer any Edit/Write to a test file**
(keyed on `agent_type`, same mechanism as the algorithm-blind rule); (b) this prose rule;
(c) the whole-diff CODE-REVIEW (Gate 7), which flags any change under `<tests_root>/`.

Exit when green; append the run-log entry, then proceed to VERIFY. (Coverage + mutation
are the slow checks, enforced at CODE-REVIEW — not here.)

## Gate 6 — VERIFY  [I] `verifier`  (outer loop)

**Green unit tests are not Done.** Spawn a **fresh, read-only** verifier —
`subagent_type: sdlc-lite:verifier` (Sonnet/medium; observes, cannot fix — pinned in
`agents/verifier.md`). It did not write the code, so it won't drive it the way the author
expects. Its inbox: `01-requirements.md` (the ACs + boundary inventory) and `<code_root>/`
(to invoke the real thing, not to trust it).

**It must:**
1. For **each acceptance criterion**, invoke the **real** public function/flow and confirm
   the **observed** result matches — not just that a test is green.
2. For **every external boundary** in the inventory, exercise it **un-mocked** at least
   once (a mocked test only proved the mock). If the inventory is "None (pure feature)",
   verify on the acceptance examples and say so.
3. If `01-requirements.md` flagged concurrency, run the stress/property checks per
   `references/quality-standards.md`.

It writes `<artifact_dir>/handoff/07-verify-report.md`: per-AC **observed** PASS/FAIL with
the actual value, the boundary drives performed, and an overall verdict.

**This is the OUTER loop.** On any FAIL → go **back to IMPLEMENT (Gate 5)** — re-enter the
inner loop, fix, re-green, then re-VERIFY (bounded; surface to the human if it won't
converge). On all-PASS → append the run-log entry and proceed to CODE-REVIEW.

## Gate 7 — CODE-REVIEW + quality  [I] `code-reviewer`  (the last unattended gate)

Spawn a fresh, read-only whole-diff reviewer —
`subagent_type: sdlc-lite:code-reviewer` (Opus/medium; pinned in
`agents/code-reviewer.md`). "One senior engineer reviewing the entire PR": fresh context
kills anchoring, a stronger model than the implementer kills monoculture. Its inbox:
`01-requirements.md` + the full design + the **whole change** (tests + `<code_root>/`) +
the standards.

**It reviews across six quality dimensions** (borrowed from the `claude-sdlc` profile
backbone — scale each to the feature; state **`N/A — why`**, never silently drop one):
1. **Best practices** — modularity/cohesion, purity/side-effects, naming, typing, docstrings;
   idiomatic Python; the constraints in `01-requirements.md` honored.
2. **Performance & scale** — the measurable signals the design flagged; no accidental
   O(n²)/N+1 or unbounded growth.
3. **Testing pyramid** — the **slow checks** live here (deferred by split-by-speed):
   **coverage** (`pytest --cov=<code_root>`) and **mutation** (`mutmut run` → kill-rate) vs
   the `04-test-plan.md` thresholds. Surviving mutants = weak tests; call out untested lines.
4. **Security** — injection/quoting, secrets, filesystem, dependency surface.
5. **Reliability & resilience** — timeout/retry/backoff/idempotency at every boundary in the
   inventory; concurrency (races/deadlocks/ordering/cancellation) if `01-requirements.md` flagged it.
6. **Observability & logging** — the change is diagnosable (levels, messages) per policy.

Plus two cross-cutting checks: **whole-diff consistency** (no dead/speculative code) and
**test-integrity** (flag **any change under `<tests_root>/`** — the implementer must not have
altered them). Fast checks (`ruff`/`mypy`/unit `pytest`) were gated in IMPLEMENT — confirm they
still pass; spend the effort on the six dimensions + the slow checks.

It writes `<artifact_dir>/handoff/08-code-review-findings.md` with **every finding TYPED with a
repair target**, and a **verdict**:
- **APPROVE →** append the run-log entry and proceed to the human gates (8–10).
- **CHANGES-REQUESTED → route each finding by its type (one review pass, two repair paths — P37):**
  - **`→IMPLEMENT`** — *code* defects (correctness, best-practice, reliability/perf,
    observability wiring, **dead-code deletion**) → back to **IMPLEMENT (Gate 5)**; the
    implementer edits `<code_root>/` only.
  - **`→TESTS`** — *weak/missing tests* (surviving mutants, coverage gaps that are missing
    tests) → back to **WRITE-TESTS (Gate 3)** then **TEST-REVIEW (Gate 4)**. New tests must
    themselves be independently reviewed before re-use — the implementer is **barred** from
    editing tests (guard-hook job #4), so routing a test-weakness to IMPLEMENT is a dead end.
    A surviving mutant that is actually *unreachable-by-requirement code* routes `→IMPLEMENT`
    to delete it instead.

Findings of both types in one round dispatch to both actors. After repair, re-converge forward
(→ VERIFY → CODE-REVIEW). **Bound the loop; surface to the human if it won't converge.**

## Gate 8 — REVIEW-GUIDE  [C]  (Sonnet/Haiku)

Make the human's review fast and focused — **guide the eye; do not dump a diff.** Present:
- the list of **changed files**, with a recommended **review order**;
- **one line per file** — why it matters / where the key change is;
- **pointers to every findings file** under `<artifact_dir>/handoff/`:
  `06-test-review-findings.md`, `07-verify-report.md`, `08-code-review-findings.md`, and
  the audit `run-log.jsonl` (what each agent did, which model, what it read).

The observability from every gate pays off here: the human can drill into any agent's work
rather than re-reviewing everything from scratch.

## Gate 9 — HUMAN REVIEW  [C] ↔ human   (approval gate — the ship decision)

**Pre-approval breach check (informational — P40).** Before asking for approval, run the
analyzer's fast isolation pass over this run and summarize it for the human:
`PYTHONPATH="<plugin_root>" python3 -m analyzer.analyze_run --workdir <artifact_dir> --no-transcript`
(the guard's audit log is complete by now, so the verdicts are final). Report the isolation
verdicts. **If any verdict is a VIOLATION, surface it prominently and require the human's
explicit acknowledgement** before they approve — a breach must not ship silently. The
analyzer **never blocks**; real-time blocking is the guard hook's job and this only confirms
after the fact.

**STOP. Do not commit. Wait for the human to review and reply APPROVED.** If the human
requests changes, route them to the relevant gate (e.g. a logic fix → IMPLEMENT; a missing
test → back through WRITE-TESTS/TEST-REVIEW), then re-run forward and re-present at Gate 8.
The human owns the decision to ship — nothing here is automatic. The same "review the real
artifact" discipline (P47) applies: point the human at the actual files, never only a summary.

## Gate 10 — COMMIT  [C]  (Sonnet/Haiku)

**Only after the human replied APPROVED** (the hard rule from Gate 0): commit the change
with a clear message referencing the feature and its acceptance criteria. This is the
**only** gate that writes to git history. The gitignored `.implement-feature/` artifact dir
is **never** part of the commit.

**Re-check the never-on-default invariant (P52) before committing.** Confirm HEAD is not the
repo's default branch (it should be `feature/<NN-slug>` per the Gate 0 branch decision). **If
HEAD is somehow the default branch, STOP** — do not commit; create/switch to the feature
branch first (the human confirmed this at Gate 0).

**Authorship = the repo's configured git identity (P39).** This plugin ships to other users,
so it **never** hardcodes an author or email. Let `git commit` resolve `user.name` /
`user.email` from the ambient config (repo-local → global) — **do not** pass `--author` and
**do not** run `git config` to set one. If no identity is configured, `git commit` fails:
**STOP and tell the human** to set `user.name`/`user.email` rather than inventing one. For a
`Co-Authored-By:` trailer, **follow the repo's existing convention** (match recent commits if
they use one; otherwise omit it) — never a hardcoded name.

(In a repo with branch/PR conventions: commit on the feature branch, push — the pre-push
hook runs the tests — and open a PR; merge only on green CI + approval.)

Append the final run-log entry. **Then, only after the commit succeeds, clear the lock:**
delete `$CLAUDE_PROJECT_DIR/.implement-feature/.active-run`. (An interrupted COMMIT
correctly still looks active until the commit lands.)

## Gate 11 — REPORT  [C]  (auto, measure-only — P40)

**Auto-run the analyzer** over the just-finished run and present the compliance report — no
manual step. The artifact dir persists (gitignored), so this reads it directly and **saves
the report** next to the handoff dir via `--out`:
`PYTHONPATH="<plugin_root>" python3 -m analyzer.analyze_run --workdir <artifact_dir> --out <artifact_dir>/run-report.md`
(full report incl. the transcript token pass this time; it prints AND persists to
`<artifact_dir>/run-report.md`). Present:
- **Isolation compliance** — the guard's invariants held across all gates.
- **Per-gate model split** — each isolated gate's pinned model + tokens (the evidence for
  "reviews ran on a higher model than implementation").
- **Per-agent activity** + token/cost totals.

The analyzer only **measures** — it never blocks or edits. (Any past run can be re-analyzed
later with the standalone `/sdlc-lite:analyze-run` command.) The pipeline (Gates
0–11) is complete.

---

## Rules
- Curated handoffs only — a gate never sees a prior gate's raw transcript.
- The test-writer is blind to `03-design-internal.md`.
- Design & every review use a higher model than implementation.
- Not Done on green tests alone — VERIFY observed behavior.
- Bound every automated loop; surface to the human on no progress.
- Never ask a human to approve an artifact they have not seen in full (P47).
- Product code lives in the repo; process artifacts live in the gitignored `.implement-feature/`.
- Review before commit; the artifact dir is never committed.
