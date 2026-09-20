# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Repo Contents

- Ships the `sdlc-lite` plugin (command `/implement-feature`) that turns a one-line feature request into a reviewed, tested, committed python change — through an interview-driven, test-first, human-in-the-loop workflow.
- Top-level `README.md` routing to three audiences
  - **User Guide** (`docs/user-guide.md`) — install from GitHub, Python-only setup + toolchain
  prerequisite, how to run, FAQ. For a real user on their **own machine / own repo**.
  - **Developer Guide** (`docs/developer-guide.md`) — architecture, ADRs, design principles, the guard
  hook, the analyzer, and the testing / dry-run methodology. For someone improving the plugin.
  - **Tutorial** (`docs/tutorial.md`) — concepts (plugin vs command vs skill vs workflow) + subagent isolation, with `toy-greet-plugin/` as the runnable example.
- `toy-greet-plugin/` a minimal 2-gate example, kept for the Tutorial
- **Two channels (ADR-13):** this repo's root `.claude-plugin/marketplace.json` is the **dev** catalog (`name: sdlc-lite-dev`, directory source, live) holding `sdlc-lite` + the tutorial-only `toy-greet`; the **release** channel is a separate umbrella repo `Sdaas/claude-plugins` (`name: sdaas`, github-tag-pinned) — customers `marketplace add Sdaas/claude-plugins` → `install sdlc-lite@sdaas`.

## Working conventions
- **Process:** plan → approve → phased execution. Commit per **logical unit**. Keep git history.
- **Before every commit:** give the user a concise list of the key files / changes to review, and
  wait for explicit approval. Never commit before the user has reviewed and approved.
- **Bar:** *genuinely usable* — a stranger can install from GitHub and run it against their own Python repo. "Done" = a **green end-to-end dry run in the dev container** (see `DEVCONTAINER.md`), not "docs exist."
- **Issue triage:** releases are GitHub **milestones** (`1.0.0-beta.1`, `1.0.0`, …); label issues by **type only** (`bug`/`enhancement`/`documentation`); **no milestone = backlog**. **Every issue you file must follow `docs/issue-template.md`** (required
  structure, ~300-word cap, no transcripts). Full conventions + release procedure: `RELEASING.md`. Roadmap (current + next release only): `release-plan.md`.
- **Planning docs (two kinds):**
  - **`release-plan.md`** — the roadmap for the current + next release: the **narrative** *plus* the **execution order** of the milestone's issues. **GitHub is the SSOT for *which* issues ship** (and which don't); `release-plan.md` only adds *what order to implement them in*, referencing issues **by number only** — never copy titles or specs into it, so the two can't drift. Resumable with **"read release-plan.md and continue."**
  - **`<NN>-plan.md`** — a per-issue working plan (e.g. `41-plan.md`), created **only when the work is plan-mode-worthy** (spans multiple sessions, has multiple phases, or is structurally complex; small issues need none — the GitHub issue is the plan). It carries the locked decisions, the phased plan with testing, and a progress tracker. **Checked in on the feature branch, `git rm`'d in the merge/close commit** — branch-scoped scratch that travels with the branch it plans.
- Temp/scratch files go to `/tmp/` or end in `.tmp`, deleted when done.


## Architecture: the `/implement-feature` conductor + isolated gates
The whole product is expressed **declaratively** — a skill (`SKILL.md`) is the "score", agent-definition files pin per-gate models, and a hook enforces isolation. There is no hand-written orchestration driver. (Full detail + the ADRs behind these choices are in `docs/developer-guide.md`.)

- **Conductor [C]** — the interactive session running the skill
  (`sdlc-lite-plugin/skills/implement-feature/SKILL.md`). It holds the through-line, talks to the human, and walks 12 gates (0–11) in order.
