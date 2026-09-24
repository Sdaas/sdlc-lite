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
#   4. /plugin update proof (git/fs only, no model calls): install the PREVIOUS release
#      from an old-pinned catalog, advance the catalog to the current pin, then
#      `marketplace update` + `plugin update` → assert the installed version moved.
#      Skipped automatically on the very first release (no previous tag).
#   5. Prints the human handoff for the full gated run.
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
#   ./release-verify.sh --links-only    # just the relative-link check; no Docker/container needed
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
LINKS_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --keep)       KEEP=1 ;;
    --no-smoke)   SMOKE=0 ;;
    --links-only) LINKS_ONLY=1 ;;
    -h|--help)    sed -n '2,41p' "$0"; exit 0 ;;
    *)            echo "release-verify.sh: unknown arg: $arg" >&2; exit 2 ;;
  esac
done

die()  { echo "release-verify.sh: $*" >&2; exit 1; }
pass=0; fail=0
ok()   { echo "  ✅ $1"; pass=$((pass+1)); }
no()   { echo "  ❌ $1"; fail=$((fail+1)); }
step() { echo; echo "── $1 ─────────────────────────────────────────────"; }

cd "$(git rev-parse --show-toplevel)"

# ── L. relative-link check (host-only, no Docker) ─────────────────────────────
# Scans every *.md file for markdown links whose target is a relative filesystem
# path, and fails on any that doesn't resolve on disk. Skips http(s)/mailto
# links, pure in-page anchors, and GitHub issue/PR links (../../issues/NN,
# ../../pull/NN — relative on github.com, not on disk). A '#anchor' suffix on a
# file link is stripped before the existence check (headings aren't validated).
step "L. relative-link check"
link_fail=0
while IFS= read -r -d '' md; do
  dir="$(dirname "$md")"
  while IFS= read -r target; do
    [[ -z "$target" ]] && continue
    case "$target" in
      http://*|https://*|mailto:*|\#*|*/issues/[0-9]*|*/pull/[0-9]*) continue ;;
    esac
    target="${target%%#*}"
    [[ -z "$target" ]] && continue
    if [[ ! -e "$dir/$target" ]]; then
      echo "  ❌ $md → $target (missing: $dir/$target)"
      link_fail=$((link_fail+1))
    fi
  done < <(grep -oE '\]\([^)]+\)' "$md" | sed -E 's/^\]\(//; s/\)$//')
done < <(find . -name '*.md' -not -path './.git/*' -print0)

if [[ "$link_fail" -eq 0 ]]; then
  ok "all relative links in *.md files resolve"
else
  no "$link_fail broken relative link(s) — see above"
fi

if [[ "$LINKS_ONLY" -eq 1 ]]; then
  echo
  [[ "$fail" -eq 0 ]] && { echo "✅ link check passed"; exit 0; }
  echo "❌ link check failed ($fail issue(s))"; exit 1
fi

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
# NOTE (#55): there is deliberately NO commands/implement-feature.md — a same-named command
# shadows the skill. `/implement-feature` is registered by skills/implement-feature/SKILL.md.
for f in skills/implement-feature/SKILL.md commands/analyze-run.md agents/test-writer.md hooks/hooks.json; do
  dx "test -f '$CACHE_BASE/$VER_DIR/$f'" && ok "present: $f" || no "missing: $f"
done
dx "test -f '$CACHE_BASE/$VER_DIR/commands/implement-feature.md'" \
  && no "shipped a command that shadows the implement-feature skill (#55)" \
  || ok "absent (correctly): commands/implement-feature.md"

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
  # BODY CANARY (#55). The gate markers above are NOT evidence the score loaded: with a
  # same-named command shadowing the skill, the conductor reaches them anyway — it hunts
  # SKILL.md down on disk and Reads it. So a plain grep for SKILL.md text false-passes;
  # assert instead that the body arrived THROUGH THE ENTRY POINT, by its two signatures:
  #   "Base directory for this skill:"  — the slash expansion injected the skill (healthy)
  #   "already loaded above; ..."       — a command shadowed it and the load was a no-op (bug)
  # Read the session TRANSCRIPT: -p's stdout carries only the final text, and
  # --output-format stream-json omits the expanded command and the injected body entirely.
  RV_TX=$(dx "ls -t '$VERIFY_CFG'/projects/*$(basename "$VERIFY_RUN")*/*.jsonl 2>/dev/null | head -1" | tr -d '\r')
  if [[ -z "$RV_TX" ]]; then
    no "Gate 0: no session transcript found — cannot verify the skill body loaded"
  elif dx "grep -q 'already loaded above; instructions unchanged' '$RV_TX'"; then
    no "Gate 0: SKILL.md SHADOWED — a same-named command suppressed the skill body (#55)"
  elif dx "grep -q 'Base directory for this skill' '$RV_TX'"; then
    ok "Gate 0: the skill body loaded through /implement-feature (entry point intact)"
  else
    no "Gate 0: the skill body never reached the conductor via the entry point (#55)"
  fi
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

