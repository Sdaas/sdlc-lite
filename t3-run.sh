#!/usr/bin/env bash
#
# t3-run.sh — hands-off T3 dry runs: the agent launches and watches, the human attaches (#66).
#
# A T3 run is an interactive /implement-feature session inside the dev container. This
# script puts that session in a tmux session (`t3`) INSIDE the container, so the agent
# can read its screen and the human can attach to the same terminal from the Mac. No
# tmux is needed on the Mac: `attach` goes through `docker exec`.
# The full journey (who does what, when) is in dev-docs/t3-runs.md.
#
# SUBCOMMANDS
#   start <slug> [ENTRY=<prompt>] [VENV=1]
#                 1. ./clean-run.sh <slug> — reset the container, set up the fixture.
#                 2. Pre-trust /workspaces/<slug>-run in ~/.claude.json (jq merge, like
#                    post-start.sh does for /workspaces/sdlc-lite), so no trust dialog.
#                 2b. VENV=1 only (the /sdlc-init T3, #19): build ~/t3-venv in the container
#                    (no system site packages) with ruff==0.5.0 (under the floor) and the
#                    fixture installed editable; strip the run copy's [tool.mutmut],
#                    [tool.pytest.ini_options], [tool.coverage.run] tables and three of the
#                    /sdlc-init .gitignore lines (.coverage*, .implement-feature/,
#                    if-runlog.jsonl — mutants/ and *.egg-info/ stay: the editable
#                    install committed next would otherwise dirty the tree), and commit that so the tree is clean.
#                    claude then runs with the venv first on PATH: no mutmut, old ruff,
#                    unconfigured — what /sdlc-init has to fix.
#                 3. Start tmux session `t3` in the fixture dir, running
#                    claude --model opus "/implement-feature <BRIEF.md>"
#                    or, with ENTRY=<prompt> other than /implement-feature (e.g. /sdlc-init),
#                    claude --model opus "<ENTRY>" (no BRIEF).
#                    with .env sourced for auth. The script types the entry prompt; the
#                    human only answers the plugin's STOPs. Just before, it touches
#                    $START_MARKER in the container: `watch` reads only transcripts newer
#                    than it (#72).
#                 4. Print the attach command.
#   attach        Attach this terminal to the session (detach: Ctrl-b d).
#   peek          Print the session's current screen (what the human would see).
#   watch         Stream one line per change until the run ends — built for the agent's
#                 Monitor tool. The loop runs INSIDE the container (jq, the files) as
#                 `t3-run.sh _watch`; the Mac side only streams its output. Events:
#                   GATE    <gate> — <result>   a conductor record in the run-log
#                   AGENT   <agent_type>        the first tool call of an isolated agent
#                   DENY    <agent> <tool> …    a guard denial (run-log guard_decision)
#                   ERROR   <where>: …          an API error, or a failed non-Bash tool call.
#                                               Failed Bash is skipped: red tests and probes
#                                               exit non-zero by design.
#                   WORKING / WAITING …         a dialog on screen (permission, picker) =
#                                               waiting; else the conductor transcript: its
#                                               last turn ended (system/turn_duration) =
#                                               waiting, anything later = working. A turn
#                                               that ended while an isolated agent it
#                                               launched is still running = working (the
#                                               session waits for the agent). Debounced
#                                               over 2 polls; WAITING quotes the ask (the
#                                               last paragraph of the conductor's message)
#                   ENDED                       claude exited or the session is gone; exits 0
#                 Transcripts: only those newer than $START_MARKER — the projects dir
#                 is on the volume and keeps earlier runs' sessions, which are not
#                 replayed (nor deleted). No marker = every transcript, with a warning.
#                 Logs: the guard writes no log until the .active-run pointer exists
#                 (Gate 0), then .implement-feature/<run>/handoff/run-log.jsonl.
#   stop          Kill the tmux session. The container stays; the next clean-run removes it.
#
# Usage (on the Mac, from anywhere in the repo; Docker Desktop must be running):
#   ./t3-run.sh start roman-numeral
#   ./t3-run.sh start roman-numeral ENTRY=/sdlc-init VENV=1
#   ./t3-run.sh attach | peek | watch | stop
#   make t3-start SLUG=roman-numeral [ENTRY=/sdlc-init] [VENV=1]   ·   make t3-attach | t3-peek | t3-watch | t3-stop
#
set -euo pipefail

# ── config ───────────────────────────────────────────────────────────────────
CONTAINER="sdlc-lite-test"          # runArgs --name in devcontainer.json
SESSION="t3"
WS="/workspaces/sdlc-lite"
FIXTURES="test-fixtures/python-starter"
MODEL="opus"                        # same as test-fixtures/README.md → Run one
START_MARKER="/tmp/t3-start.marker" # in the container; clean-run recreates the container