- **Isolated subagents [I]** — bias-sensitive gates run as **separate agents** with fresh context, a **pinned model/effort**, and a **curated file inbox**. They are spawned via the Agent tool using the **plugin-namespaced** `subagent_type`, e.g. `sdlc-lite:test-writer` (never the bare name).
- Definitions live in `sdlc-lite-plugin/agents/*.md` — model/effort/tools are pinned there (`effort` can only be set via agent-def frontmatter, not inline).
- **The handoff contract:** every gate reads a curated inbox and writes a defined outbox **as files** —
  a gate **never** sees a prior gate's raw transcript. Code stays in the repo; gate isolation is via git
  plus a per-feature artifact dir (`.implement-feature/<run>/` with numbered handoff files). The
  interface/internal **design split** keeps the test-writer algorithm-blind: it is handed the interface
  design but **never** the internal design.

Core invariants (also in `SKILL.md` → Rules): design & every review use a higher model/effort than implementation; green unit tests are not "Done" (VERIFY drives the real code un-mocked); bound every automated loop and surface to the human on no progress; **never commit before human approval**.

### The guard hook 
Isolation is enforced, not just requested.

`sdlc-lite-plugin/hooks/hooks.json` registers a **PreToolUse** hook (`hooks/scripts/guard.py`) that fires for the conductor **and every subagent** and keys on `agent_type`. On every Read/Bash/Grep/Glob/Edit/Write/NotebookEdit it does the following 

- **audits** — appends a JSONL line per tool call; 
- **secrets guardrail** — denies reading `.env`/keys/credentials for any agent; -
- **algorithm-blind** — denies the `test-writer` reading the internal design;
- **test-integrity** — denies the `implementer` editing/writing any test file; plus reviewer write-confinement (writes only to its outbox + scratch).
- **draft-confinement** — denies any subagent reading under `handoff/draft/`.

A **plugin** hook (not a project-settings hook) was required for it to fire for subagents in headless.

### Quality standards / toolchain 
`sdlc-lite-plugin/skills/implement-feature/references/quality-standards.md` defines "green", coverage/mutation thresholds, boundary-resilience policy, and concurrency policy. The pinned toolchain is `sdlc-lite-plugin/toolchain/requirements-dev.txt` (ruff, mypy, pytest, pytest-cov, mutmut, hypothesis, pytest-asyncio). 

Gate 0 preflight hard-fails if any tool is missing. **A real user must install this toolchain into their own environment** (v1: documented manual install; auto-install is a v1.1 backlog item).

## Running / testing the plugin (dev container = our test harness)

For development, the plugin is **never** installed into the Mac's global `~/.claude`.** For 
our testing it is installed and run inside a **dev container** with its own isolated `~/.claude` (login persisted in the named volume
`sdlc-lite-claude`), which also has the pinned Python toolchain. Full lifecycle in
`DEVCONTAINER.md`. 

A *real end user* installs on their own machine — that path is the User Guide's job.

```bash
# On the Mac, from the repo root (Docker Desktop must be running):
devcontainer up --workspace-folder .          # build if needed + start (idempotent)
devcontainer exec --workspace-folder . bash   # shell inside
devcontainer exec --workspace-folder . claude # jump into Claude Code inside
```

The container's directory-source marketplace loads the plugin **from the workspace**
(`/workspaces/sdlc-lite/sdlc-lite-plugin/**`), not the `~/.claude/plugins/cache`
copy — so a workspace edit takes effect after a fresh container Claude session restart, with no
cache-sync step. Host unit tests (guard + analyzer, pytest-only): `python3 -m pytest
sdlc-lite-plugin -q`. The full pinned toolchain (ruff/mypy/mutmut) runs only in-container.

## When editing the product
- The **behavior lives in Markdown** (`SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`). Editing
  the workflow means editing these files, not writing code. The only real code is `guard.py` (the hook)
  and `analyzer/` (deterministic measurement, not orchestration — both allowed).
- Changing a gate's model/effort/tools → edit the matching `agents/*.md` frontmatter.
- Changing what an agent may read/write → update both the agent's prose inbox **and** `guard.py`
  (defense-in-depth: role instruction + hook enforcement).
