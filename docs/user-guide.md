# User Guide — running `/implement-feature` on your own repo

This guide is for someone who wants to **use** the plugin: install it from GitHub, do a one-time
setup, and run `/implement-feature` against their own Python project. If you want to understand or
change how it works, read the [Developer Guide](developer-guide.md) instead; if you're new to Claude
Code plugins, the [Tutorial](tutorial.md) builds the concepts from scratch.

---

## 1. What it does (in one paragraph)

You give `/implement-feature` a one-line feature request. It interviews you to pin down the
requirements, proposes a design you approve, then hands the work to a chain of isolated subagents that
write the tests, review them, implement to green, verify the real behavior, and review the whole
change — each on a model pinned to its role. You review the finished work and approve; only then does
it commit, on a feature branch, using **your** git identity. Nothing is committed without your
approval, and it never commits on your default branch.

---

## 2. Prerequisites

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

## 3. One-time setup

### 3a. Install the plugin from GitHub

The plugin is published through a marketplace in this repo. Register the marketplace, then install:

```bash
# register this repo as a plugin marketplace
claude plugin marketplace add Sdaas/sdlc-lite

# install the plugin from it
claude plugin install implement-feature@sdaas-sdlc-lite
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

### 3b. Install the pinned toolchain into your project's environment

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
either from the file (after `claude plugin install`, it lives under your Claude Code plugins cache) or
by name:

```bash
# from the pinned file (path is under your plugins cache after install):
pip install -r ~/.claude/plugins/**/sdlc-lite-plugin/toolchain/requirements-dev.txt

# or simply, by name (the pinned floors):
pip install ruff mypy pytest pytest-cov mutmut hypothesis pytest-asyncio
```

> **Auto-installing the toolchain is a v1.1 backlog item.** For v1, this manual step is expected.

### 3c. Grant the plugin directory a one-time read permission

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

### 3d. Make your source package importable

If your project uses a **src-layout** (`src/yourpkg/`), install it editable so the tests can import it:

```bash
pip install -e .
```

Gate 0 checks this and stops with a clear message if your package isn't importable — see the
troubleshooting section.

---

## 4. Running a feature

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

## 5. Troubleshooting

**"Preflight failed — `<tool>` not found."**
A required tool isn't importable in the active environment. Install the toolchain (§3b) into the same
Python environment Claude Code runs commands in, then re-run. *(The message mentions rebuilding a dev
container — that's how the plugin's authors run it; on your own machine the equivalent is just having
the toolchain installed on PATH.)*

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

## 6. FAQ

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
Python only, in v1.

**Does it need the dev container?**
No — the container is how the plugin's authors test it (see the [Developer Guide](developer-guide.md)).
You run it directly in your own project. The real requirement is just the pinned toolchain in your
active environment.

**Where do I see what each subagent did — which model, which files it read?**
Gate 11 prints the report automatically, and you can re-run it on any past run with
`/sdlc-lite:analyze-run`. It reads the guard hook's tamper-evident audit log and the session
transcript.

**How do I uninstall it?**
`claude plugin uninstall implement-feature`, and optionally
`claude plugin marketplace remove sdaas-sdlc-lite`. Everything is reversible.
