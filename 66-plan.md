# 66-plan — Hands-off dev-container T3 runs

**Issue:** [#66](https://github.com/Sdaas/sdlc-lite/issues/66) · **Milestone:** `1.0.0-beta.3`
**Branch:** `66-hands-off-t3` · **Status:** P1–P3 done; P4 (docs) next

Branch-scoped working plan. `git rm` this file in the merge/close commit. Resume a fresh session
with **"read 66-plan.md and continue"**: check §6 for the next unticked phase.

---

## 1. Goal

For a T3 dry run, the agent does everything it can: it resets the container, sets up the fixture,
launches the session, watches it, and reports progress in chat. The human only attaches, answers the
plugin's STOPs, and attests. Proof: one full hands-off `roman-numeral` run.

**Out of scope:** answering STOPs / driving the gates (#34); reset mechanics (#21); fresh-boot
correctness (#45).

## 2. Locked decisions (2026-09-26)

| # | Decision | Why |
|---|---|---|
| D1 | **tmux runs inside the container** (Dockerfile apt package), config from a repo template `.devcontainer/tmux.conf` → `~/.tmux.conf`, refreshed by `post-start.sh`. | The session lives and dies with the container; every run gets the same config. |
| D2 | **tmux on the Mac is not required.** The human attaches with `docker exec -it -u vscode sdlc-lite-test tmux attach -t t3` (wrapped as `make t3-attach`). | No extra prerequisite. Every command and step is documented. |
| D3 | Keep tmux's default prefix `Ctrl-b`. Attaching from inside a Mac tmux is nested: document `Ctrl-b Ctrl-b d` to detach the inner session. | Least surprise. The user left the prefix question open; revisit only if nesting hurts in P5. |
| D4 | **Why tmux, not the alternatives:** permission prompts and dialogs appear only on screen until answered, so the agent needs to read the screen (`capture-pane`). Rejected: no multiplexer (no screen access), headless `claude -p` (not a real T3, and the agent would type for the human), `screen` (harder to script), ttyd / VS Code terminal (more moving parts, no screen read). | Grilled 2026-09-26. |
| D5 | **Script, not prose** (`t3-run.sh` + `make` targets). | Repeatable. The user's general rule: prefer a script over prose. |
| D6 | **The script passes `/implement-feature <BRIEF.md>` as `claude`'s first prompt.** The human does only what the agent cannot or must not do: answer STOPs and attest. | Matches the issue's Verification line. `verify-entry-points.py` already covers the check that only a human can start the workflow. |
| D7 | "Waiting for you" is detected by a **screen heuristic** (`capture-pane`); gates come from `run-log.jsonl`, which is reliable. | Accepted by the user. |
| D8 | **Teardown = kill the tmux session only.** The container stays; the next `clean-run` removes it. | Accepted by the user. |
| D9 | `t3-run.sh start` **pre-trusts the fixture dir** (`/workspaces/<slug>-run`) in `~/.claude.json`, the same jq merge `post-start.sh` does for `/workspaces/sdlc-lite`. | The template trusts only `/workspaces/sdlc-lite`, so the folder-trust dialog would otherwise appear on every run. It's our own fixture. |
| D10 | Docs: new **`dev-docs/t3-runs.md`** = the developer journey (§3), every command, and a short tmux tutorial (borrowed from the user's Evernote note "iTerm2 + tmux + Claude + Termius — Key Learnings": core commands, Shift+Enter `extended-keys` config, `kill-server` after a config change, smallest-client resize). Pointers from `DEVCONTAINER.md`, `test-fixtures/README.md`, `.claude/skills/feature/SKILL.md` Gate 7, and `verification-ladder.md` T3. | Single home for the practice. |

**Known risk:** the auto-mode classifier denied `tmux send-keys` into an interactive `claude` and
reading the container's `~/.claude.json` (#45). The design needs neither. `capture-pane` was allowed
on the Mac; P1 re-checks it through `docker exec`.

## 3. Developer journey (expected; P5 checks reality against it)

1. **Human**, in Claude Code on the Mac: "run T3 on roman-numeral", or `/feature` reaches Gate 7.
2. **Agent** runs `make t3-start SLUG=roman-numeral`: `clean-run` (~20 s, status table green),
   then tmux session `t3` inside the container, running
   `claude --model opus "/implement-feature <BRIEF>"` in `/workspaces/roman-numeral-run`.
3. **Agent** reads the screen (`make t3-peek`) to confirm there's no login, trust or onboarding
   dialog, then starts `t3-run.sh watch` under the Monitor tool.
4. **Agent** posts one command: `make t3-attach`.
5. **Human** opens an iTerm2 tab on the Mac, runs it, and sees the session already working.
6. **Agent** reports in chat: gates reached and passed; isolated agents starting; guard denials and
   errors.
7. At each STOP, **agent** posts "⏸ waiting for you: <STOP>" with a short summary of the handoff
   file. **Human** answers in the tmux pane.
8. When the run ends, **agent** says so and that the human can detach (`Ctrl-b d`), runs the
   analyzer receipt, asks for the attestation, then runs `make t3-stop`.

## 4. Script surface — `t3-run.sh` (repo root, runs on the Mac)

| Subcommand | `make` | Does |
|---|---|---|
| `start <slug>` | `t3-start SLUG=` | `./clean-run.sh <slug>`; pre-trust the fixture dir (D9); `tmux new-session -d -s t3` in the fixture dir, sourcing `.env`, running `claude --model opus "/implement-feature $(cat BRIEF.md)"`, with `remain-on-exit on`; print the attach command. Refuses if session `t3` exists. |
| `attach` | `t3-attach` | `docker exec -it -u vscode sdlc-lite-test tmux attach -t t3` (passes `TERM`). |
| `peek` | `t3-peek` | `capture-pane -p` of the current screen. |
| `watch` | `t3-watch` | Polls every ~10 s; prints **one line per change**: `GATE <gate> <result>` (new orchestration record), `AGENT <agent_type>` (first call from a new isolated agent), `DENY <agent> <tool> <target>`, `WAITING` / `WORKING` (screen: `esc to interrupt` present = working; prompt or `Do you want…` dialog = waiting), `ENDED` (claude exited / session gone). Designed for the Monitor tool. |
| `stop` | `t3-stop` | `tmux kill-session -t t3`. |

## 5. Phases

| Phase | Work | Verify | Commit |
|---|---|---|---|
| **P1** container tmux | Dockerfile `tmux`; `.devcontainer/tmux.conf` (`mouse on`, `extended-keys on`, `terminal-features 'xterm*:extkeys'`, larger `history-limit`); `post-start.sh` REFRESH installs it; `make clean-run ARGS=--rebuild`. | `tmux -V` in container; a `docker exec … tmux new -d` + `capture-pane` round trip is **allowed by the classifier** (record the result in memory). | `feat(devcontainer): install tmux + repo tmux.conf (#66)` |
| **P2** start / attach / peek / stop | `t3-run.sh` + `Makefile` targets; D9 pre-trust. | `shellcheck`; `t3-start` then `t3-peek` shows claude working on the brief with no dialog; human `t3-attach` works and Shift+Enter inserts a newline; `t3-stop` cleans up. | `feat(toolchain): t3-run.sh start/attach/peek/stop (#66)` |
| **P3** watch | `watch` subcommand. | Run under Monitor against a live session: GATE / AGENT / WAITING lines appear, no duplicates. | `feat(toolchain): t3-run.sh watch (#66)` |
| **P4** docs | `dev-docs/t3-runs.md` + the pointers (D10). | `./release-verify.sh --links-only`. | `docs(devcontainer): hands-off T3 runs + tmux primer (#66)` |
| **P5** proof | One full hands-off `roman-numeral` run following §3. Record deltas between journey and reality in §7; fix blocking ones. | Human attests: they only attached and answered STOPs. | fixes as needed |
| **P6** close | Final review; `git rm 66-plan.md`; `release-plan.md` (close #66, #53 next); merge; close #66. | — | `docs(release-plan): close #66; #53 next` |

Every commit waits for the human's review and approval.

## 6. Progress tracker

- [x] P1 container tmux — tmux 3.5a; `docker exec` new-session + capture-pane allowed (shell only; a live `claude` pane is re-checked in P2); `clean-run` Toolchain row now shows tmux
- [x] P2 start / attach / peek / stop — live: no trust/login/onboarding dialog; `capture-pane` of a live claude allowed; human attach + Shift+Enter newline + detach verified. Found + fixed: `clean-run.sh` failed without `--rebuild` on macOS bash 3.2 (empty array under `set -u`)
- [x] P3 watch — live through Gate 0 → Gate 1 STOP: GATE, WORKING, WAITING (quotes the ask), ENDED; AGENT / DENY / ERROR parsers checked on synthetic records (live in P5). Changed from the plan: "esc to interrupt" never matched, so working/waiting now comes from the conductor transcript (`system/turn_duration` = turn ended); a dialog on screen still wins. The ask comes from the transcript too
- [ ] P4 docs
- [ ] P5 proof run
- [ ] P6 close

## 7. Journey vs reality (filled in P5)

_Filled by the proof run. Early notes from the P2/P3 live checks:_

- Gate 1 asked all its interview questions in one message, not one at a time: fine, no change.
- The watcher replays the run's history when it (re)starts, so a restart mid-run repeats earlier GATE lines.
