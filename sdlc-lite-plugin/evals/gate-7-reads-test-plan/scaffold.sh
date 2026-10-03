#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_fixtures/python-starter.sh"
source "$(dirname "$0")/../_fixtures/roman-handoff.sh"
python_starter flat
roman_handoff gate-7

# The conductor's Gate 7 measurements (#40): the reviewer grades these, never runs the tools.
q=.implement-feature/37-to-roman/quality
mkdir -p "$q"
cat > "$q/coverage.txt" <<'COV'
---------- coverage: platform linux, python 3.12 -----------
Name                   Stmts   Miss  Cover   Missing
----------------------------------------------------
romankit/__init__.py       4      0   100%
romankit/roman.py         10      0   100%
----------------------------------------------------
TOTAL                     14      0   100%
COV
{
  for i in $(seq 1 18); do echo "    romankit.roman.x_to_roman__mutmut_$i: killed"; done
  echo "    romankit.roman.x_to_roman__mutmut_19: survived"
  echo "    romankit.roman.x_to_roman__mutmut_20: survived"
} > "$q/mutation.txt"
