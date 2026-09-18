#!/usr/bin/env bash
#
# release.test.sh — sandbox tests for the cross-repo release.sh (ADR-13 / #41 Phase D).
#
# Exercises the REAL release.sh against throwaway git repos with --no-push, so nothing
# is tagged or pushed for real. Covers: happy-path bump+tag+umbrella-repoint, the
# no-umbrella manual-edit path, and preflight guards (semver, dirty tree, bad umbrella
# path fail-fast, existing tag). Run: bash release.test.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_SCRIPT="$HERE/release.sh"
[[ -f "$REAL_SCRIPT" ]] || { echo "release.test.sh: cannot find release.sh next to this test" >&2; exit 2; }

SBX="$(mktemp -d)"
trap 'rm -rf "$SBX"' EXIT
pass=0; fail=0
ok() { echo "  ok: $1"; pass=$((pass+1)); }
no() { echo "  FAIL: $1"; fail=$((fail+1)); }

gitcfg() { # local identity + no gpg signing, so the script's commits/tags succeed anywhere
  git -C "$1" config user.name Test
  git -C "$1" config user.email test@test
  git -C "$1" config commit.gpgsign false
  git -C "$1" config tag.gpgsign false
}
mk_product() { # $1=dir  $2=starting-version
  local d="$1"; mkdir -p "$d/sdlc-lite-plugin/.claude-plugin"
  cat > "$d/sdlc-lite-plugin/.claude-plugin/plugin.json" <<J
{ "name": "sdlc-lite", "version": "$2", "description": "x" }
J
  cp "$REAL_SCRIPT" "$d/release.sh"; chmod +x "$d/release.sh"
  git -C "$d" init -q; git -C "$d" branch -M main; gitcfg "$d"
  git -C "$d" add -A; git -C "$d" commit -q -m init
}
mk_umbrella() { # $1=dir
  local d="$1"; mkdir -p "$d/.claude-plugin"
  cat > "$d/.claude-plugin/marketplace.json" <<'J'
{
  "name": "sdaas",
  "plugins": [
    { "name": "sdlc-lite",
      "source": { "source": "git-subdir", "url": "https://github.com/Sdaas/sdlc-lite.git",
                  "path": "sdlc-lite-plugin", "ref": "v0.0.0" },
      "description": "x" }
  ]
}
J
  git -C "$d" init -q; git -C "$d" branch -M main; gitcfg "$d"
  git -C "$d" remote add origin "https://github.com/Sdaas/claude-plugins.git"
  git -C "$d" add -A; git -C "$d" commit -q -m init
}
getf() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2]))" "$1" "$2"; }

echo "== T1: happy path with --umbrella (--no-push) =="
P="$SBX/prod1"; U="$SBX/umb1"; mk_product "$P" "0.1.0"; mk_umbrella "$U"
( cd "$P" && ./release.sh 1.0.0-beta.1 --umbrella "$U" --no-push >"$SBX/t1.out" 2>&1 ) \
  && ok "script exit 0" || { no "script nonzero"; cat "$SBX/t1.out"; }
[[ "$(getf "$P/sdlc-lite-plugin/.claude-plugin/plugin.json" 'd["version"]')" == "1.0.0-beta.1" ]] && ok "plugin.json bumped" || no "plugin.json not bumped"
git -C "$P" rev-parse -q --verify refs/tags/v1.0.0-beta.1 >/dev/null && ok "tag created" || no "tag missing"
TAGSHA="$(git -C "$P" rev-parse 'v1.0.0-beta.1^{commit}')"
[[ "$(getf "$U/.claude-plugin/marketplace.json" 'd["plugins"][0]["source"]["ref"]')" == "v1.0.0-beta.1" ]] && ok "umbrella ref set" || no "umbrella ref wrong"
[[ "$(getf "$U/.claude-plugin/marketplace.json" 'd["plugins"][0]["source"]["sha"]')" == "$TAGSHA" ]] && ok "umbrella sha == tag sha" || no "umbrella sha wrong"
git -C "$U" diff --quiet && ok "umbrella committed (clean tree)" || no "umbrella left uncommitted"
[[ "$(git -C "$U" log --oneline | wc -l | tr -d ' ')" == "2" ]] && ok "umbrella has release commit" || no "umbrella commit count off"
grep -q "marketplace add Sdaas/claude-plugins" "$SBX/t1.out" && ok "verify handoff uses umbrella add" || no "handoff wrong add"
grep -q "install sdlc-lite@sdaas" "$SBX/t1.out" && ok "verify handoff uses sdlc-lite@sdaas" || no "handoff wrong install"

echo "== T2: no --umbrella prints manual edit, does not touch umbrella =="
P="$SBX/prod2"; mk_product "$P" "0.1.0"
( cd "$P" && ./release.sh 1.2.3 --no-push >"$SBX/t2.out" 2>&1 ) && ok "script exit 0" || { no "nonzero"; cat "$SBX/t2.out"; }
SHA2="$(git -C "$P" rev-parse 'v1.2.3^{commit}')"
grep -q "umbrella NOT updated" "$SBX/t2.out" && ok "prints not-updated notice" || no "missing notice"
grep -q "\"ref\": \"v1.2.3\"" "$SBX/t2.out" && ok "prints manual ref" || no "missing manual ref"
grep -q "\"sha\": \"$SHA2\"" "$SBX/t2.out" && ok "prints manual sha" || no "missing manual sha"

echo "== T3: preflight rejects bad semver =="
P="$SBX/prod3"; mk_product "$P" "0.1.0"
( cd "$P" && ./release.sh 1.0 --no-push >"$SBX/t3.out" 2>&1 ) && no "should have failed" || ok "rejected bad semver"
grep -q "not semver" "$SBX/t3.out" && ok "semver error message" || no "no semver msg"

echo "== T4: preflight rejects dirty tree, no mutation =="
P="$SBX/prod4"; mk_product "$P" "0.1.0"; echo dirty >> "$P/sdlc-lite-plugin/.claude-plugin/plugin.json"
( cd "$P" && ./release.sh 2.0.0 --no-push >"$SBX/t4.out" 2>&1 ) && no "should have failed" || ok "rejected dirty tree"
git -C "$P" rev-parse -q --verify refs/tags/v2.0.0 >/dev/null && no "tag wrongly created" || ok "no tag on dirty-tree fail"

echo "== T5: bad --umbrella path fails BEFORE mutating product (no tag) =="
P="$SBX/prod5"; mk_product "$P" "0.1.0"
( cd "$P" && ./release.sh 3.0.0 --umbrella "$SBX/nope" --no-push >"$SBX/t5.out" 2>&1 ) && no "should have failed" || ok "rejected bad umbrella"
git -C "$P" rev-parse -q --verify refs/tags/v3.0.0 >/dev/null && no "tag wrongly created" || ok "no tag when umbrella invalid (fail-fast)"
[[ "$(getf "$P/sdlc-lite-plugin/.claude-plugin/plugin.json" 'd["version"]')" == "0.1.0" ]] && ok "plugin.json untouched on umbrella-fail" || no "plugin.json mutated on umbrella-fail"

echo "== T6: existing tag rejected =="
P="$SBX/prod6"; mk_product "$P" "0.1.0"; git -C "$P" tag -a v5.0.0 -m x
( cd "$P" && ./release.sh 5.0.0 --no-push >"$SBX/t6.out" 2>&1 ) && no "should have failed" || ok "rejected existing tag"

echo ""
echo "RESULT: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]]
