# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Repo Contents

- Ships the `sdlc-lite` plugin: `/implement-feature` turns a one-line feature request into a
  reviewed, tested, committed Python change through an interview-driven, test-first,
  human-in-the-loop workflow. The slash command is registered by the skill itself (ADR-14).
- **`README.md`** — the single user-facing doc (install, setup, run, FAQ) for a real user on their
  own machine and repo. It routes developers to `dev-docs/` in one line.
- **`dev-docs/`** — for someone improving the plugin. See `dev-docs/README.md` for the map:
  - `developer-guide.md` — architecture, guard hook, analyzer, ADRs, design principles, testing.
  - `tutorial.md` — concepts + subagent isolation, with `toy-greet-plugin/` as the runnable example.
  - `DEVCONTAINER.md`, `verification-ladder.md`, `RELEASING.md`, `release-plan.md`,
    `issue-template.md`; `findings/` (settled investigations) and `proposals/` (unbuilt sketches).
- **Two channels (ADR-13):** this repo's root `.claude-plugin/marketplace.json` is the **dev**
  catalog (`sdlc-lite-dev`, live directory source; also holds the tutorial-only `toy-greet`). The
  **release** channel is the umbrella repo `Sdaas/claude-plugins` (`sdaas`) — customers
  `marketplace add Sdaas/claude-plugins` → `install sdlc-lite@sdaas`.

## Working conventions
- **Process:** plan → approve → phased execution. Commit per **logical unit**. Keep git history.
- **Before every commit:** give the user a concise list of the key files / changes to review, and
  wait for explicit approval. Never commit before the user has reviewed and approved.
- **Bar:** *genuinely usable* — a stranger can install from GitHub and run it against their own
  Python repo. "Done" = a **green end-to-end dry run in the dev container** (see
  `dev-docs/DEVCONTAINER.md`), not "docs exist."
- **Issue triage:** releases are GitHub **milestones** (`1.0.0-beta.1`, `1.0.0`, …); label issues by
  **type only** (`bug`/`enhancement`/`documentation`); **no milestone = backlog**. **Every issue you
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
- Temp/scratch files go to `/tmp/` or end in `.tmp`, deleted when done.

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
- **Host unit tests** (guard, policy, agentdefs, analyzer): `python3 -m pytest sdlc-lite-plugin -q`.
  The full pinned toolchain (ruff/mypy/mutmut) runs only in the container.
- **Link check:** `./release-verify.sh --links-only`. Test tiers: `dev-docs/verification-ladder.md`.

## When editing the product
Architecture, the guard hook's rules, and the ADRs are in `dev-docs/developer-guide.md`. The hard
rules:
- **Behavior lives in Markdown** (`SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`). The only
  real code is `guard.py` + `policy.py` (enforcement) and `analyzer/` + `agentdefs.py`
  (measurement) — code may enforce or measure, never orchestrate.
- **Isolated gates are spawned by the plugin-namespaced name** (`sdlc-lite:test-writer`), never the
  bare name.
- **Never add a `commands/<x>.md` whose name matches a `skills/<x>/` directory** — the command
  shadows the skill and `SKILL.md` silently never loads (ADR-14, #55).
- **This plugin's skills are explicit-entry only** — a human types the slash command; the model never
  auto-invokes them. `guard.py` denies `Skill` calls to them; the skill `description` says so too.
- **Change a gate's model/effort/tools** → edit the matching `agents/*.md` frontmatter (effort is
  frontmatter-only).
- **Change what an agent may read/write** → update both the agent's prose inbox **and** `policy.py`.
  `guard.py` and the analyzer both import `policy.py`, so there is nothing else to sync.
- **Change "green" or a threshold** → edit `references/quality-standards.md`, not individual briefs.
- **Core invariants** (also in `SKILL.md` → Rules): design and every review use a higher model than
  implementation; green unit tests are not "Done" (VERIFY drives the real code un-mocked); bound every
  automated loop; **never commit before human approval**.
