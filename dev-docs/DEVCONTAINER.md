# Dev Container guide — how to run, manage, and tear down the sandbox

This repo uses a **dev container** so we can install and run the plugin inside an isolated Claude
Code, **without ever touching your Mac's `~/.claude`**. Config lives in `.devcontainer/` at the repo root.

- **Your code** always lives on the Mac (bind-mounted into the container) — never at risk.
- **Claude Code's login** lives in a Docker **named volume** `sdlc-lite-claude`
  (persists across rebuilds; separate from the Mac login).
- **The container itself** is disposable — remove and recreate freely.

> Prerequisite for everything below: **Docker Desktop must be running** (whale icon ready).
> Confirm with `docker ps`. The devcontainer CLI needs `npm i -g @devcontainers/cli` once.

---

## Lifecycle from the command line

Run these **on the Mac**, from the repo root (`~/dev/sdlc-lite`).

### Start / resume / get a shell
```bash
devcontainer up --workspace-folder .                    # build (if needed) + start; idempotent
devcontainer exec --workspace-folder . bash             # open a shell inside

# Jump straight into Claude Code, authenticated from .env (see "Authentication" below).
devcontainer exec --workspace-folder . bash -c \
  "set -a; source /workspaces/sdlc-lite/.env; set +a; claude"
```
`devcontainer up` is idempotent: existing-but-stopped → starts it; removed → recreates from the
cached image (fast, no rebuild) **unless** `.devcontainer/*` changed, in which case it rebuilds.

### Rebuild (only after editing `.devcontainer/Dockerfile` or `devcontainer.json`)
```bash
devcontainer up --workspace-folder . --build                       # rebuild, reuse cache
devcontainer up --workspace-folder . --remove-existing-container   # force a fresh container
devcontainer build --workspace-folder .                            # just build; surfaces errors early
```

### Find the container
It is always named **`sdlc-lite-test`** (`runArgs --name` in `devcontainer.json`), whatever path
the repo is cloned to. `docker ps -a --filter name=sdlc-lite-test` shows it.

### Fresh setup from zero (no container, image, or volume yet)
1. `docker ps` — confirms Docker Desktop is running.
2. `devcontainer up --workspace-folder .` — builds the image, starts the container, and creates the
   `sdlc-lite-claude` volume if absent. `post-start.sh` provisions `~/.claude` (see below).
3. Confirm the pinned toolchain installed cleanly:
   `devcontainer exec --workspace-folder . bash -c "ruff --version && mypy --version && pytest --version && claude --version"`.
4. Set up auth once (see **Authentication** below).
5. Start `claude` in the container and confirm `/implement-feature` resolves. No install is needed;
   the plugin loads live from the workspace (see **How the plugin loads** below).

Steps 2, 3 and 5 are also what `make clean-run` does and checks (next section).

### Clean run — `make clean-run` (before every dry run)
One command takes the machine to a known-good dry-run state and ends in a status table:
```bash
make clean-run                                  # reset + every fixture in test-fixtures/python-starter/
make clean-run ARGS="roman-numeral"             # reset + only the named fixture(s)
make clean-run ARGS="--rebuild"                 # also rebuild the image, no cache (~2 min)
```
It runs `./clean-run.sh` (the header comment is the full spec):

1. **Preflight:** Docker running, `devcontainer` CLI present, `.env` has a token.
2. **Reset:** `docker rm -f sdlc-lite-test`. The volume is kept, so the login survives. The image is
   kept too unless `--rebuild`.
3. **Up:** `devcontainer up`. A new container re-runs postCreate (toolchain) and `post-start.sh`.
4. **Settings:** `~/.claude/settings.json` is deleted and re-seeded from the template, so in-session
   `/config` and plugin toggles do not leak into the run.
5. **Fixtures:** `test-fixtures/setup-fixture.sh <slug>` for each.
6. **Status table:** Docker · volume · container · settings == template · plugin (a one-turn headless
   session loads `sdlc-lite:implement-feature` from the workspace — this also proves `.env` auth) ·
   toolchain versions · each fixture (on `main`, baseline intact, importable). Any ❌ row → exit 1
   with the fix on the row.

