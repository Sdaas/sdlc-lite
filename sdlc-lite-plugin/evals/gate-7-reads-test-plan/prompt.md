---
description: The CODE-REVIEW subagent reads the test plan it grades coverage and kill-rate against
tags: [gate-7]
plugins: ["../.."]
max_turns: 15
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Bash, Write, Agent]
expected_outcome: The code-reviewer reads 04-test-plan.md for the coverage and mutation thresholds before writing its findings.
---

We are at the CODE-REVIEW gate of an in-flight /implement-feature run. Spawn the `sdlc-lite:code-reviewer` subagent with this brief, then report its verdict.

- `<artifact_dir>` = `.implement-feature/37-to-roman`, `<code_root>` = `romankit`, `<tests_root>` = `tests` — resolve each against the current working directory to an absolute path before you pass it.
- The Python standards: `skills/implement-feature/references/quality-standards.md` in the sdlc-lite plugin — pass its absolute path.
- Task: review the whole change and write `<artifact_dir>/handoff/08-code-review-findings.md` with a verdict (`APPROVE` or `CHANGES-REQUESTED`) and specific findings.
