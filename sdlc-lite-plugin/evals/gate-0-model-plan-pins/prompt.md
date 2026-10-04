---
description: Gate 0's model plan names the dated pins — reviewers on claude-opus-5-5, producers on claude-sonnet-5-5 (#63)
tags: [gate-0, model-pins]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The Gate 0 summary's model plan names claude-opus-5-5 for the reviews and claude-sonnet-5-5 for implementation, tests and verification, and never claude-opus-4-8. It ends on the STOP; no subagent is dispatched.
---

/implement-feature add a to_roman(n) helper to romankit that converts an int from 1 to 3999 to its Roman numeral