Removing the container is enough to reset: fixture run dirs and `~/.claude.json` live in the
container's own filesystem, and the plugin loads live, so nothing stale survives. Use `--rebuild`
only after a `Dockerfile` change or when the build cache is suspect. Re-running is idempotent
(~20 s). **Anything you left in the container — e.g. an in-progress `/workspaces/<slug>-run` — is
deleted.**

### Hands-off T3 run — `make t3-start` (#66)
For a full dry run, `make t3-start SLUG=<slug>` runs the clean run above, then starts
`/implement-feature` in a tmux session inside the container. You attach with `make t3-attach` and
answer the STOPs; an agent can launch it, watch it, and report progress. Journey, commands, and a
tmux primer: [`t3-runs.md`](t3-runs.md).

### Stop / remove / teardown — four levels, shallowest first
```bash
docker stop <container>                       # 1. stop (keep container, fs, volume)
docker rm -f <container>                       # 2. remove container (code + login untouched)
docker volume rm sdlc-lite-claude    # 3. drop the Claude login (container must be stopped/removed)
docker images && docker rmi <image>            # 4. drop the build cache (next up rebuilds from scratch)
```
Full walk-away: run 2 + 3 (+ optional 4). Blunt option: **Quit Docker Desktop** — stops everything
but deletes nothing.

### What persists through which action
| Action | Code (bind mount) | Container | Claude login (volume) | Image |
|---|---|---|---|---|
| `docker stop` | ✅ | stopped | ✅ | ✅ |
| Quit Docker Desktop | ✅ | stopped | ✅ | ✅ |
| `docker rm -f` | ✅ | ❌ | ✅ | ✅ |
| `make clean-run` | ✅ | new | ✅ (`settings.json` re-seeded) | ✅ (`--rebuild`: new) |
| `docker volume rm` | ✅ | (must be gone first) | ❌ | ✅ |
| `docker rmi` | ✅ | (must be gone first) | ✅ | ❌ |

Only removing the **volume** loses state you'd notice (you re-login). Code is never at risk.

### Claude Code UX inside the container (status line, hooks, settings)

The container's Claude gets a curated setup provisioned from the templates in
**`.devcontainer/claude/`** by **`.devcontainer/post-start.sh`**, which `devcontainer.json` runs as
its `postStartCommand` on every start (create, restart, rebuild). The script is idempotent by three
rules — **refresh** files we own outright, **seed** (only if absent) `settings.json`, **merge** the
first-run keys into `~/.claude.json` — and it is the commented source of truth for what lands where:

- **`statusline-command.sh`** + **`smart_rm_hook.sh`** are refreshed into `~/.claude/` on every
  start (static scripts — safe to overwrite). The status line shows dir · branch · `user@host` ·
  model · effort · context %; the smart-rm hook auto-allows `/tmp` + `*.tmp` deletions.
- **`settings.json`** is written **only if absent**, so a **fresh volume self-heals** but your
  in-session `/config` and plugin toggles are **never clobbered**. It ships: permissive sandbox
  permissions (`Bash(*)`, `defaultMode: auto`), the status line + smart-rm hook, `document-quality-pdf`
  off, and the enabled plugins/marketplaces (`sdlc-lite@sdlc-lite-dev` — the live directory-source
  channel of the plugin, see ADR-13; `mattpocock-skills`, `understand-anything`).
- **Intentionally NOT ported:** the Mac's `Stop` / `Notification` **osascript** alert hooks — they're
  macOS-only and meaningless in a headless container.

To re-apply the template after you've changed settings in-session: `rm ~/.claude/settings.json` and
restart the container (or copy `.devcontainer/claude/settings.json` in by hand).

### Two loosened Docker defaults — so Claude's Bash sandbox runs inside

