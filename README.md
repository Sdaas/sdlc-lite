# Contents

The main deliverable is **implement-feature** - a **Claude Code plugin** that turns a one-line feature request into a reviewed, tested, committed python change — through an interview-driven, test-first, human-in-the-loop workflow.

## Implement Feature

`/implement-feature` runs as a **conductor** (the interactive session that holds the through-line and
talks to you) walking a fixed sequence of **gates**. The bias-sensitive gates — write tests, review
tests, implement, verify, review code — run as **isolated subagents**. A guard hook enforces the isolation; a deterministic analyzer
proves after the fact what actually happened. There is **no hand-written orchestration code** — the
whole workflow is expressed in Markdown, and the agent is the runtime.

What that buys you:

- **Test-first, for real.** Tests are written by an *algorithm-blind* subagent (it sees the public
  contract, never the internal design), reviewed by an independent critic *before* any code exists,
  and the implementer is *barred from editing them*.
- **Reviews stronger than the code.** Design and every review gate run on a higher model than
  implementation — an invariant the plugin pins and the analyzer verifies.
- **Not "done" on green tests.** A separate verifier drives the *real* feature against every
  acceptance criterion and exercises every external boundary un-mocked.
- **You own the ship decision.** Nothing is committed until you review the real artifacts and approve.
- **Two guarantees.** Every gate is *isolated* (it reads only the files
  curated for its role) and runs at a *pinned model/effort*. After each run a deterministic audit
  produces a **receipt** that verifies both from the ground-truth session transcript — turning "we
  isolate and we bound the reasoning budget" from a claim into a per-run, checkable fact. The pieces
  are honest about *how* each is held: the model, effort, and isolation are all **verified** by the
  receipt from the transcript, with **best-effort real-time prevention** by the guard (isolation).
  This is observability plus
  best-effort prevention — not a hard cost cap**: the receipt tells you exactly what happened and
  flips to *untrusted* on any violation, which is the property a reviewer of the run actually needs.

---

## Pick your path

| You are… | Go to | What you'll find |
|---|---|---|
| **A user** — you want to run `/implement-feature` on your own Python repo | **[User Guide](docs/user-guide.md)** | Install from GitHub, one-time Python + toolchain setup, how to run a feature end-to-end, and an FAQ. |
| **A developer** — you want to understand, extend, or improve the plugin | **[Developer Guide](docs/developer-guide.md)** | Architecture (conductor + isolated gates), the guard hook, the analyzer, the design decisions (ADRs), and the container testing methodology. |
| **A learner** — you want to understand *how* a plugin like this is built | **[Tutorial](docs/tutorial.md)** | The concepts (plugin vs command vs skill vs subagent), subagent isolation, and a runnable `toy-greet` example to build intuition before reading the real product. |

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
.claude-plugin/marketplace.json  # publishes both plugins
.devcontainer/                 # the dev container definition
REVIEW-PROMPT.md               # read-only review methodology (findings now tracked as GitHub issues)
```

Two plugins are published through `.claude-plugin/marketplace.json`:

- **`implement-feature`** — the product this repo exists to ship.
- **`toy-greet`** — a two-file, two-gate `/greet` workflow kept as the Tutorial's runnable example.

---

## Requirements at a glance

- **Claude Code** (the CLI, desktop, or IDE extension).
- **Python 3.12+** on the target repo.
- The pinned dev toolchain (`ruff`, `mypy`, `pytest`, `pytest-cov`, `mutmut`, `hypothesis`,
  `pytest-asyncio`) installed into the target repo's environment — the [User Guide](docs/user-guide.md)
  walks through this. Gate 0 hard-fails if any tool is missing, so nothing runs on a broken environment.

## Status

`implement-feature` is **v1**: it has been run end-to-end against real Python features (a duration
parser, a slugifier, and an async cached JSON fetcher), including a fault-injection pass, inside the
dev container. See the [Developer Guide](docs/developer-guide.md) for the testing methodology and the
recorded design decisions.

---
Built by Soumendra Daas. Licensed MIT (see `sdlc-lite-plugin/.claude-plugin/plugin.json`).
