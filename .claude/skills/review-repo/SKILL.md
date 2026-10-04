---
name: review-repo
description: Full-repo review before a release — nine parallel area reviewers and one consolidator, all pinned to claude-opus-5-5 at effort high, then a measurement that proves it. Human-typed only; the model never starts it.
disable-model-invocation: true
argument-hint: "<release version>"
---

# /review-repo — full-repo review, pinned and measured

Release version: `$ARGUMENTS` (the bare version, e.g. `0.1.0`). Output: one ranked `review-YYYYMMDD.md` in the repo root — a kept record that is committed after the human approves it, not a `.md.tmp` file. You are the
conductor: you dispatch, measure and report. You do no review yourself.

Pins live in `.claude/agents/repo-area-reviewer.md` and `repo-review-consolidator.md`
(`claude-opus-5-5`, effort `high`). `measure.py` checks the agent files and the transcripts against those fixed values.

## Steps

0. **Preconditions.** Run in a FRESH session: earlier subagents in this session would be counted.
   State the current branch and `git status`. The review belongs on a clean `main` after the last
   product change; if it is not, warn and let the human decide.
   **Pre-flight.** Run
   `python3 .claude/skills/review-repo/measure.py --session ${CLAUDE_SESSION_ID} --phase pins --report none`.
   It checks only the two agent files. Any non-zero exit → STOP before spawning anything: show the
   block and say the pins are wrong.
1. **Assign files.** Run `git ls-files`. Assign every file to exactly one area in the table below.
   Report any file that fits no area; do not skip it.
2. **Area reviewers.** Spawn 9 `repo-area-reviewer` agents in ONE message (parallel), by that name,
   with NO `model` parameter (the frontmatter pins are the SSOT; an inline model would override
   them). Each prompt: the area number and name, its file list, the release version. Wait until all
   9 reports are back (each as a returned result or a completion notice) before step 3. Do not edit their reports.
3. **Report path.** `review-YYYYMMDD.md` (today) in the repo root. If it exists, use `-2`, `-3`, ….
4. **Measure the areas.** Run
   `python3 .claude/skills/review-repo/measure.py --session ${CLAUDE_SESSION_ID} --phase areas --report <path>`.
   Any non-zero exit → STOP. Show the block (or the error), say the review is INVALID and nothing may be triaged. Do not
   spawn the consolidator.
5. **Consolidator.** Spawn one `repo-review-consolidator` (NO `model`). Wait for its result
   before step 6. Give it the release version, every area report
   verbatim, the files that fit no area (step 1) and the report path.
6. **Measure the final run.** Run the same command with `--phase final`. Any non-zero exit → STOP as in
   step 4 (the report now carries the INVALID header).
   Never hand the turn to the human between step 0 and step 7 except at a STOP: step 6 must run.
   Under `claude -p`, set `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`; the default ends the session
   after 600 s of background work, before step 6.
7. **Report.** Show the measurement line and the summary counts per bucket. Do not file issues,
   change other files or commit. Wait for the human.

## Areas

| # | Area | Files |
|---|---|---|
| 1 | Skill and agent prose (product, agent-read) | `sdlc-lite-plugin/skills/**` (including each skill's `references/`), `sdlc-lite-plugin/agents/**` |
| 2 | Enforcement code and its tests | `sdlc-lite-plugin/hooks/**`, `policy.py`, `agentdefs.py`, `conftest.py`, `sdlc-lite-plugin/commands/**`, `sdlc-lite-plugin/tests/**` |
| 3 | Analyzer and toolchain | `sdlc-lite-plugin/analyzer/**` (with its tests), `sdlc-lite-plugin/toolchain/**` |
| 4 | Evals and fixtures | `sdlc-lite-plugin/evals/**`, `test-fixtures/**`, `.devcontainer/**` |
| 5 | User docs and install path | `README.md`, `.claude-plugin/**`, `sdlc-lite-plugin/.claude-plugin/**`, `release*.sh`, `release.test.sh`, `Makefile`, `clean-run.sh`, `t3-run.sh`, `verify-entry-points.py`, `.gitignore`, `.env.example`, `LICENSE` |
| 6 | Developer docs | `dev-docs/*.md` (not `adr/`, `findings/`, `proposals/`) |
| 7 | Historical records | `dev-docs/adr/**`, `dev-docs/findings/**`, `dev-docs/proposals/**`, earlier `review-*.md` files |
| 8 | Repo-local skills and process | `.claude/**`, `CLAUDE.md`, `dev-docs/issue-template.md`, `toy-greet-plugin/**` |
| 9 | Overall repo structure | The whole `git ls-files` list and the directory tree, not file contents (read a file only to check a claim) |
