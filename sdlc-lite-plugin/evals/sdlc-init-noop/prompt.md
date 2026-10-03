---
description: On a repo /sdlc-init already set up, a run changes nothing — it re-checks, runs the mutmut smoke test, cleans up after it and reports nothing to change
tags: [sdlc-init, smoke]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The table with no action needed, a green mutmut smoke test, and a reply saying there is nothing to change. No file is edited or written, mutants/ is not left behind, nothing is installed or committed.
---

/sdlc-init
