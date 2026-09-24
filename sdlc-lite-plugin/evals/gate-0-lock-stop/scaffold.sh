#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_fixtures/python-starter.sh"
python_starter flat
mkdir -p .implement-feature/00-earlier-run-202609240900/handoff
printf "%s\n" "$PWD/.implement-feature/00-earlier-run-202609240900" > .implement-feature/.active-run
