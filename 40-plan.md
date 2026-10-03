# 40-plan — conductor runs coverage + mutmut (#40, closes #75)

Branch `40-conductor-quality-checks` from `main`. Tier T1 + T2 + T3. Scope: issue #40 comment (STOP ① 2026-10-03).

## Progress

| Gate | Status |
|---|---|
| 0 CLASSIFY | done |
| 1 INTERVIEW — STOP ① | approved 2026-10-03 |
| 2 DESIGN — STOP ② | approved 2026-10-03 |
| 3 WRITE-EVALS | done — 3 new cases, gate-7-reads-test-plan edited, T2 red (14). Deviation: mutation.txt = `mutmut results --all true` (run output is a spinner) |
| 4 EVAL-REVIEW — STOP ③ | review CHANGES-REQUESTED → fixed → re-review 1 APPROVE; STOP ③ approved 2026-10-03. Human added: pin `mutmut==3.8.0` in `toolchain/requirements-dev.txt` (Gate 5) |
| 5 IMPLEMENT | confirm-red 4/4 red ($1.94); sonnet implementer; pin applied; BENIGN_BASH `mutmut run` → `ruff check src` (test edit after STOP ③, flag at ④); fast checks green (205) |
| 6 CODE-REVIEW | CHANGES-REQUESTED (12 →IMPLEMENT, 2 →WRITE-EVALS) → fixed; case 2 now full-gate + no-dispatch, red with change stashed ($0.67), eval re-review APPROVE; code re-review 1 APPROVE + 3 nits applied. STOP ③ re-approval for case 2 pending |
| 7 VERIFY | T1 4/4 green (re-run after the option A repair, $1.39); T2 207; T3 roman-numeral: all 3 evidence points confirmed from the run's files (artifacts in t3-40-run.tmp/); attestation at STOP ④ |
| 8 REGRESSION | smoke 3/3 green ($0.73); pytest 207 |
| 9 REVIEW-GUIDE | 40-review.md.tmp |
| 10 HUMAN REVIEW — STOP ④ | approved 2026-10-03 (commit split); T3 attested from t3-40-run.tmp run-report (isolation compliance) |
| 11 COMMIT | in progress |

## Approved design


### 1. Files that change, and how

