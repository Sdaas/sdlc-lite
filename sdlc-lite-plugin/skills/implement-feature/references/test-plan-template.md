# Test plan: <feature name>

> Canonical handoff file: **`04-test-plan.md`** (Gate 2 outbox; drafted at `handoff/draft/`,
> promoted on approval). Enumerates the tests that will PROVE the feature, and the
> thresholds the CODE-REVIEW gate enforces. Consumed by `test-writer` (what to write),
> `test-reviewer` (is it covered?), and `code-reviewer` (thresholds met?).

## Test inventory
Each test maps to an acceptance criterion or a boundary. Cover happy path, edge cases,
negative/error cases, and every boundary in the inventory. For an error case whose
exception message carries required diagnostic content, the row's assertion must pin the
message (`pytest.raises(T, match=…)`), not just the exception type. **For a network
boundary, include at least one transport-level fault test** (a timeout / connection failure
raised *before* a response) asserting it propagates and is **not cached** — distinct from
response-level (status / body) faults; see `quality-standards.md` → "Boundary resilience".

| ID | Level (unit/api/e2e) | What it asserts | Traces to (AC# / boundary) |
|----|----------------------|-----------------|----------------------------|
| T1 | unit | … | AC1 |
| T2 | unit | edge: empty input → … | AC3 |
| T3 | api  | … | AC5 |
| T4 | e2e  | real flow: … | AC1, boundary: fs |
| T5 | unit | transport fault: timeout/connection failure raised *before* a response → propagates as the expected type AND is **not cached** | boundary: network |

## Coverage target
- **Line/branch coverage ≥ <N>%** (`pytest-cov`). State the number and any justified
  exclusions.

## Mutation target
- **Mutation kill rate ≥ <M>%** (`mutmut`). **Default anchor: 80%** — start there and
  **justify any deviation right here**: raise for a small/safety-critical pure function,
  lower only with a stated reason (large surface, equivalent mutants). Surviving mutants
  below the chosen rate are treated as weak tests and block APPROVE at CODE-REVIEW.
  - Chosen: **<M>%** — Justification: <why this differs from 80%, or "default 80%">.

## Concurrency plan (fill only if the feature is concurrent/async)
- If the boundary inventory flags threads / async I/O / shared mutable state: list the
  property-based / stress / async tests (`hypothesis`, `pytest-asyncio`, stress loops
  under `python -X dev`) and the concurrency review focus (races, deadlocks, ordering,
  cancellation).
- Otherwise: **"No concurrency surface — skipped."**
