# #19 — `/sdlc-init`: set a Python repo up for `/implement-feature`

Working plan (root `CLAUDE.md` → Planning docs). GitHub #19 is the spec; settled scope is the
issue comment of 2026-10-03. Branch `19-sdlc-init` from `main`. Tier **T1 + T2 + T3**.

## Locked decisions

- **D1** `requirements-dev.txt`: `mutmut>=3` (was `==3.8.0`).
- **D2** Gate 0 (pure checker): all seven pins via `importlib.metadata` + `[tool.mutmut]` in
  `pyproject.toml` or `[mutmut]` in `setup.cfg`; missing → 🔴 "run `/sdlc-init`". Inline command
  still opens with `ruff --version`; the ✅ render is unchanged.
- **D3** `.gitignore` lines: `mutants/`, `.coverage*`, `*.egg-info/`, `.implement-feature/`, `if-runlog.jsonl`.
- **D4** T3 fixture `.gitignore` gains `.coverage*`; `test-fixtures/README.md` updated to match.
- **D5** Smoke: `mutmut run "*__mutmut_1"`, then `rm -rf mutants/`; failure → cause + fix table.
- **D6** One approval STOP for the whole plan (installs + package dir + diffs); `python -m pip`
  only; no pip / no `pyproject.toml` → stop with a message. `git init` offered first, run only on yes.
- **D7** Only missing tables are added: `[tool.mutmut] source_paths = ["<pkg dir>/"]`,
  `[tool.pytest.ini_options] testpaths = ["<tests>"]`, `[tool.coverage.run] source = ["<pkg dir>"]`,
  `branch = true`. Existing tables never edited.
- **D8** `t3-run.sh` / `Makefile`: `ENTRY=` override, `VENV=1` (`~/t3-venv`: `ruff==0.5.0` + the
  fixture editable; run copy stripped of mutmut table + gitignore lines). T3 session:
  `/sdlc-init` → `/sdlc-init` (no-op on its own output) → `/implement-feature <BRIEF>` through Gate 7.
- **D9 (option A)** `toolchain/setup_check.py` — measure-only, stdlib-only: prints the
  found / floor / action table and the missing config items. The skill renders + writes; the
  script never writes. Added to the code list in `CLAUDE.md` / `architecture.md`.

## Files

| File | Change |
|---|---|
| `sdlc-lite-plugin/skills/sdlc-init/SKILL.md` | new skill (explicit entry) |
| `sdlc-lite-plugin/toolchain/setup_check.py` | new measure-only script |
| `sdlc-lite-plugin/toolchain/requirements-dev.txt` | D1 |
| `sdlc-lite-plugin/policy.py` | `PLUGIN_SKILL_NAMES` += `sdlc-init` |
| `sdlc-lite-plugin/skills/implement-feature/SKILL.md` | Gate 0 step 1 + 🔴 render (D2) |
| `sdlc-lite-plugin/evals/_fixtures/python-starter.sh` | `[tool.mutmut]` default; `nomutmut`, `nogit` options |
| `sdlc-lite-plugin/evals/gate-7-mutmut-unconfigured-halts/scaffold.sh` | `nomutmut` |
| `test-fixtures/python-starter/roman-numeral/{pyproject.toml,.gitignore}` | what `/sdlc-init` writes |
| `t3-run.sh`, `Makefile` | D8 |
| docs | `README.md` §2, `test-fixtures/README.md`, `evals/README.md`, `dev-docs/t3-runs.md`, `CLAUDE.md`, `dev-docs/architecture.md` |

## Eval cases (run order) — cap `--max-cost-usd 3` per invocation

1. `sdlc-init-plan-stop` [sdlc-init] — unconfigured flat repo → table + `[tool.mutmut]` diff, STOP; nothing written, no pip, no commit.
2. `sdlc-init-noop` [sdlc-init, smoke] — configured repo → no Edit/Write, smoke `mutmut run`, no `mutants/`, "nothing to change".
3. ~~`sdlc-init-offers-git-init`~~ — dropped at Gate 7 (human ruling): the eval sandbox's home above the workspace is a git repo, so "not a repo" is unexpressible at T1. Proven at T3 instead.
4. `gate-0-mutmut-unconfigured-stop` [gate-0] — `/implement-feature` on unconfigured repo → points to `/sdlc-init`, no lock, no edit.

## T2

`tests/test_setup_check.py` (versions, config detection, T3 fixture = nothing missing,
`mutmut>=3`); `test_entry_points.py` parametrized over both skills.

## T3 evidence (`make t3-start SLUG=roman-numeral ENTRY=/sdlc-init VENV=1`)

- run 1: table (mutmut install, ruff 0.5.0 upgrade, rest install), diffs approved then written, smoke green
- run 2: nothing to change; `git status` clean
- `/implement-feature <BRIEF>` passes Gate 0, Gate 7 mutmut runs
- #68: `import roman_numeral` resolves into the run dir; any critic pip call `deny` / `critic-env-change`
- git-init offer: a separate short session in a non-git copy of the fixture — `/sdlc-init` offers `git init` and runs nothing until answered

## Progress

- [x] 0 CLASSIFY — branch `19-sdlc-init`, T1+T2+T3, plan file yes
- [x] 1 INTERVIEW — STOP ① approved; scope posted on #19
- [x] 2 DESIGN — STOP ② approved (option A)
- [x] 3 WRITE-EVALS — 4 cases + `test_setup_check.py`, entry-point params; pytest red, YAML ok
- [x] 4 EVAL-REVIEW — STOP ③ approved (review + 2 re-reviews; last finding fixed by human ruling)
- [x] 5 IMPLEMENT — confirm red ✓ (all 4 red, $0.45; results 2026-10-03T11-37…11-40); edit by [I] sonnet ✓; fast checks green (261 passed, links ok)
- [x] 6 CODE-REVIEW — review + 2 re-reviews, PASS; 6/7 (eval gaps, gate-1 history) → human at Gate 9
- [ ] 7 VERIFY — T1 ✓ (plan-stop, noop, gate-0 green after 2 repairs; git-init case dropped → T3), T2 ✓ 268; T3 ✓ run done (2× /sdlc-init, /implement-feature → Gate 9, #68, git-init offer) — attestation at STOP ④
- [x] 8 REGRESSION — 11 cases ✓, pytest 268 ✓
- [x] 9 REVIEW-GUIDE — 19-review.md.tmp
- [ ] 10 HUMAN REVIEW — STOP ④
- [ ] 11 COMMIT
