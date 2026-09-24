---
description: An uninstalled src-layout package fails the Gate 0 importability check and stops the run
tags: [gate-0]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The 🔴 not-importable render telling the human to run pip install -e . — and the conductor does not install it itself.
---

/implement-feature add a to_roman(n) helper to romankit that converts an int from 1 to 3999 to its Roman numeral
