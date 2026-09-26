# #31b-iii finding — bare `pytest.raises(T)` survived Gate 3 + Gate 4, caught only at Gate 7

_P1 and P2 applied in #37 (2026-09-26), with corrections to the drafts below: the grep covers only this
run's test files (not all of `<tests_root>`, which would sweep in unrelated pre-existing tests), each
hit's full call is read since `match=` may sit on the next line, and `as excinfo` plus an assert on
the message counts as pinned. P3 is not
applied. Drafted during the roman-numeral clean acceptance run (2026-09-18)._

## What happened

Gate 7 (CODE-REVIEW) found 9 surviving mutants in `converter.py`, all the same class: three
error-path tests (`test_int_to_roman_non_int_raises_type_error`,
`test_roman_to_int_empty_string_raises_value_error`, `test_roman_to_int_non_str_raises_type_error`)
used a bare `pytest.raises(T)` instead of `pytest.raises(T, match=…)`, so a mutated/garbled
exception message would ship undetected. This forced a loop back through Gate 3 (WRITE-TESTS) and
Gate 4 (TEST-REVIEW).

## Why this is notable — it wasn't a missing rule

The rule was already written down in **three places**, correctly worded, before the test-writer
ever ran:
- `implement-feature-plugin/skills/implement-feature/references/quality-standards.md` — "Error-path
  tests assert the exception _message contract_, not just the type... a bare `pytest.raises(T)` lets
  a mutated/garbled message ship undetected."
- `implement-feature-plugin/agents/test-writer.md` step 1 — near-identical wording, told to the
  test-writer directly.
- `implement-feature-plugin/agents/test-reviewer.md` Judge section — "A bare `pytest.raises(T)` with
  no `match=` is a weak test when the contract specifies message content — flag it."

Both the test-writer (`sonnet`, `effort: medium`) and the test-reviewer (`claude-opus-4-8`,
`effort: low`) had this instruction in front of them and missed all three instances in one pass.
This is a durability problem, not a documentation gap: a correctly-written prose rule, repeated at
two separate gates, still wasn't reliably applied.

## Why it didn't need to wait for Gate 7

Unlike most of what Gate 7's mutation run measures, "does every `pytest.raises(T)` in this file
carry a `match=`" is pure syntax over the test file alone — no implementation required to check it.
It could have been caught at Gate 4 (or even self-caught at Gate 3) with zero dependency on code
existing. The loop happened because *reasoning* missed a *mechanical* pattern, not because the
finding was structurally undetectable before Gate 7.

## Recommendation (not yet applied)

Two prose-only additions, cheapest-first, both effort-independent (they don't rely on the model
"remembering" to apply the rule — they make checking it a required step):

**P1 — test-writer self-check (`agents/test-writer.md`, step 1 or a new step between 1 and 2).**
Before finalizing the test file, grep it for `pytest.raises(` calls lacking `match=` and justify or
fix each one against `02-design-interface.md`'s documented message contract. Draft addition:

> **Self-check before finishing:** `grep -n "pytest.raises(" <tests_root>/**/*.py` and for every hit
> without `match=`, confirm against `02-design-interface.md` whether that exception's message
> carries diagnostic content. If it does, add `match=…`; if the interface genuinely specifies no
> message content for that raise, leave it bare — don't add `match=` for a contract that doesn't
> exist.

**P2 — test-reviewer procedural step (`agents/test-reviewer.md`, Judge section).** Convert the
existing "flag it" prose into an explicit first step rather than a note buried in the mutation-minded
analysis:

> **Before the rest of the review:** `grep -n "pytest.raises(" <tests_root>/**/*.py`. For every hit
> without `match=`, check `02-design-interface.md` for a documented message contract on that
> exception; a bare `pytest.raises(T)` against a documented message contract is a CHANGES-REQUESTED
> finding on its own, not just a note.

**P3 — optional, bigger lift, not proposed for now.** A real deterministic lint (alongside
`ruff`/`mypy`) that flags this pattern automatically, run at Gate 4 and Gate 7, independent of model
effort entirely. More robust than P1/P2 but real engineering scope — track separately if this class
of miss recurs after P1/P2 ship.

## Relationship to #28 / #35

`test-reviewer` runs at `effort: low` right now *by design* — #28's dev-spread exists so the audit
can prove it observes effort levels, not as a production quality bar; `plan.md` already schedules
flipping every gate to `effort: medium` (#35) once this acceptance run completes. This run is a live
data point for that: at low effort, an Opus reviewer missed an explicit, matching rule three times
in one file. That said, P1/P2 are recommended as effort-independent fixes in their own right — a
mechanical "did you check for X" step is more reliable than raising effort, and stays valuable after
#35 ships.
