#!/usr/bin/env bash
#
# release-verify.sh — automated clean-room verification of the RELEASED sdlc-lite plugin.
#
# Verify-only companion to release.sh (which cuts). Runs everything about the customer
# path that CAN be automated, then hands the one irreducibly-human step (the full gated
# /implement-feature run) back to a person. Principle: automate whatever can be automated.
#
# It exercises the REAL release channel: a fresh, isolated Claude config (no dev
# marketplace) installs sdlc-lite from the umbrella marketplace on GitHub, then a headless
# two-call smoke proves Gate 0 (preflight) passes and Gate 1 (interview) is entered.
#
# WHAT IT AUTOMATES
#   1. Auth from .env (no interactive login) — CLAUDE_CODE_OAUTH_TOKEN (preferred) or
#      ANTHROPIC_API_KEY, sourced INSIDE the container from the bind-mounted .env.
#   2. Clean-room install: fresh config → marketplace add umbrella → install sdlc-lite@sdaas
#      → assert a genuine git-subdir GitHub install, cached version == plugin.json version,
#      commands + agents present.
#   3. Gate-0/Gate-1 smoke (headless, two `claude -p` calls) on a fresh fixture:
#        call 1: /implement-feature <request>  → assert "Preflight passed" + Gate 0 STOP
#        call 2: --continue "<approval>"        → assert the Gate 1 interview started
#   4. Prints the human handoff for the full gated run.
#
# WHAT IT DOES NOT DO (by design)
#   The full /implement-feature run is human-in-the-loop (approval gates; never commits
#   before a human approves). This script stops at "Gate 1 entered" and hands off.
#
# PREREQUISITES
#   • Docker + the dev container up (devcontainer up --workspace-folder .).
#   • A repo-root .env (gitignored) with CLAUDE_CODE_OAUTH_TOKEN=... (from `claude
#     setup-token`) or ANTHROPIC_API_KEY=...
#   • The release already cut & pushed (release.sh) so the tag/umbrella pin exist.
#
# Usage:
#   ./release-verify.sh                 # verify the current umbrella pin end-to-end
#   ./release-verify.sh --keep          # don't tear down the verify config/fixture at the end
#   ./release-verify.sh --no-smoke      # install-verify only; skip the Gate 0/1 model calls
#
set -euo pipefail

# ── config ───────────────────────────────────────────────────────────────────
UMBRELLA_SLUG="Sdaas/claude-plugins"
MARKETPLACE="sdaas"
PLUGIN="sdlc-lite"
FIXTURE_SLUG="roman-numeral"
FEATURE_REQUEST="add a to_roman(n) function that converts an integer 1..3999 to a Roman numeral string"
# Dedicated, disposable config + fixture — kept separate from the human .claude-cleanroom
# so an automated run never collides with an interactive session's run lock.
VERIFY_CFG="/home/vscode/.claude-verify"
VERIFY_RUN="/workspaces/${FIXTURE_SLUG}-verify-run"
ENV_IN_CONTAINER="/workspaces/sdlc-lite/.env"

# ── args ─────────────────────────────────────────────────────────────────────
KEEP=0
SMOKE=1
for arg in "$@"; do
  case "$arg" in
    --keep)     KEEP=1 ;;
    --no-smoke) SMOKE=0 ;;
    -h|--help)  sed -n '2,40p' "$0"; exit 0 ;;
    *)          echo "release-verify.sh: unknown arg: $arg" >&2; exit 2 ;;
  esac
done

die()  { echo "release-verify.sh: $*" >&2; exit 1; }
pass=0; fail=0
ok()   { echo "  ✅ $1"; pass=$((pass+1)); }
no()   { echo "  ❌ $1"; fail=$((fail+1)); }
step() { echo; echo "── $1 ─────────────────────────────────────────────"; }

cd "$(git rev-parse --show-toplevel)"