# ── 4. /plugin update proof (previous release → current pin) ──────────────────
# Pure git/fs (no model calls). Simulates the umbrella BEFORE this cut by rewriting a
# clone's catalog to the previous tag, installing that, then advancing the catalog to
# the current pin and running marketplace-update + plugin-update — asserting the move.
step "4. /plugin update proof"
PREV_TAG="$(git tag -l 'v*' --sort=-version:refname | sed -n '2p')"
if [[ -z "$PREV_TAG" ]]; then
  ok "first release (no previous tag) — /plugin update check skipped"
else
  PREV_VER="${PREV_TAG#v}"
  # Resolve the previous tag's commit in THIS (product) repo — the umbrella clone has no product tags.
  PREV_SHA="$(git rev-list -n1 "$PREV_TAG")"
  UPD_CFG="/home/vscode/.claude-verify-upd"
  UMB_CLONE="/tmp/rv-umbrella"
  CACHE_UPD="$UPD_CFG/plugins/cache/$MARKETPLACE/$PLUGIN"
  UPD_OUT="$(dx '
    set -e
    rm -rf "'"$UPD_CFG"'" "'"$UMB_CLONE"'"; mkdir -p "'"$UPD_CFG"'"
    export CLAUDE_CONFIG_DIR="'"$UPD_CFG"'"
    git clone -q https://github.com/'"$UMBRELLA_SLUG"' "'"$UMB_CLONE"'"
    CAT="'"$UMB_CLONE"'/.claude-plugin/marketplace.json"
    cp "$CAT" /tmp/rv-cat-current.json
    python3 - "$CAT" "'"$PLUGIN"'" "'"$PREV_TAG"'" "'"$PREV_SHA"'" <<'"'"'PY'"'"'
import json, sys
p, name, ref, sha = sys.argv[1:5]
d = json.load(open(p))
for e in d["plugins"]:
    if e.get("name") == name:
        e["source"]["ref"] = ref; e["source"]["sha"] = sha
json.dump(d, open(p, "w"), indent=2)
PY
    claude plugin marketplace add "'"$UMB_CLONE"'" >/dev/null 2>&1
    claude plugin install "'"$PLUGIN@$MARKETPLACE"'" -y >/dev/null 2>&1
    echo "INSTALLED=$(ls "'"$CACHE_UPD"'" 2>/dev/null | head -1 | tr -d "\r")"
    cp /tmp/rv-cat-current.json "$CAT"
    claude plugin marketplace update "'"$MARKETPLACE"'" >/dev/null 2>&1
    claude plugin update "'"$PLUGIN"'" -y >/dev/null 2>&1
    echo "UPDATED=$(claude plugin list 2>/dev/null | grep -A2 "'"$PLUGIN"'" | grep -oE "Version: .*" | head -1 | tr -d "\r")"
    rm -rf "'"$UPD_CFG"'" "'"$UMB_CLONE"'"
  ')"
  echo "$UPD_OUT" | grep -E '^(INSTALLED|UPDATED)=' | sed 's/^/    /'
  echo "$UPD_OUT" | grep -qx "INSTALLED=$PREV_VER" \
    && ok "installed previous release $PREV_VER" || no "did not install previous $PREV_VER"
  echo "$UPD_OUT" | grep -qx "UPDATED=Version: $EXPECT_VER" \
    && ok "plugin update $PREV_VER → $EXPECT_VER" || no "plugin update did not reach $EXPECT_VER"
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
   GitHub (git-subdir), loads its commands, reaches Gate 0 preflight-pass + Gate 1, and
   \`/plugin update\` advances a prior release to this one.

The remaining step is HUMAN (approval-gated, by design). To drive the full run:
   devcontainer exec --workspace-folder . bash -c \\
     "cd $VERIFY_RUN && CLAUDE_CONFIG_DIR=$VERIFY_CFG claude"
   then run: /implement-feature <your feature>   (re-run this script with --keep first)
EOF
fi
[[ "$fail" -eq 0 ]]
