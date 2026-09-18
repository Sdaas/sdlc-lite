#!/usr/bin/env bash
#
# release.sh — cut a versioned release of the sdlc-lite plugin (cross-repo).
#
# Automates RELEASING.md §4 steps 2–4 and hands off to the verify gate (step 5).
# Background + rationale: docs/developer-guide.md → ADR-13 (two-channel distribution).
#
# Two channels live in TWO repos (ADR-13):
#   • dev      → this repo's root catalog (name: sdlc-lite-dev), directory source, live.
#                release.sh NEVER touches it.
#   • release  → the umbrella repo Sdaas/claude-plugins (catalog name: sdaas), where the
#                sdlc-lite entry is a github source pinned to a tag. CUSTOMERS install from
#                here: `marketplace add Sdaas/claude-plugins` → `install sdlc-lite@sdaas`.
#
# A release = bump plugin.json "version" + tag v<version> in THIS repo, then repoint the
# umbrella entry's ref/sha to that tag. All are required: /plugin update compares the
# plugin.json "version" and SKIPS if it is unchanged.
#
# Usage:
#   ./release.sh <version> --umbrella <path-to-local-clone-of-Sdaas/claude-plugins>
#   ./release.sh <version>                # no --umbrella: prints the manual umbrella edit
#   ./release.sh <version> ... --no-push  # do everything locally; skip both pushes
#
#   --umbrella <dir> may also be supplied via the UMBRELLA_DIR environment variable.
#
# This script does NOT verify the release. Verification is a human-run gate in an
# ISOLATED clean-room environment (no dev marketplace) — see RELEASING.md §4 step 5.
#
set -euo pipefail

# ── config ───────────────────────────────────────────────────────────────────
DEFAULT_BRANCH="main"
PLUGIN_JSON="sdlc-lite-plugin/.claude-plugin/plugin.json"
REPO_SLUG="Sdaas/sdlc-lite"                 # this repo (the product)
UMBRELLA_SLUG="Sdaas/claude-plugins"        # the release-channel umbrella repo
UMBRELLA_MARKETPLACE="sdaas"                # catalog name inside the umbrella
UMBRELLA_ENTRY="sdlc-lite"                  # the plugin entry to repoint
UMBRELLA_CATALOG_REL=".claude-plugin/marketplace.json"

# ── args ─────────────────────────────────────────────────────────────────────
PUSH=1
VERSION=""
UMBRELLA_DIR="${UMBRELLA_DIR:-}"            # env default; --umbrella overrides
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-push)      PUSH=0 ;;
    --umbrella)     shift; [[ $# -gt 0 ]] || { echo "release.sh: --umbrella needs a path" >&2; exit 2; }; UMBRELLA_DIR="$1" ;;
    --umbrella=*)   UMBRELLA_DIR="${1#*=}" ;;
    -h|--help)      sed -n '2,33p' "$0"; exit 0 ;;
    -*)             echo "release.sh: unknown flag: $1" >&2; exit 2 ;;
    *)              if [[ -z "$VERSION" ]]; then VERSION="$1"; else
                      echo "release.sh: unexpected argument: $1" >&2; exit 2; fi ;;
  esac
  shift
done

die() { echo "release.sh: $*" >&2; exit 1; }

[[ -n "$VERSION" ]] || die "usage: ./release.sh <version> [--umbrella <dir>] [--no-push]"

# Semver with optional prerelease (e.g. 1.0.0, 1.0.0-beta.1, 1.0.0-rc.2).
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] \
  || die "version '$VERSION' is not semver (MAJOR.MINOR.PATCH[-prerelease])"

TAG="v$VERSION"

# Run from the repo root regardless of caller's cwd.
cd "$(git rev-parse --show-toplevel)"

# ── preflight (this repo) ────────────────────────────────────────────────────
command -v python3 >/dev/null || die "python3 is required (JSON surgery)"
[[ -f "$PLUGIN_JSON" ]] || die "missing $PLUGIN_JSON"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "$BRANCH" == "$DEFAULT_BRANCH" ]] \
  || die "must cut releases from '$DEFAULT_BRANCH' (on '$BRANCH')"

git diff --quiet && git diff --cached --quiet \
  || die "working tree not clean — commit or stash first"

git rev-parse -q --verify "refs/tags/$TAG" >/dev/null \
  && die "tag $TAG already exists"

