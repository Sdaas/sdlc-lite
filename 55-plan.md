# 55-plan.md — `/implement-feature` SKILL.md body suppression

_Branch-scoped working plan for **#55** (`fix(skill): a same-named command suppresses the
implement-feature SKILL.md body`), milestone `1.0.0-beta.3`. Checked in on
`55-skill-suppression`; `git rm`'d in the merge/close commit._

## Problem

Under the `--plugin-dir` load path, `Skill(sdlc-lite:implement-feature)` returns only
`Launching skill: sdlc-lite:implement-feature` — the 636-line `SKILL.md` body never enters
context, and the conductor improvises gate prose that *resembles* the real workflow. The plugin
ships two surfaces under the same name:

- `sdlc-lite-plugin/commands/implement-feature.md` — a 12-line shim ("load the skill")
- `sdlc-lite-plugin/skills/implement-feature/SKILL.md` — the real 636-line score

Issue evidence (one load path only): arm-a (as shipped) 0/2; arm-b (shim deleted) 2/2.

**Why it is urgent:** #50 makes `claude plugin eval` — which uses `--plugin-dir` — the T1
verification primitive for the whole plugin. Every eval run against a suppressed body scores a
hallucination. #55 was therefore pulled into `1.0.0-beta.3` **ahead of #50**.

## Locked decisions (2026-09-23)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Fix shape: decided after measurement.** Phase 0 runs to completion and STOPs; no file in `sdlc-lite-plugin/` is touched before the human picks the fix from the matrix. | AC #1 says measure first. The plausible fixes (delete the shim vs. rename the skill dir) trade off differently depending on whether a skill is reachable as a slash command on *all* three paths. |
| 2 | **Schedule: `1.0.0-beta.3`, worked first — ahead of #50.** | #50's premise is that eval results are trustworthy; today they are not. |
| 3 | **Regression check: both layers** — a structural host pytest (command/skill name collision) *and* a behavioral canary in `release-verify.sh`'s smoke. | Neither depends on the early-access `plugin eval` gate. The structural check is free and always-on; the behavioral one catches non-collision ways the body could stop loading. |
| 4 | **This plan file is checked in** on the branch. | Multi-phase with a measurement matrix to track — plan-mode-worthy per `CLAUDE.md`. |

## Constraints

- Measure **all three** load paths before any fix (AC #1).
- Phase 0 runs as **headless probes in the dev container** — `claude plugin eval` is early-access
  gated and Bash-granting eval cases cannot run on this Mac (Docker Desktop symlinks).
- **Out of scope:** renaming or removing the `/implement-feature` entry point users type.
- Never commit before human review and approval.

## The canary

`05-test-intent.md` — the Gate 3 WRITE-TESTS outbox filename. It appears **only** in `SKILL.md`
(line 71/83/84/407), never in the command shim. Its presence in a transcript is a clean
body-loaded signal; its absence is suppression.

## Phases

### Phase 0 — Measure (AC #1) — **STOP at the end**

3 load paths x 2 arms x 2 runs = 12 headless probes, in the dev container.

- **Arms:** `/tmp/arm-a` (plugin as shipped) and `/tmp/arm-b` (`commands/implement-feature.md` deleted).
- **Load paths:** (A) directory marketplace, (B) `--plugin-dir`, (C) installed-from-umbrella
  (clean-room config, as `release-verify.sh` builds it).
- **Probe:** invoke the skill, then ask for the Gate 3 WRITE-TESTS outbox filename.
- **Output:** `dev-docs/findings/2026-09-23-skill-suppression-findings.md` with the filled matrix.

Then STOP and hand the matrix to the human for the fix decision.

### Phase 1 — Fix (AC #2)

Apply the human-chosen fix. Re-run the Phase 0 probe on all three paths, 2/2 expected each.

### Phase 2 — Regression check (AC #3)

1. Host pytest in `sdlc-lite-plugin/tests/` — fails if any `commands/<x>.md` collides with
   `skills/<x>/`. Runs in `python3 -m pytest sdlc-lite-plugin -q`.
2. Behavioral canary step in `release-verify.sh`'s Gate-0 smoke — asserts a `SKILL.md`-only
   string in the transcript.

Both must fail when the fix is reverted.

### Phase 3 — Docs (AC #4)

- Developer Guide 7: revise **"Thin command, heavy skill"** — it currently *recommends* the
  pattern that broke this.
- New ADR: *one name, one surface*, with the Phase 0 matrix as its evidence.
- `analyze-run.md` is unaffected (no same-named skill) — note it explicitly.

### Phase 4 — Verify & close

- `python3 -m pytest sdlc-lite-plugin -q`
- `./release-verify.sh` — Gate 0 reaches `Preflight passed` + the Gate 0 STOP
- File-change list for human review -> approval -> commit -> merge (`git rm 55-plan.md`)

## Success criteria

- [ ] Filled 3x2x2 matrix in `dev-docs/findings/`
- [ ] Post-fix canary present on all three load paths, 2/2 runs each
- [ ] Reverting the fix fails both the pytest and the `release-verify.sh` canary
- [ ] Headless Gate-0 smoke green; `./release-verify.sh` green
- [ ] Naming rule documented as an ADR in the Developer Guide

## Progress

| Phase | State | Notes |
|---|---|---|
| 0 — Measure | **done** 2026-09-23 | 12/12 clean: all 3 paths suppressed in arm-a, loaded in arm-b. Root cause identified (command body injected in place of SKILL.md). See `dev-docs/findings/2026-09-23-skill-suppression-findings.md`. Awaiting fix decision. |
| 1 — Fix | **done** | Shim deleted; `policy.skill_invoke_decision()` + `Skill` in the guard matcher; description defanged. Verified on all 3 paths via the real typed-slash entry point; auto-trigger denied. |
| 2 — Regression check | **done** | `tests/test_entry_points.py` (9 tests, fails when the shim returns — verified both directions); `release-verify.sh` body canary keyed on the expansion signature, plus an install assertion that the shim is absent. No headless escape hatch needed: the typed slash never touches the `Skill` tool. |
| 3 — Docs | **done** | ADR-14 + two rewritten design principles + file-tree fix in the Developer Guide; `CLAUDE.md` rules; findings record corrected after the stream-json measurement artifact was caught. |
| 4 — Verify & close | in progress | Host suite 169 passed. `./release-verify.sh` cannot pass until the fix is released (it verifies the umbrella's beta.2, which still ships the shim) — see the note below. |

## Note on `./release-verify.sh` (Phase 4)

The issue lists it under Verification, but it verifies the **released** plugin from the umbrella
marketplace — today `1.0.0-beta.2`, which still ships the shim. Its new body canary would therefore
(correctly) report `SKILL.md SHADOWED` against that tag. The canary and the install assertion were
validated directly instead:

- the canary's discriminator was measured across five real transcripts — `Base directory for this
  skill` is present in every healthy run and absent in the shadowed one, while
  `already loaded above; instructions unchanged` appears only in the shadowed one;
- a plain grep for the canary string **false-passes** on a shadowed body, because the conductor hunts
  `SKILL.md` down and `Read`s it — which is why the check keys on the expansion signature instead.

Run `./release-verify.sh` end-to-end at the **next release cut**, once the fix is tagged.

---

# RESUME HERE (state as of 2026-09-24)

**Branch:** `55-skill-suppression` · **Issue:** #55 · **Milestone:** `1.0.0-beta.3` (first in the
execution order, ahead of #50).

## Status: the fix is COMPLETE and COMMITTED (`989e6ad`), NOT merged, issue NOT closed.

**One gap is open and must be closed first — step 1 below.** Do not merge or close #55 until it is.

Phases 0-3 are done and verified. What remains is close-out only.

### What was decided and built (do not re-litigate)

1. **Deleted** `sdlc-lite-plugin/commands/implement-feature.md`. A command file whose name matches a
   skill directory shadows the skill on **all three** load paths — measured 12/12. The skill
   registers `/implement-feature` itself, so the entry point users type is unchanged.
2. **Explicit-entry enforcement**, plugin-wide: `policy.skill_invoke_decision()` denies every `Skill`
   tool call in the `sdlc-lite:` namespace; `hooks.json` matches `Skill`. The human's typed slash
   command never makes a `Skill` call (the CLI expands it directly), so it is untouched. Prose half
   in the skill `description`.
3. **Two regression checks:** `sdlc-lite-plugin/tests/test_entry_points.py` (structural, host, free —
   verified to fail when the shim is restored) and a `release-verify.sh` body canary keyed on the
   expansion signature, plus an install assertion that the shim is absent.
4. **Docs:** ADR-14 in the Developer Guide (call sequences + known fragility), two design principles
   rewritten (the old "thin command, heavy skill" is retired), `CLAUDE.md` rules, and the findings
   record.

### Verified

| Check | Result |
|---|---|
| Host suite (`python3 -m pytest sdlc-lite-plugin -q`) | 169 passed |
| Typed `/implement-feature` on all 3 load paths | body loads |
| Auto-trigger from natural phrasing | denied by the guard |
| Shim restored → structural test | fails, as intended |

### Remaining work — do these in order

**1. FIRST: prove the new body canary actually fires (the open gap — do not skip).**

The canary added to `release-verify.sh` has never executed **inside the script**. Its discriminator
was validated by hand against five real transcripts, and the glob pattern was checked against a
different directory — but this line has never run with the real `$VERIFY_CFG` and fixture cwd:

```bash
RV_TX=$(dx "ls -t '$VERIFY_CFG'/projects/*$(basename "$VERIFY_RUN")*/*.jsonl 2>/dev/null | head -1" | tr -d '\r')
```

That is untested code sitting on the release path. Close it by running the gate against the
**currently released** `1.0.0-beta.2`, which genuinely still ships the shim:

```bash
devcontainer up --workspace-folder .    # Docker Desktop must be running
./release-verify.sh
```

**Expected: a RED**, specifically

```
Gate 0: SKILL.md SHADOWED — a same-named command suppressed the skill body (#55)
```

That red is the canary's **true-positive test**, not a failure to wait out — beta.2 *is* shadowed, so
a canary that stays green there is broken. Interpret the outcomes:

| Outcome | Meaning | Action |
|---|---|---|
| `SKILL.md SHADOWED` | glob resolved, signature fired, message reads correctly | gap closed — proceed to step 2 |
| `no session transcript found` | the glob is wrong (harness bug) | fix the `RV_TX` lookup in `release-verify.sh`, re-run |
| `the skill body loaded ... (entry point intact)` | canary is broken — it cannot see a genuinely shadowed release | **stop**; the check is worthless as written, rethink the discriminator |

Everything else in that run is expected to pass as it did before, EXCEPT the install assertion added
for #55 (`absent (correctly): commands/implement-feature.md`), which will also red against beta.2 —
that tag still ships the file. Both reds are expected and vanish once this fix is released.

Record the result in this file before moving on.

**2. Merge to `main`** — `git checkout main && git merge 55-skill-suppression`, with
`git rm 55-plan.md` in the merge/close commit (branch-scoped scratch travels with the branch).

**3. Close #55** — all four acceptance criteria met. In the close comment, state that
`release-verify.sh` end-to-end against the *released* plugin happens at the beta.3 cut, and that its
gate is already mandated by `RELEASING.md` §4 (no separate issue — see the note below).

**4. Then start #50** — next in `dev-docs/release-plan.md`'s execution order. #55 existed to make
#50's premise true: `claude plugin eval` uses the `--plugin-dir` path, where the body was being
suppressed, so every eval was scoring a hallucinated workflow.

### Why no separate issue for the release-cut run (decided 2026-09-24)

`RELEASING.md` §4 already makes `release-verify.sh` **"the gate"** — mandatory at every cut, before
announcing, alongside confirming the milestone's issues are closed. An issue saying "remember to run
the release gate at the release" would duplicate an existing checklist step, and duplicated process
drifts.

It is also the wrong shape structurally: `release-plan.md`'s rule is *"if the current milestone has
no open issues, the release is ready to cut."* An issue whose work can only happen **after** the tag
exists can never be closed before the cut — it would either block the cut permanently or get punted,
teaching the habit of punting milestone issues to ship.

The **real** gap was never "will we remember to run it" but "the new assertion has never executed",
and step 1 above closes that directly. File an issue only if step 1 surfaces something that cannot be
fixed cheaply in that session.

### Two traps for whoever picks this up

- **`--output-format stream-json` lies about the slash path.** It does not surface the expanded
  command message or the injected skill body. Read the on-disk transcript
  (`<config>/projects/<cwd-slug>/<session>.jsonl`) for anything about typed slash commands. This
  artifact produced two wrong conclusions in the original session.
- **A plain grep for `05-test-intent.md` false-passes on a shadowed body** — the shadowed conductor
  hunts `SKILL.md` down and `Read`s it, so the string shows up anyway. Key on
  `Base directory for this skill` (healthy) vs `already loaded above; instructions unchanged` (bug).
