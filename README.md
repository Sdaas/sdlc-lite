# sdlc-lite

Interview-driven, test-first, human-in-the-loop workflow that builds a reviewed, tested, committed Python feature via a conductor + isolated, model/effort-pinned subagent gates.

## Implement Feature

`/implement-feature` runs as a **conductor** (the interactive session that holds the through-line and
talks to you) walking a fixed sequence of **gates**. The bias-sensitive gates — write tests, review
tests, implement, verify, review code — run as **isolated subagents**. A guard hook enforces the isolation; a deterministic analyzer
proves after the fact what actually happened. There is **no hand-written orchestration code** — the
whole workflow is expressed in Markdown, and the agent is the runtime.

What that buys you:

- Tests are written by an *algorithm-blind* subagent and reviewed by an independent critic *before*
  any code exists. The implementer is *barred from editing them*.
- Design and every review gate run on a higher model than implementation.
- A separate verifier drives the *real* feature against every acceptance criterion and exercises
  every external boundary un-mocked.
- Nothing is committed until you review the real artifacts and approve.
- Every gate is *isolated* (it reads only the files curated for its role) and runs at a *pinned
  model/effort*. A guard hook blocks isolation breaches as they happen (best-effort for shell
  commands).
- After each run, a deterministic audit reads the session transcript and produces a **receipt**
  showing which model and effort each gate actually used and what each one saw. A violation marks
  the run untrusted.

---

## Quick start

1. Install the plugin:
   ```
   /plugin marketplace add Sdaas/claude-plugins
   /plugin install sdlc-lite@sdaas
   ```
2. Make sure your target project is a git repo.
3. Install the required toolchain into that repo's environment (see Prerequisites below).
4. Run `/implement-feature` and point it at a GitHub issue, a file, or a 1-2 line description of the feature.

---

## What it does (in one paragraph)

You give `/implement-feature` a one-line feature request. It interviews you to pin down the
requirements, proposes a design you approve, then hands the work to a chain of isolated subagents that
write the tests, review them, implement to green, verify the real behavior, and review the whole
change — each on a model pinned to its role. You review the finished work and approve; only then does
it commit, on a feature branch, using **your** git identity. Nothing is committed without your
approval, and it never commits on your default branch.

---

## Prerequisites

