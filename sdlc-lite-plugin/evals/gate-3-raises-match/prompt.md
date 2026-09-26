---
description: The WRITE-TESTS subagent's error tests pin the design's message contract
tags: [gate-3]
plugins: ["../.."]
max_turns: 15
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Agent]
expected_outcome: tests/test_roman.py implements the test plan and every error test asserts the documented message, not just the exception type.
---

We are at the WRITE-TESTS gate of an in-flight /implement-feature run. Spawn the `sdlc-lite:test-writer` subagent with this brief, then report what it returned.

- `<artifact_dir>` = `.implement-feature/37-to-roman`, `<code_root>` = `romankit`, `<tests_root>` = `tests` — resolve each against the current working directory to an absolute path before you pass it.
- Its inbox: `01-requirements.md`, `02-design-interface.md` and `04-test-plan.md` under `<artifact_dir>/handoff/`.
- Hard rule: do NOT read `03-design-internal.md` or anything under `<code_root>/` — encode the contract, not an implementation.
- Task: implement the `04-test-plan.md` inventory under `<tests_root>/`, write `<artifact_dir>/handoff/05-test-intent.md`, and confirm the suite is red.
