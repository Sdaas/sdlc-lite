#!/usr/bin/env bash
#
# acceptance.sh — the ACCEPTANCE CONTAINER: a stranger's machine for a release's human run (#100).
#
# NOT the dev container. Two containers exist; never mix them up:
#   • dev container  (sdlc-lite-test, .devcontainer/)  — develop and test the plugin. Mounts this
#     repo, pre-installs the pinned toolchain, live-loads the plugin from the workspace.
#   • acceptance container (sdlc-lite-acceptance, acceptance/) — THIS script. Mounts nothing, has no
#     plugin, no toolchain, no login. A human installs the RELEASED plugin from GitHub by following
#     README.md alone, then runs /sdlc-init and /implement-feature on ~/mypackage.
#
# Purpose, constraints, what NOT to use it for, and the user's step list: dev-docs/ACCEPTANCE.md.
#
# This script only builds, enters, collects from and removes the container. It never performs a
# user step (venv, plugin install, login, /sdlc-init) — those steps ARE the test.
#
# Usage (on the Mac, from the repo root; Docker Desktop must be running):
#   ./acceptance.sh up      # build the image fresh (latest Claude Code) and start the container
#   ./acceptance.sh shell   # open a shell in it as user "stranger", in ~/mypackage
#   ./acceptance.sh logs    # copy run evidence to ./acceptance-logs.tmp/ (for debugging)
#   ./acceptance.sh down    # remove the container and the image
#
set -euo pipefail

NAME="sdlc-lite-acceptance"           # container AND image name
HOME_IN="/home/stranger"
REPO_IN="$HOME_IN/mypackage"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT="$ROOT/acceptance"
LOGS="$ROOT/acceptance-logs.tmp"

die() { echo "acceptance.sh: $*" >&2; exit 1; }
exists() { docker container inspect "$NAME" >/dev/null 2>&1; }
running() { [[ "$(docker container inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" == "true" ]]; }
# Run a command in the container as the stranger, in a login-free non-interactive bash.
inside() { docker exec -u stranger -w "$REPO_IN" "$NAME" bash -c "$1"; }

usage() { sed -n '/^# Usage/,/^#$/p' "$0" | sed 's/^# \{0,1\}//'; }

cmd_up() {
  exists && die "container '$NAME' already exists. Use './acceptance.sh shell', or './acceptance.sh down' for a fresh start."
  echo "→ building image '$NAME' (fresh: --pull --no-cache, so Claude Code is the latest) …"
  docker build --pull --no-cache -t "$NAME" "$CONTEXT"
  echo "→ starting container '$NAME' (no mounts, no auth, no plugin) …"
  docker run -d --name "$NAME" --hostname acceptance "$NAME" >/dev/null
  echo
  echo "✅ acceptance container is up. Claude Code: $(inside 'claude --version' 2>/dev/null || echo '?')"
  echo "   Next: ./acceptance.sh shell — then follow dev-docs/ACCEPTANCE.md §4."
}

cmd_shell() {
  exists || die "no container '$NAME'. Run './acceptance.sh up' first."
  running || docker start "$NAME" >/dev/null
  exec docker exec -it -u stranger -w "$REPO_IN" "$NAME" bash
}

cmd_logs() {
  exists || die "no container '$NAME'. Nothing to collect."
  running || docker start "$NAME" >/dev/null
  rm -rf "$LOGS"; mkdir -p "$LOGS"
  # Session transcripts and the plugin's run folder (handoff files + run-log.jsonl). Never
  # ~/.claude.json or ~/.claude/.credentials.json.
  docker cp "$NAME:$HOME_IN/.claude/projects" "$LOGS/transcripts" 2>/dev/null \
    || echo "(no transcripts yet)" > "$LOGS/transcripts.missing"
  docker cp "$NAME:$REPO_IN/.implement-feature" "$LOGS/implement-feature" 2>/dev/null \
    || echo "(no .implement-feature/ yet)" > "$LOGS/implement-feature.missing"
  for f in settings.json plugins/installed_plugins.json plugins/known_marketplaces.json; do
    docker cp "$NAME:$HOME_IN/.claude/$f" "$LOGS/claude-$(basename "$f")" 2>/dev/null || true
  done
  inside '
    echo "## claude";            claude --version 2>&1
    echo; echo "## plugins";     claude plugin list 2>&1
    echo; echo "## plugin cache"; ls -d ~/.claude/plugins/cache/*/*/* 2>/dev/null || echo "(none)"
  ' > "$LOGS/versions.txt" 2>&1 || true
  # shellcheck disable=SC2016  # expands inside the container, on purpose
  inside '
    echo "## venvs under ~ (wherever the user made one)"
    for cfg in $(find ~ -maxdepth 4 -name pyvenv.cfg -not -path "*/.local/*" -not -path "*/.claude/*" 2>/dev/null); do
      v=$(dirname "$cfg"); echo; echo "### $v"; "$v/bin/python" -m pip list 2>&1
    done
    echo; echo "## system python (anything here beyond pip = installed outside a venv)"
    /usr/local/bin/python3 -m pip list 2>&1
    echo; echo "## user site (~/.local)"; /usr/local/bin/python3 -m pip list --user 2>&1
  ' > "$LOGS/python.txt" 2>&1 || true
  inside '
    echo "## branch";  git branch -a 2>&1
    echo; echo "## status"; git status --short --ignored 2>&1
    echo; echo "## log";    git log --oneline --decorate -n 20 2>&1
    echo; echo "## stray artifacts in the project (expect none)"
    find . -path ./.implement-feature -prune -o \( -name ".coverage*" -o -name mutants -o -name if-runlog.jsonl \) -print 2>&1
  ' > "$LOGS/git.txt" 2>&1 || true
  echo "✅ evidence copied to $LOGS/"
  ls -1 "$LOGS"
}

cmd_down() {
  exists && docker rm -f "$NAME" >/dev/null && echo "→ removed container '$NAME'"
  docker image inspect "$NAME" >/dev/null 2>&1 && docker rmi "$NAME" >/dev/null && echo "→ removed image '$NAME'"
  echo "✅ down. ($LOGS/ is kept; delete it when done.)"
}

command -v docker >/dev/null || die "docker not found."
docker info >/dev/null 2>&1 || die "Docker is not running. Start Docker Desktop."

case "${1:-}" in
  up) cmd_up ;;
  shell) cmd_shell ;;
  logs) cmd_logs ;;
  down) cmd_down ;;
  *) usage; exit 2 ;;
esac
