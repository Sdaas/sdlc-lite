#!/usr/bin/env bash
# Scaffolds one standard test fixture into a fresh, ephemeral scratch git repo
# inside the dev container, ready for /implement-feature to run against.
#
# Usage (run on the Mac, from the repo root):
#   test-fixtures/setup-fixture.sh <slug>
#
# What it does, inside the container:
#   1. Refuses if /workspaces/<slug>-run already exists (no silent wipe — a
#      stale scratch dir is removed by hand, same philosophy as the
#      workflow's own .active-run lock).
#   2. Copies test-fixtures/python-starter/<slug>/ to /workspaces/<slug>-run/.
#   3. git init's a fresh repo there on branch `main` and commits the copied
#      baseline — so /implement-feature's "never commit on default branch"
#      guard forces it onto a feature branch, per #21's design.
#   4. `pip install -e .` so the package is importable (Gate 0's preflight).
#
# This is the reusable building block #21 (clean-container-per-run) and #34
# (agent-driven regression harness) are expected to wrap later — it does not
# itself destroy/rebuild the container or drive the workflow.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: test-fixtures/setup-fixture.sh <slug>" >&2
  exit 1
fi

slug="$1"
template_dir="test-fixtures/python-starter/${slug}"
scratch_dir="/workspaces/${slug}-run"

if [[ ! -d "${template_dir}" ]]; then
  echo "No such fixture template: ${template_dir}" >&2
  exit 1
fi

devcontainer exec --workspace-folder . bash -c "
  set -euo pipefail
  if [[ -e '${scratch_dir}' ]]; then
    echo 'Scratch dir already exists: ${scratch_dir} — remove it by hand first (rm -rf ${scratch_dir}) if it is stale.' >&2
    exit 1
  fi
  cp -r '/workspaces/sdlc-lite/${template_dir}' '${scratch_dir}'
  cd '${scratch_dir}'
  git init -q -b main
  git config user.name 'SDLC Test Fixture'
  git config user.email 'fixture@sdlc-lite.local'
  git add -A
  git commit -q -m 'fixture baseline: ${slug}'
  pip install -e . --quiet
  echo \"Fixture ready: ${scratch_dir} (branch main, package installed editable)\"
"
