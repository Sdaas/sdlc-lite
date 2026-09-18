# Contents

Interview-driven, test-first, human-in-the-loop workflow that builds a reviewed, tested, committed Python feature via a conductor + isolated, model/effort-pinned subagent gates.

# Features
## Implement Feature

`/implement-feature` runs as a **conductor** (the interactive session that holds the through-line and
talks to you) walking a fixed sequence of **gates**. The bias-sensitive gates — write tests, review
tests, implement, verify, review code — run as **isolated subagents**. A guard hook enforces the isolation; a deterministic analyzer
proves after the fact what actually happened. There is **no hand-written orchestration code** — the
whole workflow is expressed in Markdown, and the agent is the runtime.

What that buys you:

- Tests are written by an *algorithm-blind* subagent, reviewed by an independent critic *before* any code exists, and the implementer is *barred from editing them*.
- Design and every review gate run on a higher model than implementation
- A separate verifier drives the *real* feature against every
  acceptance criterion and exercises every external boundary un-mocked.
- Nothing is committed until you review the real artifacts and approve.
- Every gate is *isolated* (it reads only the files
  curated for its role) and runs at a *pinned model/effort*. 
- After each run a deterministic audit produces a **receipt** that verifies both from the ground-truth session transcript — turning "we
  isolate and we bound the reasoning budget" from a claim into a per-run, checkable fact. The model, effort, and isolation are all **verified** by the receipt from the transcript, with **best-effort real-time prevention** by the guard (isolation).

---

## User Guide

Read the **[User Guide](docs/user-guide.md)** for full install, prerequisites, and FAQ. Quick start:

1. Install the plugin:
   ```
   /plugin marketplace add Sdaas/claude-plugins
   /plugin install sdlc-lite@sdaas
   ```
2. Make sure your target project is a git repo.
3. Install the required toolchain into that repo's environment (see [User Guide](docs/user-guide.md)).
4. Run `/implement-feature` and point it at a GitHub issue, a file, or a 1-2 line description of the feature.

## Developer Guide

Read the **[Developer Guide](docs/developer-guide.md)** - Architecture (conductor + isolated gates), the guard hook, the analyzer, the design decisions (ADRs), and the container testing methodology. 

Also there is a **[Tutorial](docs/tutorial.md)** that demonstrates how to build a basic plugin.
The concepts (plugin vs command vs skill vs subagent), subagent isolation, and a runnable `toy-greet` example to build intuition before reading the real product.

---

## What's in this repo

```
README.md                      # this router
CLAUDE.md                      # guidance for Claude Code working in this repo
docs/
  user-guide.md                # run it on your own repo
  developer-guide.md           # understand / extend it
  tutorial.md                  # learn the underlying concepts
DEVCONTAINER.md                # the dev-container test harness (referenced by the Developer Guide)
design/                        # standalone design-investigation records referenced by the ADRs
sdlc-lite-plugin/      # ← the product
toy-greet-plugin/              # a minimal 2-gate example plugin (used by the Tutorial)
.claude-plugin/marketplace.json  # the DEV catalog (name: sdlc-lite-dev)
.devcontainer/                 # the dev container definition
REVIEW-PROMPT.md               # read-only review methodology (findings now tracked as GitHub issues)
```

This repo's root `.claude-plugin/marketplace.json` is the **dev** catalog
(`name: sdlc-lite-dev`, a live directory source used by the maintainer + dev container). It carries:

- **`sdlc-lite`** — the product this repo exists to ship (command `/implement-feature`).
- **`toy-greet`** — a two-file, two-gate `/greet` workflow kept as the Tutorial's runnable example
  (tutorial-only; never published to customers).


---

## Requirements at a glance

- **Claude Code** (the CLI, desktop, or IDE extension).
- **Python 3.12+** on the target repo.
- The pinned dev toolchain (`ruff`, `mypy`, `pytest`, `pytest-cov`, `mutmut`, `hypothesis`,
  `pytest-asyncio`) installed into the target repo's environment — the [User Guide](docs/user-guide.md)
  walks through this. Gate 0 hard-fails if any tool is missing, so nothing runs on a broken environment.

## Status

`sdlc-lite` is **v1**: it has been run end-to-end against real Python features (a duration
parser, a slugifier, and an async cached JSON fetcher), including a fault-injection pass, inside the
dev container. See the [Developer Guide](docs/developer-guide.md) for the testing methodology and the
recorded design decisions.

---
Built by Soumendra Daas. Licensed MIT (see `sdlc-lite-plugin/.claude-plugin/plugin.json`).
