---
description: Build a Python feature via an interview-driven, test-first, human-in-the-loop workflow (conductor + isolated model-pinned gates). Use when the user wants to implement a new feature or capability with TDD and staged approvals.
---

# /sdlc-lite:implement-feature — conductor entry point

You are the **conductor** of the `implement-feature` workflow. Load and follow the
**`implement-feature` skill** — its `SKILL.md` is your full gate-by-gate score.

Do not improvise the process here. Load the skill and walk its gates in order,
starting at **Gate 0 (CLASSIFY + model plan)**.

If the user typed a feature description after the command, treat it as the raw
feature request handed to Gate 0. If they typed nothing, ask for a one-line
description of the feature to build, then proceed to Gate 0.
