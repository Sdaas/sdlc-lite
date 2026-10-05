---
description: On a set-up repo with nothing for mutmut to mutate yet, /sdlc-init reports the smoke test as a plain skip, not a failure (#101)
tags: [sdlc-init]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The mutmut smoke test runs, finds no mutant, and the reply reports it as a plain skip (nothing to mutate yet) with no 🔴 or ❌. No file is edited or written, mutants/ is not left behind, nothing is installed or committed.
---

/sdlc-init