`devcontainer.json` starts the container with `--security-opt seccomp=unconfined` and
`--security-opt systempaths=unconfined`. Claude Code wraps a sandboxed Bash command in
**bubblewrap**, which needs to create a user namespace (Docker's default seccomp profile blocks
`unshare(CLONE_NEWUSER)`) and mount a fresh `/proc` (the kernel refuses while Docker masks paths
in `/proc`). Without both, every sandboxed Bash call fails with
`bwrap: No permissions to create a new namespace` — which is what `claude plugin eval` runs for any
case that grants Bash (see [Running `plugin eval`](#running-plugin-eval-problems-and-fixes), problem 5).

The trade-off: the container ↔ VM-kernel boundary is looser (more syscalls allowed, `/proc`
unmasked). No capabilities are added, you are still not root, and the Docker Desktop VM still
separates it from macOS — far narrower than `--privileged`. Changing `runArgs` needs
`devcontainer up --workspace-folder . --remove-existing-container`.

## Running `plugin eval`: problems and fixes

`claude plugin eval` runs the plugin's eval cases (T1 on the
[verification ladder](verification-ladder.md)). Run it in this container. Five problems show up
when you do not. Each has a symptom, a cause and a fix.

### 1. "`plugin eval` is currently in early access"

- **Cause:** your `claude` is older than 2.1.281. Older builds turn the command off. They also
  reject the pinned model `claude-opus-5-5`.
- **Fix:** use the container. It pins `CLAUDE_VERSION=2.1.281` in `.devcontainer/Dockerfile`.

### 2. The first headless run waits for a trust prompt

- **Cause:** `plugin eval` runs the plugin's code and scaffold scripts as you. The first run in an
  untrusted plugin directory asks you to confirm.
- **Fix:** pass `--trust-plugin`. `release-verify.sh` already does.

### 3. "not granted (missing --allow-tools grant …)"

- **Cause:** a case lists the tools it wants in `allowed_tools` (in `prompt.md`). That is only a
  request. The operator must also grant each gated tool on the command line.
  `Read`, `Glob`, `Grep`, `Skill`, `TodoWrite` and `Agent` need no grant.
  `Bash`, `Write`, `Edit`, `WebFetch`, `WebSearch` and `mcp__*` do.
- **Fix:** pass `--allow-tools`. Put it last on the command line, because it takes a list.

A case is **Bash-granting** when both sides agree: the case asks for `Bash` and the operator grants
it. A narrow grant still counts:

| Grant | Bash-granting? |
|---|---|
| `--allow-tools Bash` | yes |
| `--allow-tools "Bash(pytest:*)"` | yes |
| `--allow-tools "Bash(printf:*)"` | yes |
| `--allow-tools Write Edit` | no |
| no grant (a read-only case) | no |

Every case that types `/implement-feature` is Bash-granting, because Gate 0 runs shell commands.
Problems 4 and 5 apply to Bash-granting cases only.

### 4. On the Mac: "a Bash-granting evaluation cannot run here"

The full error:

```
error: the Docker (~/.docker, DOCKER_CONFIG) credential store on this machine holds a symbolic
link inside it, so the Bash sandbox cannot reliably exclude it — a Bash-granting evaluation
cannot run here
```

- **Cause, step by step:**
  1. When Bash is granted, `plugin eval` wraps each Bash command in the OS sandbox (seatbelt on
     macOS, bubblewrap on Linux). The sandbox hides every credential store from the agent.
  2. `~/.docker` is a credential store. `~/.docker/config.json` has `auths` (registry
     credentials) and `credsStore` (a pointer to the Keychain helper).
  3. Docker Desktop puts symlinks in that directory. All 14 entries in `~/.docker/cli-plugins`
     are links into `/Applications/Docker.app`, and `docker-pass` is a credential helper:

     ```
     ~/.docker/cli-plugins/docker-buildx -> /Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx
     ~/.docker/cli-plugins/docker-pass   -> /Applications/Docker.app/Contents/Library/SecretsEngine/docker-pass.app/…/docker-pass
     ```
  4. A sandbox rule hides a path by its name. A symlink gives the same file a second name. The
     rules cannot say "hide everything that resolves here, under any name".
  5. The sandbox fails closed. If it cannot prove that it hides a credential store, it refuses to
     run. This is correct. Docker Desktop and the sandbox are both working as designed.
- **Fix:** run Bash-granting cases in this container. It has no Docker Desktop and no
  `~/.docker`.
- **What does not work:**
  - `DOCKER_CONFIG=<other dir>`. It only tells the docker CLI where to look. The sandbox still
    checks `~/.docker`. (Tested 2026-10-03: the same error.)
  - Deleting the symlinks. Docker Desktop recreates them, and `docker compose` breaks until it does.
- **Host runs:** read-only cases (routing, guard) run on the Mac. Use them for fast iteration on
  graders. A green host run is not a suite run. Run the suite in the container before you call a
  change verified.

### 5. In the container: "bwrap: No permissions to create a new namespace"

- **Cause:** the container is the right place, but Docker's default settings block bubblewrap.
  It must create a user namespace and mount a fresh `/proc`. The default seccomp profile and
  the masked `/proc` paths stop both. Every Bash call then fails. The agent reports "Bash is
  non-functional", and the case scores low for a reason that is not the plugin.
- **Fix:** `devcontainer.json` sets `--security-opt seccomp=unconfined` and
  `--security-opt systempaths=unconfined`. Keep both. After you change `runArgs`, recreate the
  container. The trade-offs are in "Two loosened Docker defaults" above.

### Run it

Full command and flags: [`sdlc-lite-plugin/evals/README.md`](../sdlc-lite-plugin/evals/README.md).

---

## Authentication — `.env` (both modes)

The container's Claude is a **separate login store** from your Mac's. Both the headless and the
interactive path authenticate from one file:

| Where | Path |
|---|---|
| On the Mac | `~/dev/sdlc-lite/.env` (repo root, **git-ignored**) |
| Inside the container | `/workspaces/sdlc-lite/.env` (same file, bind-mounted) |

**Set it up once** — copy the template and mint a token **on the Mac**:
```bash
cp .env.example .env
claude setup-token      # paste the output as CLAUDE_CODE_OAUTH_TOKEN=... in .env
```
`.env.example` documents the alternative (`ANTHROPIC_API_KEY`, API-billed — use one or the other).

**Nothing sources `.env` automatically.** Every command that needs auth must source it *inside* the
container — which also keeps the token out of host process arguments:

```bash
# Headless (what release-verify.sh does):
devcontainer exec --workspace-folder . bash -c \
  "set -a; source /workspaces/sdlc-lite/.env; set +a; claude -p 'reply with exactly: PONG'"

# Interactive:
devcontainer exec --workspace-folder . bash -c \
  "set -a; source /workspaces/sdlc-lite/.env; set +a; claude"
```

**Don't want a token?** Run `claude` in the container once and complete `/login` interactively. That
credential lands in `~/.claude/.credentials.json`, which **is** in the `sdlc-lite-claude` volume, so
it survives rebuilds. `.env` is still required for `release-verify.sh`, which runs headlessly.

### First-run state — why interactive used to look like an auth prompt (#54)

Claude Code keeps its first-run state (`hasCompletedOnboarding`, theme, per-project trust) in
**`~/.claude.json`** — at the **home root**, *outside* the mounted `~/.claude` volume. So it is
recreated empty on every container rebuild, and a bare interactive `claude` stopped at the theme
wizard and the folder-trust dialog. That is **not** an auth failure: the token authenticates both
modes either way.

`.devcontainer/post-start.sh` **merges** the keys in `.devcontainer/claude/claude.json` into
`~/.claude.json` on every start (`jq` deep merge: only those keys are set, everything else Claude
Code wrote is kept), so interactive sessions start clean. It is a merge, not an "only if absent"
seed, because the Dockerfile's `claude --version` already creates `~/.claude.json` in the image —
the original #54 seed never applied on a fresh container (#45).

- The merge pre-trusts **`/workspaces/sdlc-lite`** only. Starting Claude in a *different* directory
  still shows the one-time trust dialog — that's a deliberate safety prompt, not an auth issue.
- The merge re-applies on every start, so deleting `~/.claude.json` no longer brings the onboarding
  wizard back. A `/theme` change lasts until the next container start; to change it for good, edit
  `.devcontainer/claude/claude.json`.

### What persists where

| State | Location | In the `sdlc-lite-claude` volume? |
|---|---|---|
| `/login` credential | `~/.claude/.credentials.json` | ✅ |
| Settings, plugins, session history | `~/.claude/` | ✅ |
| Onboarding / theme / folder trust | `~/.claude.json` | ❌ — merged in each start |
| Token | `.env` on the Mac | n/a — bind-mounted, never copied in |

## How the plugin loads — three load paths

The plugin can reach a Claude session three ways. They can resolve skills differently, so a result
proven on one says nothing about the others (ADR-14 measured all three):

| Load path | Used by | Plugin source |
|---|---|---|
| **Directory marketplace** `sdlc-lite@sdlc-lite-dev` | container sessions (the default profile) | the workspace, `/workspaces/sdlc-lite/sdlc-lite-plugin/` |
| **`--plugin-dir`** | `claude plugin eval`, `verify-entry-points.py` | the path given |
| **Installed from the umbrella** `sdlc-lite@sdaas` | customers; `release-verify.sh` | a tag-pinned copy under `~/.claude/plugins/cache/sdaas/sdlc-lite/<version>/` |

The directory marketplace is registered by the seeded `settings.json` and needs **no
`claude plugin install`**. It loads **live from the workspace**: a workspace edit takes effect on the
next fresh Claude session, with no install and no cache sync. Verified on a fresh volume
([#45](https://github.com/Sdaas/sdlc-lite/issues/45), 2026-09-26): the session's init event reports
the plugin at `path: /workspaces/sdlc-lite/sdlc-lite-plugin` with `sdlc-lite:implement-feature`
registered, and a newly added `agents/*.md` file shows up in the next session. `claude plugin list`
still says "No plugins installed" — it lists installed (cached) plugins only, so ignore it for this
path. To check what a session actually loaded:

```bash
claude -p --output-format stream-json --verbose --max-turns 1 "reply ok" | head -1 | jq '.plugins'
```

## Two Claude profiles in one container (`CLAUDE_CONFIG_DIR`)

`CLAUDE_CONFIG_DIR` is where Claude Code keeps a profile (default `~/.claude`): login, `settings.json`,
registered marketplaces, installed plugins. Point it at another directory and you get a separate
profile on the same filesystem and toolchain. That lets one container be two environments:

| | `~/.claude` (default) — **dev** | `~/.claude-verify*` — **clean-room** |
|---|---|---|
| Marketplace | `sdlc-lite-dev` (directory source) | `sdaas` (umbrella, `git-subdir` from GitHub) |
| Plugin source | the workspace | the real GitHub release (tag-pinned) |
| Answers | "does my edit work?" | "does the shipped artifact work for a stranger?" |
| Python toolchain | shared — installed system-wide | shared — the same one |

`release-verify.sh` builds the clean-room profile fresh each run
([`verification-ladder.md`](verification-ladder.md) §8). No second container is needed.

## Entry-point check — `verify-entry-points.py`

Runs the 8-cell entry-point contract (ADR-14) against the working tree, on both load paths:

```bash
devcontainer exec --workspace-folder . python3 /workspaces/sdlc-lite/verify-entry-points.py               # 8 headless sessions, ~1 min
devcontainer exec --workspace-folder . python3 /workspaces/sdlc-lite/verify-entry-points.py --interactive # all 16, ~5 min
```

Run it after editing a skill's frontmatter/`description`, adding or renaming a command or skill,
changing the guard's `Skill` rule, or bumping the container's Claude Code version. Exit non-zero = a red cell.

Verdicts are transcript signatures, never a model judgment:

| # | Typed | Session | Green when the transcript shows |
|---|---|---|---|
| 1 | `/implement-feature` | headless | `Base directory for this skill`, no shim text |
| 2 | `/sdlc-lite:implement-feature` | headless | same |
| 3 | `/implement-feature` | `--interactive` | same |
| 4 | `/sdlc-lite:implement-feature` | `--interactive` | same |
| 5 | natural phrasing | headless | skill body never injected |
| 6 | natural phrasing | `--interactive` | skill body never injected |
| 7 | "invoke the Skill tool" | headless | a `Skill` call **and** the guard's explicit-entry denial |
| 8 | "invoke the Skill tool" | `--interactive` | same |

- Cells 5–6 test the as-shipped stack.
- Cells 7–8 test the guard alone: they use a copy with a neutral skill `description` (the real one
  makes the model refuse the call, so the guard goes unexercised).
- Proven red (claude 2.1.281): restoring the #55 shim reds cells 2 and 4; dropping `Skill` from the
  guard matcher reds 7–8.

## Reading a fixture run's files from the Mac

A fixture run lives in `/workspaces/<slug>-run/`, outside the bind mount, so its `.implement-feature/`
is not on the Mac ([fixtures](../test-fixtures/README.md)). Three ways to read a gate's file at a STOP:

| Way | How |
|---|---|
| `devcontainer exec` | `devcontainer exec --workspace-folder . cat /workspaces/<slug>-run/.implement-feature/<run>/handoff/draft/<file>.md` |
| VS Code | Command Palette → **Dev Containers: Attach to Running Container** → open `/workspaces/<slug>-run` ("Reopen in Container" shows only `sdlc-lite`) |
| `docker cp` | `docker cp sdlc-lite-test:/workspaces/<slug>-run/.implement-feature/<run>/handoff/draft/<file>.md ./review.md` |

---

## VS Code — Command Palette (⇧⌘P / Cmd-Shift-P)

Open the palette with **⇧⌘P**, type part of the command, hit Enter. The Dev Containers
extension (`ms-vscode-remote.remote-containers`) must be installed.

### Getting in / out
| Command | What it does |
|---|---|
| **Dev Containers: Reopen in Container** | Build (if needed) + reopen the current folder inside the container. The normal way in. |
| **Dev Containers: Reopen Folder Locally** | Leave the container, back to the Mac filesystem view. |
| **Dev Containers: Open Recent** *(or File → Open Recent)* | Reopen a folder already tagged `[Dev Container]`. |

### Building / rebuilding
| Command | When |
|---|---|
| **Dev Containers: Rebuild Container** | After editing `Dockerfile`/`devcontainer.json` — reuses cache. |
| **Dev Containers: Rebuild Without Cache and Reopen in Container** | Force a clean rebuild (features/base changed, cache suspect). |

### Inspecting / troubleshooting
| Command | Use |
|---|---|
| **Dev Containers: Show Container Log** | See the build/startup log (debug feature or postCreate failures). |
| **Dev Containers: Open Container Configuration File** | Jump to this repo's `devcontainer.json`. |
| **Dev Containers: Attach to Running Container** | Attach a window to a container you started via the CLI. |
| **Dev Containers: Open Named Volume in New Window** | Inspect the `sdlc-lite-claude` volume contents. |

### Everyday, once inside
| Command | Use |
|---|---|
| **Terminal: Create New Terminal** (**⌃`**) | Open a shell *inside* the container. Run `claude`, `git`, `pytest` here. |
| **Python: Select Interpreter** | Point VS Code at the container's Python if it doesn't auto-detect. |

**Auth in a VS Code terminal:** the preferred path is the `.env` token — `set -a; source
/workspaces/sdlc-lite/.env; set +a` before running `claude` (see **Authentication** above).
Alternatively run `claude` and complete `/login` once; that credential is saved in the named
volume, so most rebuilds won't ask again (occasional re-auth on token expiry is normal —
container login and Mac login are separate stores).
