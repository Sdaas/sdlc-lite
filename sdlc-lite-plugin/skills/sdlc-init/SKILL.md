---
name: sdlc-init
description: "EXPLICIT ENTRY ONLY — this workflow runs when, and only when, the user types the /sdlc-init slash command. Never invoke it yourself from a natural-language request, however closely the request matches; handle such a request as you normally would. (What it is: a one-time setup that installs the pinned dev toolchain into the repo's active Python environment and adds the pytest, coverage and mutmut config that /implement-feature needs, each change shown and approved first.)"
---

# sdlc-init — set a Python repo up for /implement-feature

You are the conductor. Measure with `toolchain/setup_check.py`, present **one** plan, STOP for
approval, then apply it. Idempotent: a second run on a set-up repo changes nothing.

**Hard rules:** never commit, never stage. Never write or install anything before an explicit yes.

## Steps

1. **Git.** Run `git rev-parse --is-inside-work-tree`. If it fails, say so and ask: "Shall I run
   `git init` here?" End the turn; run `git init` only on an explicit yes. Do nothing else first.
2. **Project.** No `pyproject.toml` in the working directory → stop: "🔴 No `pyproject.toml` here.
   `/sdlc-init` sets up an existing Python project; it does not create one." Stopping.
3. **Measure.** The plugin root is two levels above this skill's base directory (the line "Base
   directory for this skill: `<root>/skills/sdlc-init`" → `<root>` = that path minus the trailing
   `/skills/sdlc-init`). Run, in the user's active Python:
   `python <root>/toolchain/setup_check.py --repo .`
   Its package table (package · found · floor · action) goes into **the turn's final message** —
   the step-4 plan, the step-6 finish, or a step-3 stop — once, in full, every row even when all
   are `ok`; never summarized. Tool output is not the reply the human reads. Exit 2 (no `pyproject.toml`, or a config file
   does not parse) → quote its message and stop. Pip not available **and** a row needs
   `install`/`upgrade` → stop and say so (🔴 `python -m pip` is missing; pip-less environments such
   as uv-only are out of scope — install the toolchain by hand, then re-run). Pip missing but every
   row `ok` → carry on; nothing needs pip.
4. **Plan — one STOP.** If any row is `install`/`upgrade` or any config item is missing, show a single
   plan message that **opens with the step-3 table**, then:
   - **Install:** `python -m pip install "<name>>=<floor>" …` for every `install`/`upgrade` row
     (bare `"<name>"` when the floor is `-`).
   - **Layout:** the package dir — `src/<pkg>/` (src-layout) or `<pkg>/` at the root, the one with
     `__init__.py` — and the tests dir (`tests/`). None found or more than one candidate → name what
     you found and ask in the same STOP; never guess silently.
   - **Config:** one unified-style diff per missing item only — never edit a table that already exists:
     - `pyproject.toml`: `[tool.mutmut]` `source_paths = ["<pkg dir>/"]` · `[tool.pytest.ini_options]`
       `testpaths = ["<tests dir>"]` · `[tool.coverage.run]` `source = ["<pkg dir>"]` + `branch = true`
     - `.gitignore` (create if absent): the missing ones of `mutants/`, `.coverage*`, `*.egg-info/`,
       `.implement-feature/`, `if-runlog.jsonl`, appended under a `# sdlc-lite (/sdlc-init)` comment.

   Then STOP and ask for approval ("reply to apply, or name items to drop"). End the turn.
   After an explicit yes: run the pip command(s), write the files with Edit/Write, re-run the check
   and show its table as in step 3. A pip error is shown verbatim and the run stops — no workaround, no downgrade, no venv.
5. **Smoke test (always, even when nothing was missing).** Run `mutmut run "*__mutmut_1"` (one mutant
   per function — fast), then `rm -rf mutants/`. On failure quote mutmut's error and name the cause + fix:

   | Error | Cause · fix |
   |---|---|
   | "Could not figure out where the code to mutate is" | `[tool.mutmut] source_paths` is wrong or missing · point it at the package dir |
   | `ModuleNotFoundError` for the package | package not installed · `pip install -e .` |
   | clean test run fails | the suite itself is red · run `pytest`, fix it first |
6. **Finish.** Nothing missing and smoke green → the step-3 table, then "✅ Nothing to change — this repo is set up for
   /implement-feature." (no approval STOP). Otherwise a 2–3 line summary of what changed (uncommitted —
   the user reviews with `git diff`). Next step: `/implement-feature <feature>`.

## Rules

- Never commit or stage; never downgrade a package; never create a venv.
- Never work around pip errors — show them verbatim.
- Every write to a user file is shown as a diff and approved first; only missing items are added.
