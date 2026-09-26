---
description: The TEST-REVIEW subagent rejects an error test that ignores the documented message contract
tags: [gate-4]
plugins: ["../.."]
max_turns: 15
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Agent]
expected_outcome: The review returns CHANGES-REQUESTED because test_to_roman_non_int_raises_type_error does not assert the documented TypeError message.
---

We are at the TEST-REVIEW gate of an in-flight /implement-feature run. Spawn the `sdlc-lite:test-reviewer` subagent with this brief, then report its verdict.

- `<artifact_dir>` = `.implement-feature/37-to-roman`, `<code_root>` = `romankit`, `<tests_root>` = `tests` — resolve each against the current working directory to an absolute path before you pass it.
- Its inbox: `01-requirements.md`, `02-design-interface.md`, `03-design-internal.md`, `04-test-plan.md` and `05-test-intent.md` under `<artifact_dir>/handoff/`, and the tests under `<tests_root>/`.
- Task: review the tests against the requirements and the design, and write `<artifact_dir>/handoff/06-test-review-findings.md` with a verdict (`APPROVE` or `CHANGES-REQUESTED`) and specific findings.