# ── preflight (umbrella clone, if given) ─────────────────────────────────────
# Validate BEFORE we mutate this repo, so a bad umbrella path fails fast (no half-cut).
UMBRELLA_CATALOG=""
if [[ -n "$UMBRELLA_DIR" ]]; then
  [[ -d "$UMBRELLA_DIR" ]] || die "--umbrella: '$UMBRELLA_DIR' is not a directory"
  UMBRELLA_CATALOG="$UMBRELLA_DIR/$UMBRELLA_CATALOG_REL"
  [[ -f "$UMBRELLA_CATALOG" ]] || die "--umbrella: no $UMBRELLA_CATALOG_REL under '$UMBRELLA_DIR'"
  git -C "$UMBRELLA_DIR" rev-parse --git-dir >/dev/null 2>&1 \
    || die "--umbrella: '$UMBRELLA_DIR' is not a git repo"
  # Confirm it's really the umbrella (remote slug match) — warn, don't hard-fail on naming.
  u_remote="$(git -C "$UMBRELLA_DIR" remote get-url origin 2>/dev/null || true)"
  [[ "$u_remote" == *"$UMBRELLA_SLUG"* ]] \
    || echo "release.sh: warning: umbrella origin '$u_remote' does not look like $UMBRELLA_SLUG" >&2
  u_branch="$(git -C "$UMBRELLA_DIR" rev-parse --abbrev-ref HEAD)"
  [[ "$u_branch" == "$DEFAULT_BRANCH" ]] \
    || die "--umbrella: clone must be on '$DEFAULT_BRANCH' (on '$u_branch')"
  git -C "$UMBRELLA_DIR" diff --quiet && git -C "$UMBRELLA_DIR" diff --cached --quiet \
    || die "--umbrella: clone working tree not clean — commit or stash first"
  # Confirm the entry exists and is a github source (fail now, not after tagging).
  python3 - "$UMBRELLA_CATALOG" "$UMBRELLA_ENTRY" <<'PY' || die "umbrella entry check failed"
import json, sys
path, name = sys.argv[1], sys.argv[2]
with open(path) as f: data = json.load(f)
for p in data.get("plugins", []):
    if p.get("name") == name:
        src = p.get("source")
        if not isinstance(src, dict) or src.get("source") != "github":
            sys.exit(f"umbrella entry '{name}' is not a github source")
        sys.exit(0)
sys.exit(f"umbrella entry '{name}' not found in {path}")
PY
else
  echo "release.sh: note: no --umbrella given — will print the manual umbrella edit instead of updating it." >&2
fi

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
git tag -a "$TAG" -m "sdlc-lite $TAG"
SHA="$(git rev-parse "$TAG^{commit}")"
echo "→ tagged $TAG @ $SHA"

# ── step 4: repoint the umbrella entry (ref + sha) ───────────────────────────
UMBRELLA_COMMITTED=0
if [[ -n "$UMBRELLA_DIR" ]]; then
  python3 - "$UMBRELLA_CATALOG" "$UMBRELLA_ENTRY" "$TAG" "$SHA" <<'PY'
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
  git -C "$UMBRELLA_DIR" add "$UMBRELLA_CATALOG_REL"
  git -C "$UMBRELLA_DIR" commit -q -m "release: point $UMBRELLA_ENTRY → $TAG ($SHA)"
  UMBRELLA_COMMITTED=1
  echo "→ repointed umbrella $UMBRELLA_ENTRY → ref=$TAG sha=$SHA (committed in $UMBRELLA_DIR)"
else
  echo "→ umbrella NOT updated (no --umbrella). Apply this edit by hand in $UMBRELLA_SLUG:"
  echo "     in $UMBRELLA_CATALOG_REL, entry '$UMBRELLA_ENTRY'.source → set:"
  echo "        \"ref\": \"$TAG\","
  echo "        \"sha\": \"$SHA\""
  echo "     then commit and push that repo."
fi

# ── step 5: push both repos (with confirmation) ──────────────────────────────
# Order matters: push the product tag FIRST so the umbrella ref resolves for customers.
if [[ "$PUSH" -eq 1 ]]; then
  read -r -p "Push $REPO_SLUG ($DEFAULT_BRANCH + $TAG)${UMBRELLA_COMMITTED:+ and $UMBRELLA_SLUG ($DEFAULT_BRANCH)} to origin? [y/N] " ans
  if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
    git push origin "$DEFAULT_BRANCH"
    git push origin "$TAG"
    echo "→ pushed $REPO_SLUG $DEFAULT_BRANCH and $TAG"
    if [[ "$UMBRELLA_COMMITTED" -eq 1 ]]; then
      git -C "$UMBRELLA_DIR" push origin "$DEFAULT_BRANCH"
      echo "→ pushed $UMBRELLA_SLUG $DEFAULT_BRANCH"
    fi
  else
    PUSH=0
    echo "→ push skipped; local commits + tag are ready (umbrella commit local too, if made)"
  fi
fi

# ── verify handoff (THE GATE — RELEASING.md §4 step 5) ───────────────────────
cat <<EOF

────────────────────────────────────────────────────────────────────────────
$TAG is prepared${PUSH:+ and pushed}. It is NOT a real release until VERIFIED.

Clean-room verify (isolated env, NO dev marketplace — see ADR-13 / RELEASING.md §4):
  1. From a fresh Claude config (own CLAUDE_CONFIG_DIR/HOME, toolchain installed):
       claude plugin marketplace add $UMBRELLA_SLUG
       claude plugin install $UMBRELLA_ENTRY@$UMBRELLA_MARKETPLACE
  2. Confirm the install log shows a genuine GitHub clone/checkout of $TAG
     (NOT a local directory source), and the cached version is $VERSION.
  3. Run /implement-feature end-to-end on test-fixtures/python-starter — it must pass.
  4. Only after that passes is $TAG a real release. If it fails: fix, delete the
     tag (git tag -d $TAG && git push origin :$TAG), revert the umbrella commit,
     and re-run release.sh.
────────────────────────────────────────────────────────────────────────────
EOF
