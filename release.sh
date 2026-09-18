#!/usr/bin/env bash
#
# release.sh — cut a versioned release of the implement-feature plugin.
#
# Automates RELEASING.md §4 steps 2–4 and hands off to the verify gate (step 5).
# Background + rationale: docs/developer-guide.md → ADR-13 (two-channel distribution).
#
# Two channels live in one root catalog (.claude-plugin/marketplace.json):
#   • implement-feature      → github source, pinned to a tag   (CUSTOMERS)
#   • implement-feature-dev  → directory source, loaded in place (DEV CONTAINER)
# A release = bump plugin.json "version" + tag v<version> + repoint the customer
# entry's ref/sha to that tag. All three are required: /plugin update compares the
# plugin.json "version" and SKIPS if it is unchanged.
#
# Usage:
#   ./release.sh <version>            e.g. ./release.sh 1.0.0-beta.1
#   ./release.sh <version> --no-push  do everything locally; skip the push
#
# This script does NOT verify the release. Verification is a human-run gate in an
# ISOLATED clean-room environment (no dev marketplace) — see RELEASING.md §4 step 5.
#
set -euo pipefail

# ── config ───────────────────────────────────────────────────────────────────
DEFAULT_BRANCH="main"
PLUGIN_JSON="implement-feature-plugin/.claude-plugin/plugin.json"
MARKETPLACE_JSON=".claude-plugin/marketplace.json"
RELEASE_ENTRY="implement-feature"          # the customer-facing (github-pinned) entry
REPO_SLUG="Sdaas/sdlc-lite"

# ── args ─────────────────────────────────────────────────────────────────────
PUSH=1
VERSION=""
for arg in "$@"; do
  case "$arg" in
    --no-push) PUSH=0 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    -*)        echo "release.sh: unknown flag: $arg" >&2; exit 2 ;;
    *)         if [[ -z "$VERSION" ]]; then VERSION="$arg"; else
                 echo "release.sh: unexpected argument: $arg" >&2; exit 2; fi ;;
  esac
done

die() { echo "release.sh: $*" >&2; exit 1; }

[[ -n "$VERSION" ]] || die "usage: ./release.sh <version> [--no-push]"

# Semver with optional prerelease (e.g. 1.0.0, 1.0.0-beta.1, 1.0.0-rc.2).
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] \
  || die "version '$VERSION' is not semver (MAJOR.MINOR.PATCH[-prerelease])"

TAG="v$VERSION"

# Run from the repo root regardless of caller's cwd.
cd "$(git rev-parse --show-toplevel)"

# ── preflight ────────────────────────────────────────────────────────────────
command -v python3 >/dev/null || die "python3 is required (JSON surgery)"
[[ -f "$PLUGIN_JSON" ]]      || die "missing $PLUGIN_JSON"
[[ -f "$MARKETPLACE_JSON" ]] || die "missing $MARKETPLACE_JSON"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" == "$DEFAULT_BRANCH" ]] \
  || die "must cut releases from '$DEFAULT_BRANCH' (on '$BRANCH')"

git diff --quiet && git diff --cached --quiet \
  || die "working tree not clean — commit or stash first"

git rev-parse -q --verify "refs/tags/$TAG" >/dev/null \
  && die "tag $TAG already exists"

# ── step 2: bump plugin.json version ─────────────────────────────────────────
python3 - "$PLUGIN_JSON" "$VERSION" <<'PY'
import json, sys
path, version = sys.argv[1], sys.argv[2]
with open(path) as f: data = json.load(f)
data["version"] = version
with open(path, "w") as f:
    json.dump(data, f, indent=2); f.write("\n")
PY
echo "→ bumped $PLUGIN_JSON version → $VERSION"

# ── step 3: commit the bump, tag it ──────────────────────────────────────────
git add "$PLUGIN_JSON"
git commit -q -m "release: $TAG — bump plugin.json version"
git tag -a "$TAG" -m "implement-feature $TAG"
SHA="$(git rev-parse "$TAG^{commit}")"
echo "→ tagged $TAG @ $SHA"

# ── step 4: repoint the customer catalog entry (ref + sha) ───────────────────
python3 - "$MARKETPLACE_JSON" "$RELEASE_ENTRY" "$TAG" "$SHA" <<'PY'
import json, sys
path, name, ref, sha = sys.argv[1:5]
with open(path) as f: data = json.load(f)
for p in data.get("plugins", []):
    if p.get("name") == name:
        src = p.get("source")
        if not isinstance(src, dict) or src.get("source") != "github":
            sys.exit(f"entry '{name}' is not a github source; refusing to repoint")
        src["ref"], src["sha"] = ref, sha
        break
else:
    sys.exit(f"entry '{name}' not found in {path}")
with open(path, "w") as f:
    json.dump(data, f, indent=2); f.write("\n")
PY
git add "$MARKETPLACE_JSON"
git commit -q -m "release: $TAG — repoint $RELEASE_ENTRY to $TAG"
echo "→ repointed $RELEASE_ENTRY → ref=$TAG sha=$SHA"

# ── step 5: push (with confirmation) ─────────────────────────────────────────
if [[ "$PUSH" -eq 1 ]]; then
  read -r -p "Push branch $DEFAULT_BRANCH and tag $TAG to origin? [y/N] " ans
  if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
    git push origin "$DEFAULT_BRANCH"
    git push origin "$TAG"
    echo "→ pushed $DEFAULT_BRANCH and $TAG"
  else
    PUSH=0
    echo "→ push skipped; local commits + tag are ready"
  fi
fi

# ── verify handoff (THE GATE — RELEASING.md §4 step 5) ───────────────────────
cat <<EOF

────────────────────────────────────────────────────────────────────────────
$TAG is prepared${PUSH:+ and pushed}. It is NOT a real release until VERIFIED.

Clean-room verify (isolated env, NO dev marketplace — see ADR-13 / RELEASING.md §4):
  1. From a fresh Claude config (own CLAUDE_CONFIG_DIR/HOME, toolchain installed):
       claude plugin marketplace add $REPO_SLUG
       claude plugin install $RELEASE_ENTRY@sdaas-sdlc-lite
  2. Confirm the install log shows a genuine GitHub clone/checkout of $TAG
     (NOT a local directory source), and the cached version is $VERSION.
  3. Run /implement-feature end-to-end on test-fixtures/python-starter — it must pass.
  4. Only after that passes is $TAG a real release. If it fails: fix, delete the
     tag (git tag -d $TAG && git push origin :$TAG), and re-run release.sh.
────────────────────────────────────────────────────────────────────────────
EOF
