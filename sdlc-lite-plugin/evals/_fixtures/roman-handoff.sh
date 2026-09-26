#!/usr/bin/env bash
# Shared scaffold: an /implement-feature run for `to_roman`, parked at a given gate.
#
# Sourced by a case's scaffold.sh after `python_starter flat`. Not a case itself: it has no
# prompt.md. Writes the promoted handoff files a subagent at that gate would find, and the
# .active-run pointer the guard hook uses to locate the run.
#
#   roman_handoff gate-3   # 01, 02, 04 — the test-writer's inbox
#   roman_handoff gate-4   # + 03, 05 and tests/test_roman.py — the test-reviewer's inbox
set -euo pipefail

roman_handoff() {
  local gate="$1" run=".implement-feature/37-to-roman" h
  h="$run/handoff"
  mkdir -p "$h"
  printf "%s\n" "$PWD/$run" > .implement-feature/.active-run

  cat > "$h/01-requirements.md" <<'EOF'
# 01 — Requirements: to_roman

Add `to_roman(n)` to romankit: convert an integer from 1 to 3999 to its Roman numeral.

## Functional ACs
- AC1: returns the standard (subtractive) Roman numeral for every n in 1..3999.
- AC2: a non-int argument is rejected with a TypeError that names the type received.
- AC3: an int outside 1..3999 is rejected with a ValueError that names the value received.

## Non-functional ACs
N/A — pure function, trivial input size.

## Constraints
Standard library only.

## Boundary inventory
None (pure feature).
EOF

  cat > "$h/02-design-interface.md" <<'EOF'
# 02 — Design (interface)

```python
from romankit import to_roman

def to_roman(n: int) -> str: ...
```

## Behavior
- `to_roman(1) == "I"`, `to_roman(1994) == "MCMXCIV"`, `to_roman(3999) == "MMMCMXCIX"`.

## Errors — message contract
| Condition | Exception | Message |
|---|---|---|
| `n` is not an `int` | `TypeError` | `expected int, got <type name>` — e.g. `expected int, got str` |
| `n` < 1 or `n` > 3999 | `ValueError` | `out of range (1..3999): <n>` — e.g. `out of range (1..3999): 0` |
EOF

  cat > "$h/04-test-plan.md" <<'EOF'
# 04 — Test plan

All tests in `tests/test_roman.py`.

| Test | Traces to | Kind |
|---|---|---|
| `test_to_roman_known_values` — 1, 4, 9, 14, 40, 90, 400, 900, 1994, 3999 | AC1 | unit |
| `test_to_roman_non_int_raises_type_error` — "5", 2.5, None | AC2 | unit |
| `test_to_roman_zero_raises_value_error` | AC3 | unit |
| `test_to_roman_negative_raises_value_error` | AC3 | unit |
| `test_to_roman_4000_raises_value_error` | AC3 | unit |

Coverage threshold: 100%. Mutation kill-rate: 80%.
EOF

  [ "$gate" = gate-3 ] && return 0

  cat > "$h/03-design-internal.md" <<'EOF'
# 03 — Design (internal)

Validate type, then range; then a greedy walk over the 13 value/symbol pairs
(1000 M, 900 CM, 500 D, 400 CD, 100 C, 90 XC, 50 L, 40 XL, 10 X, 9 IX, 5 V, 4 IV, 1 I).
EOF

  cat > "$h/05-test-intent.md" <<'EOF'
# 05 — Test intent

- `test_to_roman_known_values` — AC1: every subtractive pair plus both range ends.
- `test_to_roman_non_int_raises_type_error` — AC2: str, float and None are rejected.
- `test_to_roman_zero_raises_value_error` — AC3: lower bound, off by one.
- `test_to_roman_negative_raises_value_error` — AC3: negatives.
- `test_to_roman_4000_raises_value_error` — AC3: upper bound, off by one.
EOF

  cat > tests/test_roman.py <<'EOF'
import pytest

from romankit import to_roman


@pytest.mark.parametrize(
    ("n", "expected"),
    [(1, "I"), (4, "IV"), (9, "IX"), (14, "XIV"), (40, "XL"), (90, "XC"),
     (400, "CD"), (900, "CM"), (1994, "MCMXCIV"), (3999, "MMMCMXCIX")],
)
def test_to_roman_known_values(n: int, expected: str) -> None:
    assert to_roman(n) == expected


@pytest.mark.parametrize("bad", ["5", 2.5, None])
def test_to_roman_non_int_raises_type_error(bad: object) -> None:
    with pytest.raises(TypeError):
        to_roman(bad)  # type: ignore[arg-type]


def test_to_roman_zero_raises_value_error() -> None:
    with pytest.raises(ValueError, match=r"out of range \(1\.\.3999\): 0"):
        to_roman(0)


def test_to_roman_negative_raises_value_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"out of range \(1\.\.3999\): -7",
    ):
        to_roman(-7)


def test_to_roman_4000_raises_value_error() -> None:
    with pytest.raises(ValueError, match=r"out of range \(1\.\.3999\): 4000"):
        to_roman(4000)
EOF
}
