# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Repo Contents

- Ships the `sdlc-lite` plugin: `/implement-feature` turns a one-line feature request into a
  reviewed, tested, committed Python change through an interview-driven, test-first,
  human-in-the-loop workflow; `/sdlc-init` sets a Python repo up for it (toolchain + config). Each
  slash command is registered by its skill (ADR-14).
- **`README.md`** — the single user-facing doc (install, setup, run, FAQ) for a real user on their
  own machine and repo. Developers are routed to `dev-docs/`.
- **`dev-docs/`** — for someone improving the plugin. See `dev-docs/README.md` for the map:
  - `tutorial.md` — concepts + subagent isolation, with `toy-greet-plugin/` as the runnable example.
  - `developer-guide.md` — the hub: change → edit → verify table, review checklist, repo-local skills.
  - `repo-local-skills.md` — `/issue`, `/feature`, `/fix`, `/review-repo`: gates, STOPs, when each fires.
  - `architecture.md` — gates, handoff, model pins, guard rules, analyzer. `adr/` — the ADRs.
  - `DEVCONTAINER.md`, `ACCEPTANCE.md` (the acceptance container), `verification-ladder.md`, `RELEASING.md`, `release-plan.md`,
    `issue-template.md`; `findings/` (settled investigations) and `proposals/` (unbuilt sketches).
- **Two channels (ADR-13):** this repo's root `.claude-plugin/marketplace.json` is the **dev**
  catalog (`sdlc-lite-dev`, live directory source; also holds the tutorial-only `toy-greet`). The
  **release** channel is the umbrella repo `Sdaas/claude-plugins` (`sdaas`) — customers
  `marketplace add Sdaas/claude-plugins` → `install sdlc-lite@sdaas`.

## Working conventions
- **Repo-local skills** (`.claude/skills/`, human-typed only): filing an issue → `/issue`; an
  `enhancement` → `/feature #NN`; a `bug` → `/fix #NN`; full-repo review → `/review-repo <version>`. Shared process: `.claude/sdlc/gates.md`.
  Gates, STOPs, routing: `dev-docs/repo-local-skills.md`.
- **Process:** plan → approve → phased execution. Commit per **logical unit**. Keep git history.
- **Before every commit:** give the user a concise list of the key files / changes to review, and
  wait for explicit approval. Never commit before the user has reviewed and approved.
- **Bar:** *genuinely usable* — a stranger can install from GitHub and run it against their own
  Python repo. "Done" = a **green end-to-end dry run in the dev container** (see
  `dev-docs/DEVCONTAINER.md`), not "docs exist."
- **Issue triage:** releases are GitHub **milestones** (`0.1.0`, `1.0.0`, …); label issues by
  **type only** (`bug`/`enhancement`/`documentation`); **no milestone = backlog**. Each release in `release-plan.md` sorts its issues into **four themes**
(customer features · customer fixes · internal SDLC improvements · internal SDLC fixes; see
`RELEASING.md` §3). **Every issue you
  file must follow `dev-docs/issue-template.md`** (required structure, ~300-word cap, no
  transcripts). Full conventions + release procedure: `dev-docs/RELEASING.md`.
- **Planning docs (two kinds):**
  - **`dev-docs/release-plan.md`** — the roadmap for the current + next release: the **narrative**
    *plus* the **execution order** of the milestone's issues. **GitHub is the SSOT for *which*
    issues ship**; `release-plan.md` only adds the order, referencing each issue as **`#NN` + its
    title as a convenience copy** — never copy an issue's *spec* into it. Titles can drift; GitHub
    wins. Resumable with **"read release-plan.md and continue."**
  - **`<NN>-plan.md`** — a per-issue working plan (e.g. `41-plan.md`), created **only when the work
    is plan-mode-worthy** (multiple sessions, multiple phases, or structurally complex; otherwise the
    GitHub issue is the plan). It carries the locked decisions, the phased plan with testing, and a
    progress tracker. **Checked in on the feature branch, `git rm`'d in the merge/close commit.**
