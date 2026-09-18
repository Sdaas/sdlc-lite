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
devcontainer exec --workspace-folder . claude           # jump straight into Claude Code
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

The container's Claude gets a curated setup provisioned from **`.devcontainer/claude/`** by the
`postStartCommand` (runs every start, idempotent):

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

**First-time login:** open a container terminal → run `claude` → follow the interactive OAuth
flow. The login is saved in the named volume, so most rebuilds won't ask again (occasional
re-auth on token expiry is normal; container login and Mac login are separate stores).
