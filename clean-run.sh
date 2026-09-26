#!/usr/bin/env bash
#
# clean-run.sh — take the Mac + dev container to a known-good dry-run state (#21).
#
# Every step of setting up an /implement-feature dry run is deterministic, so this script
# runs them all and ends in a status table. No AI is involved; diagnosing an UNEXPECTED
# state stays a human task — the script only says which row is red and how to fix it.
#
# WHAT IT DOES
#   1. Preflight on the Mac: Docker running, devcontainer CLI present, .env carries auth.
#   2. Reset: `docker rm -f sdlc-lite-test`. The container's own filesystem goes with it —
#      every /workspaces/<slug>-run fixture and ~/.claude.json. The image is kept (so the
#      next `up` is fast) unless --rebuild, which removes it and builds a new one with
#      --build-no-cache. The `sdlc-lite-claude` volume is NEVER touched,
#      so the Claude login survives.
#   3. Up: `devcontainer up`. A new container re-runs postCreate (pinned toolchain) and
#      post-start (status line, hooks, ~/.claude.json first-run keys).
#   4. Settings: deletes ~/.claude/settings.json and re-runs post-start.sh, which seeds it
#      fresh from .devcontainer/claude/settings.json. The volume otherwise carries
#      in-session /config and plugin toggles into every run.
#   5. Fixtures: test-fixtures/setup-fixture.sh <slug> for each slug.
#   6. Status table: Docker / volume / container / settings / plugin / toolchain / fixtures.
#      Exits non-zero if any row is red.
#
# WHY RESET, NOT REBUILD, BY DEFAULT
#   The plugin loads live from the workspace (#45), so a stale container cannot carry stale
#   plugin code, and removing the container already clears every fixture and first-run
#   file. Rebuilding the image only matters after a Dockerfile change or a suspect cache —
#   that is --rebuild.
#
# Idempotent: every run removes the container and rebuilds the same state, so two runs in
# a row end in the same table.
#
# Usage (on the Mac, from anywhere in the repo; Docker Desktop must be running):
#   ./clean-run.sh                      # reset + every fixture in test-fixtures/python-starter/
#   ./clean-run.sh roman-numeral        # reset + only the named fixture(s)
#   ./clean-run.sh --rebuild            # also remove the image, rebuild with no cache (slow)
#   make clean-run ARGS="--rebuild roman-numeral"
#
set -euo pipefail

# ── config ───────────────────────────────────────────────────────────────────
CONTAINER="sdlc-lite-test"          # runArgs --name in devcontainer.json
VOLUME="sdlc-lite-claude"           # the ~/.claude mount in devcontainer.json
IMAGE_PREFIX="vsc-sdlc-lite-"       # the devcontainer CLI's image name for this repo
WS="/workspaces/sdlc-lite"
FIXTURES="test-fixtures/python-starter"
PLUGIN_PATH="$WS/sdlc-lite-plugin"
PLUGIN_COMMAND="sdlc-lite:implement-feature"

# ── args ─────────────────────────────────────────────────────────────────────
REBUILD=0
SLUGS=()
for arg in "$@"; do
  case "$arg" in
    --rebuild) REBUILD=1 ;;
    -h|--help) sed -n '2,/^set -euo/{/^#/p;}' "$0"; exit 0 ;;
    -*)        echo "clean-run.sh: unknown flag: $arg" >&2; exit 2 ;;
    *)         SLUGS+=("$arg") ;;
  esac
done

die()  { echo "clean-run.sh: $*" >&2; exit 1; }
step() { echo; echo "── $1 ─────────────────────────────────────────────"; }
# Run a command inside the container, from the workspace root.
cexec() { devcontainer exec --workspace-folder . bash -c "cd $WS && $1"; }

cd "$(git rev-parse --show-toplevel)"