| File | Change |
|---|---|
| `skills/implement-feature/SKILL.md` — Gate 7 | New **"Before dispatch [C]"** block. (a) Read the mutation target in `04-test-plan.md`. (b) Coverage: `COVERAGE_FILE=<artifact_dir>/quality/.coverage python -m pytest --cov=<code_root> --cov-report=term-missing > <artifact_dir>/quality/coverage.txt`. (c) Mutation, unless the plan says `skip — <reason>`: note whether `mutants/` exists, then `mutmut run > /dev/null` and `mutmut results --all true > <artifact_dir>/quality/mutation.txt` (one `<mutant>: killed|survived` line each — `mutmut run`'s own output is a progress spinner), then `rm -rf mutants/` if Gate 7 created it. (d) If mutmut errors → **halt** Gate 7: quote mutmut's error verbatim, tell the human to configure `[tool.mutmut]` (e.g. via `/sdlc-init`), and do not dispatch. Never work around it (no config edit, no scratch copy, no `pip install`). Dimension 3 is reworded as "reads the results files"; the inbox prose adds `quality/coverage.txt` + `quality/mutation.txt`; the brief carries `mutation: SKIPPED — <reason>` when skipped. The conductor appends a run-log record for this quality step as soon as it finishes (before the dispatch), whose `result` carries coverage % and the mutation status (`mutation: <killed>/<total>` or `mutation: SKIPPED — <reason>`). |
| `SKILL.md` — inbox table (CODE-REVIEW row) | Add the two results files. |
| `SKILL.md` — Gate 8 / Gate 11 | Gate 8 adds pointers to `quality/*.txt`. Gate 8 and Gate 11 state `mutation: SKIPPED — <reason>` when skipped (prose only). |
| `SKILL.md` — Gate 5 tail, Gate 2 test-plan bullet | Small wording updates: "the conductor measures at Gate 7"; the deviation may be `skip — <reason>`. |
| `agents/code-reviewer.md` | The inbox adds the two results files. Dimension 3 grades them against the thresholds. A new line: **never run coverage or mutmut; if a results file is missing, report that as a finding.** No workaround advice. The description drops "checks the mutation-kill rate" → "grades the kill rate". |
| `references/quality-standards.md` | Tool table: coverage/mutmut "run by the conductor at Gate 7" with the `COVERAGE_FILE` form. Kill-rate section: `skip — <reason>` is a Gate 2 deviation, surfaced at approval. |
| `references/test-plan-template.md` | Mutation target: allow `skip — <reason>`. |
| `policy.py` | New `runs_quality_tool(command) -> bool`: a token whose basename is `mutmut`, or a `pytest` / `python -m pytest` invocation with a `--cov*` token. New `critic_bash_decision(agent_type, command)`: deny (rule `critic-quality-tool`) for any **write-confined** role. |
| `hooks/scripts/guard.py` | `_bash_deny_reason` calls `policy.critic_bash_decision` before step (c). |
| `tests/test_policy.py`, `hooks/tests/test_guard.py` | T2 (below). |
| `tests/test_inbox_parity.py` | Results files listed in the code-reviewer inbox, the SKILL table row and the Gate 7 inbox prose. |
| `evals/` | Three new cases + one edited case (below), plus `evals/README.md` rows. |
| Docs | `dev-docs/architecture.md` guard rules: add the critic quality-tool denial (doc parity). |
| `toolchain/requirements-dev.txt` | `mutmut>=2.5` → `mutmut==3.8.0` (human, STOP ③). |

### 2. Behavior delta a cold agent should show

- **Conductor at Gate 7:** runs coverage with the data file under `<artifact_dir>/quality/`, runs mutmut, writes both results files, leaves no `.coverage*` / `mutants/` in the product tree, then dispatches. With an unconfigured mutmut it halts with the error and the `[tool.mutmut]` / `/sdlc-init` pointer, and touches nothing. With a `skip — <reason>` plan it runs no mutmut and reports `mutation: SKIPPED — <reason>`.
- **code-reviewer:** grades from the results files; never invokes `mutmut` or `pytest --cov`.
- **Guard:** denies `mutmut …` / `pytest --cov …` to test-reviewer, verifier and code-reviewer; allows them for the conductor and the implementer.

### 3. Eval cases, in run order

All of them use `python_starter flat` + `roman_handoff gate-7`. Conductor cases tell the session it is the conductor at Gate 7 and give it the absolute path of the plugin's `SKILL.md` (the conductor always has it loaded; no hint at the expected answer).

1. **`gate-7-conductor-runs-quality`** (tags `gate-7`). Scaffold adds `[tool.mutmut] source_paths = ["romankit/"]`. Prompt: "do this gate's conductor steps up to, but not including, spawning the code-reviewer; then report." Graders (free):
   - `quality/coverage.txt` and `quality/mutation.txt` exist (file regex).
   - The trace has a `mutmut run` Bash call.
   - **no `.coverage*` and no `mutants/` at the repo root** (a `bash` grader: `test -z "$(ls -a | grep -E '^\.coverage|^mutants$')"`).
   - `git status --porcelain` is clean apart from `.implement-feature/` (bash grader).
2. **`gate-7-mutmut-unconfigured-halts`** (tags `gate-7`). There is no `[tool.mutmut]`, and `mutmut run` fails on the flat layout in a randomly named sandbox. Graders:
   - No Agent spawn of `code-reviewer` (`tool_used` max 0).
   - The reply matches `/sdlc-init|\[tool\.mutmut\]`.
   - `pyproject.toml` is unchanged (`git diff --quiet pyproject.toml`).
   - No `pip install` in the trace.
3. **`gate-7-mutation-skip-deviation`** (tags `gate-7`). The scaffold overwrites the test plan's mutation target with `skip — <reason>`. Graders:
   - No `mutmut` Bash call in the trace.
   - The reply contains `mutation: SKIPPED` plus the reason text.
   - The run-log Gate 7 record contains `SKIPPED`.
4. **Edit `gate-7-reads-test-plan`.** The scaffold writes `quality/coverage.txt` (100%) and `quality/mutation.txt` (counts giving 18/20 = 90%, two survivors). The brief adds the two paths. A new grader: no Bash call by the code-reviewer runs `mutmut` or `--cov`. The existing graders are kept (85% threshold still asserted).

Expected red before the prose edit: 1, 2 and 3 fail (today the conductor does none of this); 4 fails on the new grader (today's reviewer runs mutmut itself).

### 4. Failing pytest (T2)

- `test_policy.py`: `runs_quality_tool` true for `mutmut run`, `python -m pytest --cov=x`, `pytest -q --cov-report=term`, `cd /r && mutmut results`; false for `pytest -q`, `grep mutmut file`, `cat mutants.txt`. `critic_bash_decision` denies all three critics and allows `""` (the conductor), the implementer and the test-writer.
- `test_guard.py`: end-to-end hook JSON. code-reviewer `mutmut run` → deny; conductor → allow.
- `test_inbox_parity.py`: three new assertions (results files).

### 5. What T1 cannot prove → T3

Fixture **`roman-numeral`** (`make t3-start SLUG=roman-numeral`). It ships `[tool.mutmut]` (#44), and its `.gitignore` already ignores `mutants/`. Evidence the dry run must show:
- Gate 7: the conductor runs coverage + mutmut before the dispatch, and `quality/coverage.txt` + `quality/mutation.txt` exist in the run's artifact dir.
- The code-reviewer's guard audit has **zero denials** and no `mutmut` / `--cov` call.
- After Gate 7, `git status --porcelain` in `/workspaces/roman-numeral-run` shows no `.coverage*` (closes #75) and no run-created file. **Not proven here:** `mutants/` cleanup, because the fixture gitignores it. Case 1 covers that at T1.
- The skip path: T1 only (STOP ①).

### 6. Eval budget

`--max-cost-usd 3` per invocation, one case and one run. Expected spend:
- Confirm-red: 4 runs.
- Gate 7 VERIFY: 4 runs.
- Gate 8 regression: smoke ×3 + `gate-7`-tagged cases already run.
- Roughly $5–10 in total.