# ── preflight ────────────────────────────────────────────────────────────────
command -v devcontainer >/dev/null || die "devcontainer CLI not found"
[[ -f .env ]] || die "no .env at repo root (need CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY)"
# Confirm .env carries a usable auth var — WITHOUT printing its value.
if ! grep -qE '^(CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY)=.' .env; then
  die ".env has neither CLAUDE_CODE_OAUTH_TOKEN=... nor ANTHROPIC_API_KEY=..."
fi
devcontainer exec --workspace-folder . true 2>/dev/null || die "dev container not running (devcontainer up --workspace-folder .)"

# Run a claude CLI invocation in the container, authed from .env, against the verify config.
# Auth is sourced INSIDE the container so the token never appears in host process args.
cc() {
  devcontainer exec --workspace-folder . bash -c '
    set -a; source "'"$ENV_IN_CONTAINER"'" 2>/dev/null; set +a
    export CLAUDE_CONFIG_DIR="'"$VERIFY_CFG"'"
    exec "$@"' _ "$@"
}
# A plain container bash command (no auth needed) — for fs inspection/setup.
dx() { devcontainer exec --workspace-folder . bash -c "$1"; }

# ── 0. fresh, isolated verify config (no dev marketplace) ────────────────────
step "0. fresh isolated config ($VERIFY_CFG)"
dx "rm -rf '$VERIFY_CFG' && mkdir -p '$VERIFY_CFG'"
ok "wiped + recreated verify config (no dev marketplace, no cached plugins)"

# ── 1. clean-room install from the umbrella (GitHub) ─────────────────────────
step "1. clean-room install from $UMBRELLA_SLUG"
cc claude plugin marketplace add "$UMBRELLA_SLUG" >/dev/null 2>&1 \
  && ok "marketplace add $UMBRELLA_SLUG" || no "marketplace add failed"
if cc claude plugin install "$PLUGIN@$MARKETPLACE" 2>&1 | tee /tmp/rv-install.tmp | grep -q "Successfully installed"; then
  ok "install $PLUGIN@$MARKETPLACE"
else
  no "install failed"; sed -n '1,20p' /tmp/rv-install.tmp
fi

# ── 2. assert it is a real git-subdir GitHub install, correct version ────────
step "2. assert install shape"
EXPECT_VER="$(python3 -c "import json;print(json.load(open('sdlc-lite-plugin/.claude-plugin/plugin.json'))['version'])")"
CACHE_BASE="$VERIFY_CFG/plugins/cache/$MARKETPLACE/$PLUGIN"
# The version-keyed dir (git-subdir resolves plugin.json version, not a bare sha).
VER_DIR="$(dx "ls '$CACHE_BASE' 2>/dev/null | head -1" | tr -d '\r')"
[[ "$VER_DIR" == "$EXPECT_VER" ]] \
  && ok "cached under version dir '$VER_DIR' == plugin.json $EXPECT_VER" \
  || no "cache dir '$VER_DIR' != expected version '$EXPECT_VER'"
# git-subdir puts the PLUGIN ROOT (subdir contents) at the cache root — plugin.json + commands.
dx "test -f '$CACHE_BASE/$VER_DIR/.claude-plugin/plugin.json'" \
  && ok "plugin.json at cache root (subdir resolved)" || no "no plugin.json at cache root"
for f in commands/implement-feature.md commands/analyze-run.md agents/test-writer.md hooks/hooks.json; do
  dx "test -f '$CACHE_BASE/$VER_DIR/$f'" && ok "present: $f" || no "missing: $f"
done