# ── 1. preflight (Mac) ───────────────────────────────────────────────────────
step "1. preflight"
docker info >/dev/null 2>&1 || die "Docker is not running — start Docker Desktop and wait for the whale icon."
command -v devcontainer >/dev/null || die "devcontainer CLI not found — npm i -g @devcontainers/cli"
[[ -f .env ]] || die "no .env at repo root — cp .env.example .env and add CLAUDE_CODE_OAUTH_TOKEN (see dev-docs/DEVCONTAINER.md → Authentication)."
# Confirm .env carries a usable auth var — WITHOUT printing its value.
grep -qE '^(CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY)=.' .env \
  || die ".env has neither CLAUDE_CODE_OAUTH_TOKEN=... nor ANTHROPIC_API_KEY=..."
if [[ ${#SLUGS[@]} -eq 0 ]]; then
  for d in "$FIXTURES"/*/; do SLUGS+=("$(basename "$d")"); done
fi
for slug in "${SLUGS[@]}"; do
  [[ -d "$FIXTURES/$slug" ]] || die "no such fixture: $FIXTURES/$slug"
done
echo "  fixtures: ${SLUGS[*]}"

# ── 2. reset ─────────────────────────────────────────────────────────────────
step "2. reset (volume $VOLUME kept)"
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  docker rm -f "$CONTAINER" >/dev/null
  echo "  removed container $CONTAINER"
else
  echo "  no container $CONTAINER to remove"
fi
if [[ "$REBUILD" -eq 1 ]]; then
  images="$(docker images -q --filter "reference=${IMAGE_PREFIX}*" | sort -u)"
  if [[ -n "$images" ]]; then
    # shellcheck disable=SC2086  # one id per word, on purpose
    docker rmi -f $images >/dev/null
    echo "  removed image(s) ${IMAGE_PREFIX}*"
  else
    echo "  no ${IMAGE_PREFIX}* image to remove"
  fi
fi

# ── 3. up ────────────────────────────────────────────────────────────────────
step "3. devcontainer up"
up_log="$(mktemp /tmp/clean-run-up.XXXXXX)"
echo "  building/starting (log: $up_log) …"
# --rebuild needs --build-no-cache too: with only the image removed, BuildKit re-serves
# every layer from its cache and "rebuilds" the same old image in seconds.
up_flags=()
[[ "$REBUILD" -eq 1 ]] && up_flags+=(--build-no-cache)
if ! devcontainer up --workspace-folder . "${up_flags[@]}" >"$up_log" 2>&1; then
  tail -20 "$up_log" >&2
  die "devcontainer up failed — full log kept at $up_log. A postCreate failure means the pinned toolchain did not install."
fi
rm -f "$up_log"
echo "  container up"

# ── 4. settings ──────────────────────────────────────────────────────────────
step "4. restore settings.json from the template"
cexec 'rm -f ~/.claude/settings.json && bash .devcontainer/post-start.sh' >/dev/null
echo "  ~/.claude/settings.json re-seeded"

# ── 5. fixtures ──────────────────────────────────────────────────────────────
step "5. fixtures"
for slug in "${SLUGS[@]}"; do
  test-fixtures/setup-fixture.sh "$slug" || die "setup-fixture.sh $slug failed — see its message above."
done

# ── 6. status table ──────────────────────────────────────────────────────────
step "6. status"
ROWS=()
red=0
row() {  # row <name> <ok:0|1> <detail>
  local mark="✅"
  if [[ "$2" -ne 0 ]]; then mark="❌"; red=$((red+1)); fi
  ROWS+=("$(printf '  %s %-22s %s' "$mark" "$1" "$3")")
}

if v="$(docker info --format '{{.ServerVersion}}' 2>/dev/null)"; then
  row "Docker" 0 "server $v"
else
  row "Docker" 1 "not reachable — start Docker Desktop"
fi

if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  row "Volume" 0 "$VOLUME present (login kept)"
else
  row "Volume" 1 "$VOLUME missing — log in again (dev-docs/DEVCONTAINER.md → Authentication)"
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" == "true" ]]; then
  row "Container" 0 "$CONTAINER running"
else
  row "Container" 1 "$CONTAINER not running — docker logs $CONTAINER"
fi

if cexec 'cmp -s ~/.claude/settings.json .devcontainer/claude/settings.json' >/dev/null 2>&1; then
  row "Settings" 0 "settings.json == template"
else
  row "Settings" 1 "settings.json differs from .devcontainer/claude/settings.json"
fi

# One headless one-turn session: its init event shows what the plugin loaded from, and a
# non-error result proves .env auth works. Plain `jq` checks — no model judgment.
# shellcheck disable=SC2016  # single-quoted on purpose: it expands inside the container
plugin_check="P='$PLUGIN_PATH'; C='$PLUGIN_COMMAND'"'
set -a; source .env; set +a
out="$(claude -p --output-format stream-json --verbose --max-turns 1 "reply ok" 2>/dev/null || true)"
init="$(jq -c "select(.type==\"system\" and .subtype==\"init\")" <<<"$out" | head -1)"
result="$(jq -c "select(.type==\"result\")" <<<"$out" | tail -1)"
if [[ -z "$result" || "$(jq -r .is_error <<<"$result")" != "false" ]]; then
  echo "no successful reply — check the .env token"; exit 1
fi
jq -e --arg p "$P" ".plugins[] | select(.name==\"sdlc-lite\" and .path==\$p)" <<<"$init" >/dev/null \
  || { echo "sdlc-lite not loaded from $P"; exit 1; }
jq -e --arg c "$C" ".slash_commands | index(\$c)" <<<"$init" >/dev/null \
  || { echo "$C not registered"; exit 1; }
echo "live from $P, $C registered, auth ok"'
if msg="$(cexec "$plugin_check" 2>&1)"; then
  row "Plugin" 0 "$msg"
else
  row "Plugin" 1 "$(tail -1 <<<"$msg")"
fi

# Same tools postCreate installs and checks; mutmut via metadata (it fails outside a project).
# shellcheck disable=SC2016  # expands inside the container
tool_check='printf "%s | %s | %s | mutmut %s | claude %s" \
  "$(ruff --version)" "$(mypy --version | cut -d" " -f1-2)" "$(pytest --version 2>&1)" \
  "$(python -c "import importlib.metadata as m; print(m.version(\"mutmut\"))")" \
  "$(claude --version | cut -d" " -f1)"'
if msg="$(cexec "$tool_check" 2>&1)"; then
  row "Toolchain" 0 "$msg"
else
  row "Toolchain" 1 "a pinned tool is missing — rerun with --rebuild; requirements: sdlc-lite-plugin/toolchain/requirements-dev.txt"
fi

for slug in "${SLUGS[@]}"; do
  run="/workspaces/${slug}-run"
  fixture_check="set -e
cd '$run'
[[ \"\$(git branch --show-current)\" == main ]] || { echo 'not on main'; exit 1; }
# Tracked files only: setup-fixture's 'pip install -e .' leaves an untracked *.egg-info.
[[ -z \"\$(git status --porcelain --untracked-files=no)\" ]] || { echo 'baseline modified'; exit 1; }
for pkg in src/*/; do
  name=\"\$(basename \"\$pkg\")\"; [[ \"\$name\" == *.egg-info ]] && continue
  (cd /tmp && python -c \"import \$name\") || { echo \"import \$name failed\"; exit 1; }
done
echo '$run on main, baseline intact, importable'"
  if msg="$(cexec "$fixture_check" 2>&1)"; then
    row "Fixture $slug" 0 "$msg"
  else
    row "Fixture $slug" 1 "$(tail -1 <<<"$msg") — see test-fixtures/README.md"
  fi
done

echo
printf '%s\n' "${ROWS[@]}"
echo
if [[ "$red" -eq 0 ]]; then
  echo "✅ clean-run: known-good dry-run state"
  exit 0
fi
echo "❌ clean-run: $red red row(s) — fix per the row, then rerun"
exit 1
