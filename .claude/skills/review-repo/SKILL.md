---
name: review-repo
description: Full-repo review before a release — three parallel area reviewers and one consolidator, all pinned to claude-opus-5-5 at effort high, then a measurement that proves it. Optionally reviews only the areas changed since a ref. Human-typed only; the model never starts it.
disable-model-invocation: true
argument-hint: "<release version> [<since-ref>]"
---

# /review-repo — full-repo review, pinned and measured

Arguments: `$ARGUMENTS` = the release version (bare, e.g. `0.1.0`), optionally followed by a since-ref (e.g. the last release tag). With a since-ref only areas with a file changed since that ref are reviewed. The structure checks run only when area C is reviewed, so the review before a release is a full run (no since-ref). Output: one ranked `review-YYYYMMDD.md` in the repo root — a kept record that is committed after the human approves it, not a `.md.tmp` file. You are the
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
1. **Plan.** Run
   `python3 .claude/skills/review-repo/measure.py --session ${CLAUDE_SESSION_ID} --phase plan --report none [--since <ref>]`
   (add `--since <ref>` only when a since-ref was given). It assigns every file to an area. Any non-zero exit
   → STOP and show it (nothing to review, or a bad ref). Report any unassigned file; do not skip it.
2. **Area reviewers.** Spawn one `repo-area-reviewer` per area the plan lists for review (up to 3) in ONE message (parallel), by that name,
   with NO `model` parameter (the frontmatter pins are the SSOT; an inline model would override
   them). Each prompt: the area key and name, its file list from the plan, the release version. Wait until all
   the reports are back (each as a returned result or a completion notice) before step 3. Do not edit their reports.
3. **Report path.** `review-YYYYMMDD.md` (today) in the repo root. If it exists, use `-2`, `-3`, ….
4. **Measure the areas.** Run
   `python3 .claude/skills/review-repo/measure.py --session ${CLAUDE_SESSION_ID} --phase areas --report <path> [--since <ref>]`.
   Any non-zero exit → STOP. Show the block (or the error), say the review is INVALID and nothing may be triaged. Do not
   spawn the consolidator.
5. **Consolidator.** Spawn one `repo-review-consolidator` (NO `model`). Wait for its result
   before step 6. Give it the release version, every area report
   verbatim, the areas the plan marked not reviewed (with the since-ref), the files that fit no area (step 1) and the report path.
6. **Measure the final run.** Run the same command with `--phase final` (and the same `--since <ref>` when one was given). Any non-zero exit → STOP as in
   step 4 (the report now carries the INVALID header).
   Never hand the turn to the human between step 0 and step 7 except at a STOP: step 6 must run.
   Under `claude -p`, set `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`; the default ends the session
   after 600 s of background work, before step 6.
7. **Report.** Show the measurement line and the summary counts per bucket. Do not file issues,
   change other files or commit. Wait for the human.

## Areas

The area table lives in `AREAS` in `measure.py` (SSOT; do not copy its patterns here).

- **A — Product:** skills, agents, hooks, commands, enforcement code, analyzer, toolchain and their tests.
- **B — Install path and evals:** evals, fixtures, devcontainer, README, manifests, release and run scripts.
- **C — Docs, history, process and structure:** `dev-docs/`, review records, `.claude/`, `CLAUDE.md`, `toy-greet-plugin/`, plus the structure checks over the whole file list and tree.
