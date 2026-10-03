#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_fixtures/python-starter.sh"
source "$(dirname "$0")/../_fixtures/roman-handoff.sh"
python_starter flat
roman_handoff gate-7
plan=.implement-feature/37-to-roman/handoff/04-test-plan.md
sed -i.bak 's/^Coverage threshold: 100%\. Mutation kill-rate: .*/Coverage threshold: 100%. Mutation kill-rate: skip — the known-values table pins all 13 symbol pairs; every mutant left is an equivalent rewrite of the greedy walk (approved at Gate 2)./' "$plan"
rm -f "$plan.bak"
grep -q 'kill-rate: skip' "$plan"
