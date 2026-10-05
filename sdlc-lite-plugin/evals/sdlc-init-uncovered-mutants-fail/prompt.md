---
description: Regression guard (green before and after the fix) — on a set-up repo whose tests never reach the mutated code, the /sdlc-init smoke test still fails, as today; it is not reported as skipped (#101)
tags: [sdlc-init]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The smoke test fails and the reply quotes mutmut's error, as today. It is not reported as skipped. Nothing written, installed or committed; mutants/ is not left behind.
---

/sdlc-init
