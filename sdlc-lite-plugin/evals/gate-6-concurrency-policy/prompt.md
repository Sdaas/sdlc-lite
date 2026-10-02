---
description: The VERIFY subagent applies the standards' concurrency policy to a pure feature
tags: [gate-6]
plugins: ["../.."]
max_turns: 15
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Agent]
expected_outcome: The verify report states there is no concurrency surface, per the standards file.
---

We are at the VERIFY gate of an in-flight /implement-feature run. Spawn the `sdlc-lite:verifier` subagent with this brief, then report its verdict.

- `<artifact_dir>` = `.implement-feature/37-to-roman`, `<code_root>` = `romankit`, `<tests_root>` = `tests` — resolve each against the current working directory to an absolute path before you pass it.
- The Python standards: `skills/implement-feature/references/quality-standards.md` in the sdlc-lite plugin — pass its absolute path.
- Task: verify the feature and write `<artifact_dir>/handoff/07-verify-report.md` with per-AC observed results and an overall verdict.