- **Claude Code** — the CLI, desktop app, or an IDE extension. (Install per
  [Anthropic's docs](https://code.claude.com/docs).)
- **Python 3.12 or newer** in the project you'll run it against.
- **A Python project with a test layout** — a `pyproject.toml`/`setup.cfg`, a source package
  (e.g. `src/yourpkg/` or `yourpkg/`), and a `tests/` directory. The workflow is Python-only.
- **The pinned dev toolchain installed in that project's active environment** (next section).
- **A configured git identity** (`git config user.name` / `user.email`) — the commit uses it.

> **Why so prescriptive about the toolchain?** The workflow's definition of "done" is enforced with
> real tools (lint, types, coverage, mutation testing). Gate 0 runs a **preflight** and **hard-fails
> if any tool is missing**, so nothing ever runs on a half-set-up environment and silently skips a
> quality check.

---

## One-time setup

### 1. Install the plugin from GitHub

The plugin is published through the **`Sdaas/claude-plugins`** umbrella marketplace, which pins it to
a released tag. Register that marketplace, then install:

```bash
# register the umbrella marketplace (the customer/release channel)
claude plugin marketplace add Sdaas/claude-plugins

# install the plugin from it (version-pinned to the released tag)
claude plugin install sdlc-lite@sdaas
```

Then, inside a Claude Code session, activate it in the current session:

```
/reload-plugins
```

Verify it's installed and enabled:

```bash
claude plugin list
claude plugin marketplace list
```

> **Tip.** Use the CLI form above (`claude plugin install …`) rather than typing `/plugin install …`
> as a one-liner inside a session — the interactive one-liner can silently open the manager UI and
> no-op.

### 2. Install the pinned toolchain into your project's environment

The gates rely on these tools being importable in the **same Python environment Claude Code runs
commands in** (use a virtualenv for your project):

| Tool | Used for | When |
|---|---|---|
| `ruff` | lint + format | every implement loop |
| `mypy` | static type checking | every implement loop |
| `pytest` | tests | every implement loop |
| `pytest-cov` | coverage | code review |
| `mutmut` | mutation testing | code review |
| `hypothesis` | property/stress tests | when the feature is concurrent/async |
| `pytest-asyncio` | async test support | when the feature is concurrent/async |

The plugin ships the pinned list at
`sdlc-lite-plugin/toolchain/requirements-dev.txt`. Install it into your project's environment,
either from the file (after `claude plugin install`, it lives under your Claude Code plugins cache,
in a directory named for the installed version) or by name:

```bash
# from the pinned file (<version> = the installed version, e.g. 0.1.0;
# `ls ~/.claude/plugins/cache/sdaas/sdlc-lite/` shows it):
pip install -r ~/.claude/plugins/cache/sdaas/sdlc-lite/<version>/toolchain/requirements-dev.txt

# or simply, by name (the pinned floors):
pip install ruff mypy pytest pytest-cov mutmut hypothesis pytest-asyncio
```

> **Auto-installing the toolchain is planned for `0.2.0`**
> ([#19](https://github.com/Sdaas/sdlc-lite/issues/19)). Until then, this manual step is expected.

### 3. Grant the plugin directory a one-time read permission

The plugin's bundled reference files (design/test-plan templates, the quality-standards file) live in
the plugin install directory — **outside** your project folder. By default Claude Code prompts
("read outside working directories") the first time a gate opens one. Add a one-time `permissions.allow`
read rule for the plugins cache so those reads are silent. In your Claude Code settings
(`~/.claude/settings.json` or the project's `.claude/settings.json`):

```json
{
  "permissions": {
    "allow": ["Read(~/.claude/plugins/**)"]
  }
}
```

(The load-bearing content — the Gate 0 preflight command — is kept inline in the workflow so the hot
path needs no such read even without this rule; the rule just removes the prompts for templates.)

### 4. Make your source package importable

If your project uses a **src-layout** (`src/yourpkg/`), install it editable so the tests can import it:

```bash
pip install -e .
```

Gate 0 checks this and stops with a clear message if your package isn't importable — see the
troubleshooting section.

---

## Running a feature

From a Claude Code session **in your project directory**:

```
/implement-feature add a function that parses an ISO-8601 duration string into seconds
```

(Or just `/implement-feature` and it will ask for a one-line description.)

You'll walk through these gates. You're actively involved at the start and end; the middle runs
unattended.

| Gate | What happens | Your part |
|---|---|---|
| **0 · Classify** | Preflight, detects your code/test layout, proposes the per-gate model plan and the branch. | **Confirm** layout, model plan, branch. |
| **1 · Interview** | Grills you to full clarity — it first proposes a *minimal* scope and an out-of-scope list, then asks numbered questions with a recommended answer each. Writes a `01-requirements.md` draft for you to read. | **Answer questions; review the real draft; reply APPROVED.** |
| **2 · Design** | Writes three files: the public-contract interface, the internal design (algorithm + rejected alternatives), and a test plan with coverage + mutation thresholds. | **Review the real drafts; reply APPROVED.** |
| **3 · Write tests** | An *algorithm-blind* subagent writes failing tests from the contract only. | — (unattended) |
| **4 · Review tests** | An independent critic checks the tests encode the requirements and aren't tautological — before any code exists. | — (unattended) |
| **5 · Implement** | A subagent writes the minimum code until `pytest` + `ruff` + `mypy` are all green. It **cannot edit your tests**. | — (unattended) |
| **6 · Verify** | A fresh read-only subagent drives the **real** feature against every acceptance criterion and exercises every boundary un-mocked. | — (unattended) |
| **7 · Code review** | A stronger-model reviewer reviews the whole diff across six quality dimensions and runs coverage + mutation testing. | — (unattended) |
| **8 · Review guide** | Orders the changed files, points you at every findings file and the audit log. | — |
| **9 · Human review** | Presents the finished work + an isolation-compliance summary. | **Review; reply APPROVED — or request changes.** |
| **10 · Commit** | Commits on the feature branch, with your git identity. | — |
| **11 · Report** | Auto-runs the analyzer and shows the per-gate model split + isolation compliance + token totals. | — |

Everything the run produces (requirements, design, findings, the audit log) is written to a per-run
directory under `.implement-feature/` in your repo. It's gitignored automatically and is **never** part
of the commit. Browse `handoff/` top-to-bottom (files are numbered in read order) to replay the run.

---

## Troubleshooting

**"Preflight failed — `<tool>` not found."**
A required tool isn't importable in the active environment. Install the toolchain (above) into the same
Python environment Claude Code runs commands in, then re-run.

**"`<pkg>` is not importable — a src-layout package that isn't installed."**
Your source package isn't on `sys.path`, so the test suite would go *falsely* red and could never reach
green. Run `pip install -e .` in your repo root, then re-run. The plugin deliberately **won't** install
it for you — your environment is yours to own.

**"A run is already in flight" (active-run lock).**
`.implement-feature/.active-run` exists from a previous run that didn't finish (or was interrupted
mid-commit). There is no in-workflow resume yet: finish or abandon that run, then delete the
`.active-run` file by hand and start again.

**The conductor warns its own model is below Opus-tier.**
A plugin can pin its *subagents'* models but not the *conductor's* (the interactive session). If you
launched a weaker session, the interview and design gates run below design-grade strength. Relaunch
with `claude --model opus` for full strength, or proceed as-is — it's your call at Gate 0.

**The commit fails with "no git identity."**
Set `git config user.name` and `git config user.email`. The plugin never invents an author — it uses
yours.

---

## FAQ

**Does it commit automatically?**
No. Gate 9 is a hard STOP: it never commits until you review the real artifacts and reply APPROVED.

**Will it commit on my `main`/`master`?**
Never. Gate 0 requires a feature branch if you're on the default branch, and Gate 10 re-checks before
committing. You can override the *triviality* judgment, but not this rule.

**Whose name is on the commit?**
Yours — it reads `user.name`/`user.email` from your git config and never passes `--author`. For a
`Co-Authored-By:` trailer it follows your repo's existing convention.

**Can it edit my existing tests to make them pass?**
No. The implementer subagent is blocked (by a guard hook, by its role instructions, and by the final
code review) from editing any test file. The tests are the approved, independently-reviewed contract.

**What languages does it support?**
Python only.

**Does it need the dev container?**
No — the container is how the plugin's authors test it (see the Developer Guide, linked below).
You run it directly in your own project. The real requirement is just the pinned toolchain in your
active environment.

**Where do I see what each subagent did — which model, which files it read?**
Gate 11 prints the report automatically, and you can re-run it on any past run with
`/sdlc-lite:analyze-run`. It reads the guard hook's tamper-evident audit log and the session
transcript.

**How do I uninstall it?**
`claude plugin uninstall sdlc-lite`, and optionally
`claude plugin marketplace remove sdaas`. Everything is reversible.

---

## For developers

Improving or extending the plugin itself, rather than just running it, is a different audience — see
**[`dev-docs/`](dev-docs/README.md)** for the architecture, the guard hook, the analyzer, the design
decisions (ADRs), and the container testing methodology. Before changing the plugin's prose, read
**[`verification-ladder.md`](dev-docs/verification-ladder.md)** (how much proof a change needs) and
**[`eval-tutorial.md`](dev-docs/eval-tutorial.md)** (the eval suite that provides the cheap tier).

---

## What's in this repo

```
README.md                      # this file — install + run, for a user of the plugin
CLAUDE.md                      # guidance for Claude Code working in this repo
dev-docs/
  README.md                    # audience + findings-vs-proposals split
  developer-guide.md           # hub: how to change the plugin
  architecture.md              # how it works inside
  adr/                         # why: architecture decision records
  tutorial.md                  # learn the underlying concepts
  RELEASING.md                 # versioning, issue triage, release procedure
  DEVCONTAINER.md              # the dev-container test harness
  verification-ladder.md       # T1/T2/T3 — how much proof a change needs
  eval-tutorial.md             # authoring + running the plugin eval suite (T1)
  issue-template.md            # required structure for GitHub issues
  release-plan.md              # current + next release roadmap
  findings/                    # dated design-investigation records referenced by the ADRs
  proposals/                   # unwired design sketches, not yet built
sdlc-lite-plugin/      # ← the product
toy-greet-plugin/              # a minimal 2-gate example plugin (used by the Tutorial)
.claude-plugin/marketplace.json  # the DEV catalog (name: sdlc-lite-dev)
.devcontainer/                 # the dev container definition
```

This repo's root `.claude-plugin/marketplace.json` is the **dev** catalog
(`name: sdlc-lite-dev`, a live directory source used by the maintainer + dev container). It carries:

- **`sdlc-lite`** — the product this repo exists to ship (command `/implement-feature`).
- **`toy-greet`** — a two-file, two-gate `/greet` workflow kept as the Tutorial's runnable example
  (tutorial-only; never published to customers).


---

## Status

`sdlc-lite` is at **`0.1.0`** — 1.0-quality, being validated before GA. It has been run
end-to-end against real Python features (a duration parser, a slugifier, and an async cached JSON
fetcher), including a fault-injection pass, inside the dev container. See the [verification ladder](dev-docs/verification-ladder.md) for the testing methodology and
[`dev-docs/adr/`](dev-docs/adr/README.md) for the recorded design decisions.

---
Built by Soumendra Daas. Licensed MIT (see `sdlc-lite-plugin/.claude-plugin/plugin.json`).
