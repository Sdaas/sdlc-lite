#!/usr/bin/env bash
#
# post-start.sh — provision this repo's Claude Code UX into the container.
#
# Invoked by devcontainer.json's `postStartCommand`, so it runs on EVERY container
# start (create, restart, rebuild) with the workspace folder as the cwd. It must
# therefore be IDEMPOTENT — and it is, via three deliberate rules:
#
#   REFRESH  static scripts we own outright are overwritten every start, so an edit
#            in `.devcontainer/claude/` takes effect on the next start.
#   SEED     settings.json is installed ONLY IF ABSENT, so a fresh volume
#            self-heals but nothing you changed in-session is clobbered.
#   MERGE    the first-run keys are merged into ~/.claude.json every start; the
#            rest of that file (which Claude Code writes) is left alone.
#
# Two different stores are involved, and the split matters (issue #54):
#
#   ~/.claude/        mounted to the `sdlc-lite-claude` named volume — settings,
#                     plugins, session history, and the `/login` credential all
#                     PERSIST across container rebuilds.
#   ~/.claude.json    at the HOME ROOT, OUTSIDE that volume — so it is recreated
#                     on every rebuild and must be re-provisioned here.
#
# macOS-only alerting (the Mac's Stop / Notification osascript hooks) is
# intentionally NOT ported — it is meaningless in a headless container.
#
# See dev-docs/DEVCONTAINER.md for the user-facing version of all of this.

set -euo pipefail

TEMPLATES=".devcontainer/claude"
CLAUDE_DIR="$HOME/.claude"

mkdir -p "$CLAUDE_DIR"

# --- REFRESH: static scripts, safe to overwrite -------------------------------
# The status line (dir · branch · user@host · model · effort · context %) and the
# smart-rm hook (auto-allows /tmp + *.tmp deletions). We author both; Claude Code
# never writes to them, so the workspace copy is always the source of truth.
install -m 755 \
  "$TEMPLATES/statusline-command.sh" \
  "$TEMPLATES/smart_rm_hook.sh" \
  "$CLAUDE_DIR/"

# --- SEED: settings.json, only if absent --------------------------------------
# Ships permissive sandbox permissions (Bash(*), defaultMode: auto), the status
# line + smart-rm hook wiring, and the enabled plugins/marketplaces
# (sdlc-lite@sdlc-lite-dev — the live directory-source channel, see ADR-13).
# Guarded because in-session `/config` changes and plugin toggles live in this
# same file. To re-apply the template: rm ~/.claude/settings.json and restart.
if [[ ! -f "$CLAUDE_DIR/settings.json" ]]; then
  install -m 644 "$TEMPLATES/settings.json" "$CLAUDE_DIR/settings.json"
fi

# --- MERGE: first-run keys into ~/.claude.json (issues #54, #45) --------------
# Holds Claude Code's FIRST-RUN state: hasCompletedOnboarding, theme, and
# per-project trust. Because it lives outside the volume (see header), a bare
# interactive `claude` otherwise stops at the theme wizard and the folder-trust
# dialog on every rebuild. That looks like an auth prompt but is NOT: auth comes
# from .env's CLAUDE_CODE_OAUTH_TOKEN and works headlessly either way.
#
# MERGED, not seeded-if-absent (#45): the Dockerfile's `claude --version` already
# creates ~/.claude.json in the image, so an "only if absent" seed never applied.
# jq's deep merge (`*`) sets just the template's keys and keeps everything else
# Claude Code wrote. Mode 600 matches what Claude Code writes.
if [[ -f "$HOME/.claude.json" ]]; then
  merged="$(mktemp /tmp/claude-json.XXXXXX)"
  jq -s '.[0] * .[1]' "$HOME/.claude.json" "$TEMPLATES/claude.json" > "$merged"
  install -m 600 "$merged" "$HOME/.claude.json"
  rm -f "$merged"
else
  install -m 600 "$TEMPLATES/claude.json" "$HOME/.claude.json"
fi

echo "post-start: Claude Code UX provisioned into $CLAUDE_DIR and $HOME/.claude.json"
