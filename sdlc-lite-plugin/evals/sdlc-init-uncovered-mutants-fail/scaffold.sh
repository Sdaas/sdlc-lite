#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_fixtures/python-starter.sh"
python_starter flat configured

# #101: mutants exist, but no test reaches them. mutmut prints the same "could not find any test
# case for any mutant" message as the nothing-to-mutate case — this one must stay a failure.
cat > tests/test_romankit.py <<'PY'
def test_placeholder() -> None:
    assert True
PY
git add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m "tests do not touch romankit"