- **Two audiences — write each file for its reader** (detail: `dev-docs/developer-guide.md` §5):
  - **Agent-read** (`SKILL.md`, `agents/*.md`, `references/*`, `.claude/skills/`,
    `.claude/sdlc/gates.md`, `CLAUDE.md`): precise, and tuned for the pinned model.
  - **Human-read** (`README.md`, `tutorial.md`, `developer-guide.md`, `architecture.md`,
    `DEVCONTAINER.md`, `ACCEPTANCE.md`, `RELEASING.md`, `CHANGELOG.md`): **ASD-STE100 at about 80%** — short
    sentences, active voice, one word for one meaning, imperative steps. A mermaid diagram only for
    the gate flow and the isolation model. No HTML pages.
  - ADRs, `findings/`, `proposals/` and `review-YYYYMMDD.md` are historical records. Do not rewrite
    their prose.
- **Temp files:** throwaway working files (scripts, intermediate data) go to `/tmp/` or the session
  scratchpad, or end in `.tmp`, and are deleted when done. **Anything the user is meant to read**
  (reports, findings, drafts, diffs, command output) is written to the **repo root** as
  `<name>.md.tmp` (gitignored via `*.tmp`) and left in place for review. Delete every root
  `*.md.tmp` with plain `rm` in the merge/close commit step, alongside `git rm <NN>-plan.md`.

## Running / testing
- **Never install the plugin into the Mac's global `~/.claude`.** Development runs happen in the
  **dev container** (own `~/.claude`, pinned Python toolchain). Lifecycle, auth and plugin load
  paths: `dev-docs/DEVCONTAINER.md`.
  ```bash
  # On the Mac, from the repo root (Docker Desktop must be running):
  devcontainer up --workspace-folder .
  devcontainer exec --workspace-folder . bash -c \
    "set -a; source /workspaces/sdlc-lite/.env; set +a; claude"
  ```
- **Two containers — never conflate them.** The **dev container** (`sdlc-lite-test`,
  `.devcontainer/`) is for all development and testing. The **acceptance container**
  (`sdlc-lite-acceptance`, `./acceptance.sh`, `acceptance/`) is a stranger's machine for a release's
  human run only: no mounts, no toolchain, no plugin, latest claude. Never develop, run evals or T3 in
  it, and never pre-install anything a user step should do. Its evidence: `./acceptance.sh logs` →
  `acceptance-logs.tmp/`. Purpose, user steps, rules: `dev-docs/ACCEPTANCE.md`.
- **Host unit tests** (guard, policy, agentdefs, analyzer): `python3 -m pytest sdlc-lite-plugin -q`.
  The full pinned toolchain (ruff/mypy/mutmut) runs only in the container.
- **Link check:** `./release-verify.sh --links-only`. Test tiers: `dev-docs/verification-ladder.md`.

## When editing the product
What to edit for a given change, and how to verify it: `dev-docs/developer-guide.md` §2. Architecture:
`dev-docs/architecture.md`. ADRs: `dev-docs/adr/`. The hard rules:
- **Behavior lives in Markdown** (`SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`). The only
  real code is `guard.py` + `policy.py` (enforcement) and `analyzer/` + `agentdefs.py` + `toolchain/setup_check.py`
  (measurement) — code may enforce or measure, never orchestrate.
- **Isolated gates are spawned by the plugin-namespaced name** (`sdlc-lite:test-writer`), never the
  bare name.
- **Never add a `commands/<x>.md` whose name matches a `skills/<x>/` directory** — the command
  shadows the skill and `SKILL.md` silently never loads (ADR-14, #55).
- **This plugin's skills are explicit-entry only** — a human types the slash command; the model never
  auto-invokes them. `guard.py` denies `Skill` calls to them; the skill `description` says so too.
- **Agent read/write rules change in two places:** the agent's prose inbox **and** `policy.py`.
- **Core invariants** (also in `SKILL.md` → Rules): design and every review use a higher model than
  implementation; green unit tests are not "Done" (VERIFY drives the real code un-mocked); bound every
  automated loop; **never commit before human approval**.