# ── 3. Gate 0 / Gate 1 smoke on a fresh fixture ──────────────────────────────
if [[ "$SMOKE" -eq 1 ]]; then
  step "3. fresh fixture ($VERIFY_RUN)"
  dx "
    set -e
    rm -rf '$VERIFY_RUN'
    cp -r '/workspaces/sdlc-lite/test-fixtures/python-starter/$FIXTURE_SLUG' '$VERIFY_RUN'
    cd '$VERIFY_RUN'
    git init -q -b main
    git config user.name 'SDLC Verify'; git config user.email 'verify@sdlc-lite.local'
    git config commit.gpgsign false
    git add -A && git commit -q -m 'verify fixture baseline'
    pip install -e . --quiet
  " && ok "fixture provisioned + package installed editable" || no "fixture setup failed"

  step "3a. call 1 — /implement-feature → Gate 0 preflight + STOP"
  # acceptEdits + Bash so Gate 0's preflight/version/git commands run without a human;
  # the conductor STOPs at the Gate 0 confirmation, ending the -p turn.
  dx '
    set -a; source "'"$ENV_IN_CONTAINER"'" 2>/dev/null; set +a
    export CLAUDE_CONFIG_DIR="'"$VERIFY_CFG"'"
    cd "'"$VERIFY_RUN"'"
    claude -p "/implement-feature '"$FEATURE_REQUEST"'" \
      --permission-mode acceptEdits --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
      2>&1' | tee /tmp/rv-gate0.tmp >/dev/null || true
  grep -q "Preflight passed" /tmp/rv-gate0.tmp && ok "Gate 0: 'Preflight passed'" || no "Gate 0: no 'Preflight passed' (see /tmp/rv-gate0.tmp)"
  grep -qiE "Preflight failed" /tmp/rv-gate0.tmp && no "Gate 0 HARD-FAILED (fixture not importable?)" || ok "Gate 0: no hard-fail"
  grep -qE "STOP.*(layout|model plan|branch)" /tmp/rv-gate0.tmp && ok "Gate 0: reached the confirm-STOP" || no "Gate 0: no confirm-STOP marker"
  dx "test -f '$VERIFY_RUN/.implement-feature/.active-run'" && ok "Gate 0: .active-run written" || no "Gate 0: no .active-run"

  step "3b. call 2 — approve → Gate 1 interview begins"
  dx '
    set -a; source "'"$ENV_IN_CONTAINER"'" 2>/dev/null; set +a
    export CLAUDE_CONFIG_DIR="'"$VERIFY_CFG"'"
    cd "'"$VERIFY_RUN"'"
    claude --continue -p "APPROVED — proceed with the detected layout, model plan, and branch." \
      --permission-mode acceptEdits --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
      2>&1' | tee /tmp/rv-gate1.tmp >/dev/null || true
  if grep -qE "❓|➡️|scope boundary|out-of-scope|minimal version|INTERVIEW" /tmp/rv-gate1.tmp; then
    ok "Gate 1: interview / scope-anchor started"
  else
    no "Gate 1: no interview marker (see /tmp/rv-gate1.tmp)"
  fi
else
  step "3. smoke skipped (--no-smoke)"
fi

# ── teardown ─────────────────────────────────────────────────────────────────
if [[ "$KEEP" -eq 0 ]]; then
  dx "rm -rf '$VERIFY_CFG' '$VERIFY_RUN'" && echo && echo "→ cleaned up verify config + fixture (--keep to retain)"
fi

# ── result + human handoff ───────────────────────────────────────────────────
echo
echo "════════════════════════════════════════════════════════════════════════════"
echo "release-verify: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  cat <<EOF

✅ AUTOMATED clean-room verification PASSED: the released $PLUGIN@$MARKETPLACE installs from
   GitHub (git-subdir), loads its commands, and reaches Gate 0 preflight-pass + Gate 1.

The remaining step is HUMAN (approval-gated, by design). To drive the full run:
   devcontainer exec --workspace-folder . bash -c \\
     "cd $VERIFY_RUN && CLAUDE_CONFIG_DIR=$VERIFY_CFG claude"
   then run: /implement-feature <your feature>   (re-run this script with --keep first)
EOF
fi
[[ "$fail" -eq 0 ]]
