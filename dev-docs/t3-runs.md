# Hands-off T3 runs — `t3-run.sh` + tmux

A **T3 run** is the full dev-container dry run of `/implement-feature` against a fixture
([`verification-ladder.md`](verification-ladder.md#t3--the-dev-container-dry-run)). It is interactive:
the plugin STOPs for a human at its approval gates. This page describes how to run one where **the
agent does everything it can** and **the human only attaches, answers the STOPs, and attests** (#66).

The session runs in **tmux inside the dev container**. tmux keeps a terminal alive with no window
attached, so the agent can start it and read its screen, and the human can attach to the same
terminal from the Mac, detach, and come back. **tmux on the Mac is not needed**: you attach through
`docker exec`.

Prerequisites: those of [`DEVCONTAINER.md`](DEVCONTAINER.md) (Docker Desktop running, the
`devcontainer` CLI, `.env` with a token). The image must include tmux: after pulling this change,
run `make clean-run ARGS="--rebuild"` once. The `Toolchain` row of the status table shows the tmux
version.

---

## 1. The journey — who does what

The agent below is Claude Code on the Mac, in this repo (for example at `/feature` Gate 7).

| # | Who | What |
|---|---|---|
| 1 | Human | Asks the agent for a T3 run on a fixture ("run T3 on roman-numeral"), or `/feature` reaches Gate 7. |
| 2 | Agent | `make t3-start SLUG=roman-numeral`: `clean-run` (~20 s, status table green), pre-trusts the fixture dir, then starts tmux session `t3` running `claude --model opus "/implement-feature <BRIEF.md>"` in `/workspaces/roman-numeral-run`. |
| 3 | Agent | `make t3-peek` to confirm no login, trust or onboarding dialog; starts `make t3-watch` under its Monitor tool. |
| 4 | Agent | Posts the attach command: `make t3-attach`. |
| 5 | Human | Opens a Mac terminal tab in the repo, runs `make t3-attach`, and sees the session already working. |
| 6 | Agent | Reports in chat as events arrive: gates passed, isolated agents starting, guard denials, errors. |
| 7 | Agent → Human | At each STOP the agent posts "⏸ waiting for you" with the ask (and can summarize the handoff file). The human answers **in the tmux pane**. |
| 8 | Agent → Human | When the run ends the agent says so; the human detaches (`Ctrl-b d`) and attests what they saw. The agent runs `make t3-stop`. |

**The human does only what the agent cannot or must not:** type into the session (answer STOPs,
approve dialogs) and attest. The agent never types into the session (`tmux send-keys`), never answers
a STOP, and never marks T3 satisfied on its own ([`gates.md`](../.claude/sdlc/gates.md)).

**Without an agent**, the same commands work by hand: `make t3-start SLUG=<slug>`, then
`make t3-attach` in one tab and, optionally, `make t3-watch` in another.

The container stays up after `t3-stop`. The next `make clean-run` (or `t3-start`) removes it.

## 2. Commands

On the Mac, from the repo root. Each `make` target wraps `./t3-run.sh <subcommand>`; the script's
header comment is the full spec.

| `make` | Does |
|---|---|
| `make t3-start SLUG=<slug>` | Reset + fixture (`clean-run.sh <slug>`), pre-trust `/workspaces/<slug>-run`, start tmux session `t3` with the entry prompt from the fixture's `BRIEF.md`. |
| `make t3-attach` | Attach this terminal to the session. Same as `docker exec -it -u vscode -e TERM=xterm-256color sdlc-lite-test tmux attach -t t3`. |
| `make t3-peek` | Print the current screen, without attaching. |
| `make t3-watch` | Stream one line per change until the run ends (below). |
| `make t3-stop` | Kill the tmux session. The container is kept. |

Reading the run's files while it runs:
[`DEVCONTAINER.md` → Reading a fixture run's files](DEVCONTAINER.md#reading-a-fixture-runs-files-from-the-mac).

## 3. What `watch` reports

| Event | Source | Meaning |
|---|---|---|
| `GATE <gate> — <result>` | run-log, conductor record | A gate finished. |
| `AGENT <agent_type>` | run-log, guard record | An isolated agent made its first tool call. |
| `DENY <agent> <tool> <target>` | run-log, `guard_decision: deny` | The guard blocked a call. |
| `ERROR <conductor\|subagent> API: …` / `tool: …` | transcripts | An API error, or a failed non-Bash tool call. |
| `WORKING` | conductor transcript | The session is working. |
| `WAITING — <the ask>` | conductor transcript | The turn ended: the session waits for the human. Quotes the last paragraph of the conductor's message. |
| `WAITING (dialog) — …` | screen | A permission dialog or picker is open. |
| `ENDED` | tmux | `claude` exited (the final screen stays readable with `t3-peek`) or the session is gone. |

Limits, by design:
- **Failed Bash calls are not reported.** Red tests and probes exit non-zero on purpose.
- **Working / waiting is inferred,** and debounced over two 5 s polls. A dialog is detected by its
  on-screen text (`Do you want to`, `Would you like to`, `Enter to select`).
- **A restarted `watch` replays** the run's history, so earlier GATE lines repeat.
- The guard writes to `<fixture>/if-runlog.jsonl` until the conductor writes the `.active-run`
  pointer at Gate 0, then to `.implement-feature/<run>/handoff/run-log.jsonl`. `watch` reads both.

## 4. tmux in five minutes

**Model.** A tmux *server* owns *sessions*. A session keeps running whether or not a terminal is
*attached*. Attach to see and type into it; *detach* to leave it running. Here the server runs in
the container as user `vscode`, and the session is named `t3`.

**Keys.** Every tmux key starts with the *prefix* `Ctrl-b`: press it, release, then press the key.

| Keys / command | Does |
|---|---|
| `Ctrl-b d` | Detach. The session and `claude` keep running. |
| `Ctrl-b [` | Scroll mode (arrows / PgUp / PgDn; `q` to leave). The mouse wheel also scrolls. |
| `Ctrl-b ?` | List all key bindings (`q` to leave). |
| `tmux ls` | List sessions (in the container: `docker exec -u vscode sdlc-lite-test tmux ls`). |
| `tmux kill-session -t t3` | End the session (`make t3-stop`). |
| `tmux kill-server` | End every session and the server. Needed after editing the config. |

**In Claude Code, inside tmux:**
- **Shift+Enter** inserts a newline, thanks to `extended-keys` in the config.
- **Don't press Ctrl-C to clear the input:** pressed twice, it exits `claude`. Use Backspace.
- **Closing the terminal tab** is the same as detaching: the run keeps going. Re-attach with `make t3-attach`.

**Nested tmux.** If your Mac terminal is itself inside tmux, `Ctrl-b` goes to the *outer* tmux.
Press `Ctrl-b Ctrl-b d` to detach the inner (container) session.

**Copying text.** With `mouse on`, a plain mouse drag selects inside tmux and copies it to the Mac
clipboard through OSC 52. In iTerm2 this needs **Settings → General → Selection → "Applications in
terminal may access clipboard"**. To bypass tmux and use the terminal's own selection, hold
**Option** while dragging in iTerm2.

**Window size.** When more than one terminal is attached, tmux shrinks the session to the smallest
one.

**Config.** The container's `~/.tmux.conf` is [`.devcontainer/tmux.conf`](../.devcontainer/tmux.conf),
installed by `post-start.sh` on every container start. It turns on the mouse, a 50 000-line
scrollback, Shift+Enter (`extended-keys`), clipboard copy (`set-clipboard`), and `remain-on-exit` (the
pane stays after `claude` exits). A running server ignores edits: `make clean-run` (a new container)
applies them.

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| `no tmux session 't3'` | Nothing is running: `make t3-start SLUG=<slug>`. |
| `tmux: command not found`, or the `Toolchain` row is red | The image predates tmux: `make clean-run ARGS="--rebuild"`. |
| `t3-start` stops in `clean-run` | Fix the red row it names ([`DEVCONTAINER.md` → Clean run](DEVCONTAINER.md#clean-run--make-clean-run-before-every-dry-run)). |
| The session shows a trust or onboarding dialog | Report it: `t3-start` pre-trusts the fixture dir and `post-start.sh` seeds onboarding (#45). Answer it in the pane to continue. |
| `watch` says `ENDED` too early | `make t3-peek` shows the final screen (`remain-on-exit`). |
| Shift+Enter submits instead of a newline | The terminal must send extended keys (iTerm2 3.5+ does). Inside a Mac tmux, the Mac's `~/.tmux.conf` needs `extended-keys on` too. |