die() { echo "t3-run.sh: $*" >&2; exit 1; }
usage() { sed -n '2,/^set -euo/{/^#/p;}' "$0"; }
# Run a command in the container as the dev user. Not `devcontainer exec`: it is slower
# and every subcommand except `start` only talks to the already-running tmux server.
dexec() { docker exec -u vscode "$CONTAINER" bash -c "$1"; }
has_session() { dexec "tmux has-session -t $SESSION 2>/dev/null"; }

# ── watch loop (runs INSIDE the container) ───────────────────────────────────
POLL="${T3_WATCH_INTERVAL:-5}"      # seconds between polls

emit() { printf '%s %s\n' "$(date +%H:%M:%S)" "$*"; }

# Run-log records → GATE / DENY lines, plus "AGENT_SEEN <type>" for the dedupe below.
# shellcheck disable=SC2016  # jq program, not shell
JQ_RUNLOG='
  if has("gate") and (has("tool") | not) then
    "GATE    \(.gate) — \((.result // "") | tostring | .[0:160])"
  elif .guard_decision == "deny" then
    "DENY    \(if (.agent_type // "") == "" then "conductor" else .agent_type end) \(.tool) \((.target // "") | tostring | .[0:140])"
  elif (.agent_type // "") != "" then "AGENT_SEEN \(.agent_type)"
  else empty end'
# Transcript records → ERROR lines. $where = conductor | subagent.
# shellcheck disable=SC2016
JQ_TRANSCRIPT='
  if .isApiErrorMessage == true then
    "ERROR   \($where) API: \([.message.content[]? | .text? // empty] | join(" ") | .[0:160])"
  else
    (.message.content[]? | select(type == "object" and .type == "tool_result" and .is_error == true)
     | (.content | if type == "array" then map(.text? // "") | join(" ") else tostring end)
     | select(test("^Exit code [0-9]+") | not)
     | "ERROR   \($where) tool: \(split("\n")[0] | .[0:160])")
  end'

# Conductor transcript → busy / idle per record; the last one is the session's state.
JQ_TURN='
  if .type == "system" and .subtype == "turn_duration" then "idle"
  elif .type == "assistant" or .type == "user" then "busy"
  else empty end'

# The ask: the last paragraph of the conductor's last text message, on one line.
JQ_ASK='
  select(.type == "assistant") | [.message.content[]? | select(.type == "text") | .text]
  | select(length > 0) | join("\n\n") | split("\n\n") | map(select(test("\\S"))) | last // empty
  | gsub("\\s+"; " ")'

# Isolated agents the conductor launched that have not reported back. A launch is the
# Agent tool_result "Async agent launched"; a finish (completed, failed or killed) is a
# <task-notification> naming the same tool-use id. Prints the count.
pending_agents() {
  local main="$1" launched finished
  launched="$(grep -F 'Async agent launched' "$main" 2>/dev/null \
    | jq -r '.message.content[]? | select(.type? == "tool_result") | .tool_use_id' 2>/dev/null | sort -u)"
  finished="$(grep -F '<task-notification>' "$main" 2>/dev/null \
    | grep -oE '<tool-use-id>[^<]+' | cut -d'>' -f2 | sort -u)"
  comm -23 <(printf '%s\n' "$launched") <(printf '%s\n' "$finished") | grep -c . || true
}

declare -A OFFSET SEEN 2>/dev/null || true   # bash 4+ (the container); unused on the Mac

# Set BUF to every COMPLETE new line of file $1 since the last call (a line still being
# written has no newline yet: `read` skips it and the next poll picks it up whole).
# Fills a global, not stdout: a pipeline would run it in a subshell and lose OFFSET.
new_lines() {
  local f="$1" off="${OFFSET[$1]:-0}" n=0 line
  BUF=""
  while IFS= read -r line; do n=$((n + 1)); BUF+="$line"$'\n'; done \
    < <(tail -n +"$((off + 1))" "$f" 2>/dev/null)
  OFFSET[$f]=$((off + n))
}

watch_loop() {
  tmux has-session -t "$SESSION" 2>/dev/null || { emit "ENDED   no tmux session '$SESSION'"; return 0; }
  local run tdir state="" cand="" hold=0 f where out screen now last main
  local -a newer=()
  run="$(tmux display -p -t "$SESSION" '#{pane_current_path}')"
  tdir="$HOME/.claude/projects/${run//[^a-zA-Z0-9]/-}"
  emit "WATCH   $run (poll ${POLL}s)"
  # The projects dir outlives clean-run (it is on the volume): skip earlier runs' sessions.
  if [[ -f "$START_MARKER" ]]; then
    newer=(-newer "$START_MARKER")
  else
    emit "WATCH   no $START_MARKER (not started by t3-run.sh start?) — reading every transcript"
  fi
  while :; do
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then emit "ENDED   session gone"; return 0; fi

    for f in "$run/if-runlog.jsonl" "$run"/.implement-feature/*/handoff/run-log.jsonl; do
      [[ -f "$f" ]] || continue
      new_lines "$f"
      out="$(jq -r "$JQ_RUNLOG" 2>/dev/null <<<"$BUF")" || true
      while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        if [[ "$line" == AGENT_SEEN\ * ]]; then
          local t="${line#AGENT_SEEN }"
          [[ -n "${SEEN[$t]:-}" ]] && continue
          SEEN[$t]=1; emit "AGENT   $t"
        else
          emit "$line"
        fi
      done <<<"$out"
    done

    while IFS= read -r -d '' f; do
      where="conductor"; [[ "$f" == */subagents/* ]] && where="subagent"
      new_lines "$f"
      out="$(jq -r --arg where "$where" "$JQ_TRANSCRIPT" 2>/dev/null <<<"$BUF")" || true
      while IFS= read -r line; do [[ -n "$line" ]] && emit "$line"; done <<<"$out"
    done < <(find "$tdir" -name '*.jsonl' "${newer[@]}" -print0 2>/dev/null)

    if [[ "$(tmux display -p -t "$SESSION" '#{pane_dead}')" == 1 ]]; then
      emit "ENDED   claude exited — the final screen stays readable (peek)"; return 0
    fi
    screen="$(tmux capture-pane -p -J -t "$SESSION")"
    # A dialog is on screen only (not yet in the transcript), so it wins. Otherwise the
    # conductor transcript decides: a turn ends with a system/turn_duration record. A turn
    # that ends right after launching an isolated agent waits for the agent, not the human.
    # xargs -r: before this run writes a transcript there is no main (bare `ls` lists the cwd).
    main="$(find "$tdir" -maxdepth 1 -name '*.jsonl' "${newer[@]}" -print0 2>/dev/null | xargs -0 -r ls -t 2>/dev/null | head -1)"
    if grep -qE 'Do you want to|Would you like to|Enter to select' <<<"$screen"; then
      now="WAITING (dialog)"
    elif [[ -n "$main" ]] && [[ "$(tail -n 300 "$main" | jq -r "$JQ_TURN" 2>/dev/null | tail -1)" == busy ]]; then
      now="WORKING"
    elif [[ -n "$main" ]] && [[ "$(pending_agents "$main")" -gt 0 ]]; then
      now="WORKING"
    else
      now="WAITING"
    fi
    # Debounce: a state must hold two polls in a row before it is announced.
    if [[ "$now" == "$cand" ]]; then hold=$((hold + 1)); else cand="$now"; hold=1; fi
    if [[ "$hold" -ge 2 && "$cand" != "$state" ]]; then
      state="$cand"
      if [[ "$state" == WAITING* ]]; then
        if [[ "$state" == "WAITING (dialog)" ]]; then
          last="$(grep -E 'Do you want to|Would you like to|\?' <<<"$screen" | tail -1 | sed 's/^[[:space:]│●]*//' | cut -c1-200)"
        else
          last="$(tail -n 300 "$main" | jq -r "$JQ_ASK" 2>/dev/null | tail -1 | cut -c1-200)"
        fi
        emit "$state${last:+ — $last}"
      else
        emit "$state"
      fi
    fi
    sleep "$POLL"
  done
}

cmd="${1:-}"
[[ -n "$cmd" ]] || { usage; exit 2; }
shift

# The in-container half of `watch`: no repo, docker or git needed.
if [[ "$cmd" == _watch ]]; then watch_loop; exit 0; fi

cd "$(git rev-parse --show-toplevel)"

case "$cmd" in
  start)
    [[ $# -ge 1 ]] || die "usage: ./t3-run.sh start <slug> [ENTRY=<prompt>] [VENV=1]"
    slug="$1"; shift
    entry="/implement-feature"; venv=""
    for opt in "$@"; do
      case "$opt" in
        ENTRY=*) entry="${opt#ENTRY=}" ;;
        VENV=*)  venv="${opt#VENV=}" ;;
        *) die "unknown option: $opt (ENTRY=<prompt> | VENV=1)" ;;
      esac
    done
    [[ -n "$entry" ]] || entry="/implement-feature"
    [[ -d "$FIXTURES/$slug" ]] || die "no such fixture: $FIXTURES/$slug"
    run="/workspaces/${slug}-run"

    ./clean-run.sh "$slug"

    if [[ "$venv" == 1 ]]; then
      echo
      echo "── t3: VENV=1 — ~/t3-venv, run copy stripped of /sdlc-init config ──"
      # The run copy is a git repo on main (setup-fixture.sh); commit the stripped state so
      # `git status` starts clean and /sdlc-init's own changes are the only diff.
      dexec "set -euo pipefail
rm -rf ~/t3-venv
python -m venv ~/t3-venv
~/t3-venv/bin/pip install --quiet ruff==0.5.0
~/t3-venv/bin/pip install --quiet -e $run
cd $run
python - <<'PY'
import re, pathlib
p = pathlib.Path('pyproject.toml')
s = p.read_text()
for t in ('tool.mutmut', 'tool.pytest.ini_options', 'tool.coverage.run'):
    s = re.sub(r'\n?\[' + re.escape(t) + r'\]\n(?:(?!\[).*\n?)*', '\n', s)
p.write_text(s.rstrip('\n') + '\n')
g = pathlib.Path('.gitignore')
drop = {'.coverage*', '.implement-feature/', 'if-runlog.jsonl'}
g.write_text(''.join(l for l in g.read_text().splitlines(True) if l.strip() not in drop))
PY
git add -A
git commit -q -m 'fixture baseline: stripped of /sdlc-init config'
[[ -z \"\$(git status --porcelain)\" ]]"
      echo "  ~/t3-venv ready; run copy committed clean"
    fi

    echo
    echo "── t3: pre-trust $run ─────────────────────────────────────────────"
    # Merge one key; leave everything Claude Code wrote. Nothing is printed from the file.
    dexec "set -euo pipefail
tmp=\$(mktemp /tmp/claude-json.XXXXXX)
jq --arg d '$run' '.projects[\$d].hasTrustDialogAccepted = true' ~/.claude.json > \"\$tmp\"
install -m 600 \"\$tmp\" ~/.claude.json
rm -f \"\$tmp\""
    echo "  trusted"

    echo
    echo "── t3: launch tmux session '$SESSION' ─────────────────────────────"
    # `watch` reads only transcripts newer than this, i.e. this run's (#72).
    dexec "touch $START_MARKER"
    # devcontainer exec (not docker exec) so the tmux server — and so claude — gets the
    # container's remoteEnv (DISABLE_AUTOUPDATER). BRIEF.md is read inside the fixture.
    # shellcheck disable=SC2016  # $(cat BRIEF.md) expands inside the tmux pane, on purpose
    if [[ "$entry" == "/implement-feature" ]]; then
      prompt='"/implement-feature $(cat BRIEF.md)"'
    else
      prompt="\"$entry\""
    fi
    pre=""
    if [[ "$venv" == 1 ]]; then
      # shellcheck disable=SC2016  # $HOME expands inside the tmux pane, on purpose
      pre='export PATH=$HOME/t3-venv/bin:$PATH VIRTUAL_ENV=$HOME/t3-venv; '
    fi
    launch="${pre}"'set -a; source '"$WS"'/.env; set +a; exec claude --model '"$MODEL"' '"$prompt"
    devcontainer exec --workspace-folder . \
      tmux new-session -d -s "$SESSION" -x 200 -y 50 -c "$run" "$launch" >/dev/null
    has_session || die "tmux session '$SESSION' did not start"
    echo "  started: claude --model $MODEL ${prompt//\$(cat BRIEF.md)/<$slug BRIEF.md>} in $run${venv:+ (venv ~/t3-venv)}"
    echo
    echo "Attach from a Mac terminal (repo root):  make t3-attach"
    echo "   or:  docker exec -it -u vscode -e TERM=xterm-256color $CONTAINER tmux attach -t $SESSION"
    echo "Detach: Ctrl-b d  (inside a Mac tmux: Ctrl-b Ctrl-b d)"
    ;;

  attach)
    has_session || die "no tmux session '$SESSION' — start one with: make t3-start SLUG=<slug>"
    # TERM is fixed: iTerm2 and Terminal.app both speak xterm-256color, the container has
    # its terminfo, and tmux.conf's extended-keys rule matches it.
    exec docker exec -it -u vscode -e TERM=xterm-256color "$CONTAINER" tmux attach -t "$SESSION"
    ;;

  peek)
    has_session || die "no tmux session '$SESSION'"
    dexec "tmux capture-pane -p -J -t $SESSION"
    ;;

  watch)
    has_session || die "no tmux session '$SESSION'"
    # No -t: plain streamed stdout, one event per line, for the Monitor tool.
    exec docker exec -u vscode -e T3_WATCH_INTERVAL="$POLL" "$CONTAINER" bash "$WS/t3-run.sh" _watch
    ;;

  stop)
    if has_session; then
      dexec "tmux kill-session -t $SESSION"
      echo "t3: session '$SESSION' killed (container kept)"
    else
      echo "t3: no session '$SESSION' to stop"
    fi
    ;;

  -h|--help) usage ;;
  *) die "unknown subcommand: $cmd (start <slug> [ENTRY=…] [VENV=1] | attach | peek | watch | stop)" ;;
esac
