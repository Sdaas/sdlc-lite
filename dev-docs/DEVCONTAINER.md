# Dev Container guide — how to run, manage, and tear down the sandbox

This repo uses a **dev container** so we can install and run the plugin (and later the
code-writing `/implement-feature` product) inside an isolated Claude Code, **without ever
touching your Mac's `~/.claude`**. Config lives in `.devcontainer/` at the repo root.

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

### Find the container (no fixed name — the CLI names it)
```bash
docker ps -a --filter "label=devcontainer.local_folder=$(pwd)"
```

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
| `docker volume rm` | ✅ | (must be gone first) | ❌ | ✅ |
| `docker rmi` | ✅ | (must be gone first) | ✅ | ❌ |

Only removing the **volume** loses state you'd notice (you re-login). Code is never at risk.

### Claude Code UX inside the container (status line, hooks, settings)

The container's Claude gets a curated setup provisioned from the templates in
**`.devcontainer/claude/`** by **`.devcontainer/post-start.sh`**, which `devcontainer.json` runs as
its `postStartCommand` on every start (create, restart, rebuild). The script is idempotent by two
rules — **refresh** files we own outright, **seed** (only if absent) files Claude Code writes to —
and it is the commented source of truth for what lands where:

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
case that grants Bash ([`eval-tutorial.md`](eval-tutorial.md) § 1).

The trade-off: the container ↔ VM-kernel boundary is looser (more syscalls allowed, `/proc`
unmasked). No capabilities are added, you are still not root, and the Docker Desktop VM still
separates it from macOS — far narrower than `--privileged`. Changing `runArgs` needs
`devcontainer up --workspace-folder . --remove-existing-container`.

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

`.devcontainer/post-start.sh` now seeds `~/.claude.json` from `.devcontainer/claude/claude.json`
**only if absent** (same self-healing rule as `settings.json`), so interactive sessions start clean.

- The seed pre-trusts **`/workspaces/sdlc-lite`** only. Starting Claude in a *different* directory
  still shows the one-time trust dialog — that's a deliberate safety prompt, not an auth issue.
- To re-run the onboarding wizard: `rm ~/.claude.json` and restart the container.

### What persists where

| State | Location | In the `sdlc-lite-claude` volume? |
|---|---|---|
| `/login` credential | `~/.claude/.credentials.json` | ✅ |
| Settings, plugins, session history | `~/.claude/` | ✅ |
| Onboarding / theme / folder trust | `~/.claude.json` | ❌ — re-seeded each start |
| Token | `.env` on the Mac | n/a — bind-mounted, never copied in |

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
