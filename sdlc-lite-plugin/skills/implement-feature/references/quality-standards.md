# Quality standards — the workflow's Definition of Done

> Single source of truth (T12). The conductor passes this file's absolute path to
> each agent's brief; agents apply it rather than restating it. To raise the bar,
> edit **this file** — not the individual gates or agents.

## Environment assumption
This workflow is **prescriptive about the dev container**: it runs inside the project
dev container (see `.devcontainer/`), where the pinned toolchain
(`sdlc-lite-plugin/toolchain/requirements-dev.txt`) is installed. It is not
supported to run on a bare host.

## Toolchain (pinned in the container)
| Tool | Purpose | Command |
|------|---------|---------|
| ruff | lint + format | `ruff check .` and `ruff format --check .` |
| mypy | static type checking | `mypy src/` |
| pytest | tests | `python -m pytest -q` |
| pytest-cov | coverage | `python -m pytest --cov=src --cov-report=term-missing` |
| mutmut | mutation testing | `mutmut run` then `mutmut results` |
| hypothesis / pytest-asyncio | property/stress/async (situational) | via the test files |

## Gate 0 preflight (hard-fail)
Before any work, the conductor verifies the environment. **If any check fails, STOP and
tell the human to rebuild/enter the dev container — do not proceed.**
```
ruff --version && mypy --version && pytest --version && python -c "import importlib.metadata as m; print('mutmut', m.version('mutmut'))"
```
(Also confirm we are inside the container, not the host.)

> **Why not `mutmut --version`?** mutmut eagerly loads its config on *any* invocation and
> hard-fails when run outside a project with a discoverable source layout (e.g. a bare
> scratch dir) — so `mutmut --version` false-fails the preflight. Check its installed
> version via package metadata instead (same approach as the `.devcontainer` postCreate).

## Definition of "green" — IMPLEMENT inner loop (fast checks)
The implementer may NOT exit its loop until ALL of:
1. `python -m pytest -q` — all tests pass.
2. `ruff check .` — clean (and `ruff format --check .`).
3. `mypy src/` — no type errors.

## CODE-REVIEW gate (slow checks) — thresholds live in the per-feature test plan
- **Coverage** ≥ the threshold set in `handoff/` test plan (`pytest-cov`).
- **Mutation kill rate** ≥ the threshold set in the test plan (`mutmut`); surviving
  mutants are reported as weak tests.

### Mutation kill-rate: default anchor 80% (justify any deviation)
The kill-rate stays **per-feature** (a 20-line pure function can reach 95%; a 2k-line
module can't), but it must not be free-picked — an agent handed a metric with no anchor
drifts (P46). So:
- **Start from 80%.** The DESIGN gate sets the test plan's kill-rate to **80% by default**.
- **Justify any deviation, in the test plan.** *Raise* it (e.g. 90–95%) for a small or
  safety-critical pure function; *lower* it only with a stated reason (large surface,
  hard-to-kill equivalent mutants). Record the rationale next to the number.
- **Surface it at DESIGN approval** so the human sees and can veto the chosen threshold
  (the human now reviews the real `04-test-plan.md`, where the number + justification live).

## Concurrency policy (situational — driven by the boundary inventory)
- If the feature is concurrent/async (threads, async I/O, shared mutable state), the
  Gate 2 **test plan MUST** include property-based + stress tests (`hypothesis`,
  `pytest-asyncio`, stress loops run under `python -X dev` with `faulthandler`), and
  CODE-REVIEW MUST include a concurrency-focused review item (races, deadlocks,
  ordering, cancellation).
- If the feature is not concurrent, state that once ("no concurrency surface") and skip
  — same shape as a VERIFY skip.

## Boundary resilience (situational — driven by the boundary inventory)
- If the boundary inventory includes a **network** boundary, the Gate 2 **test plan MUST** include at
  least one **transport-level fault** test — a **timeout / connection failure raised *before* a
  response exists** (e.g. `httpx.ReadTimeout` / `ConnectTimeout`) — asserting the fault **propagates**
  (as the expected exception type) and is **not cached**. This is **distinct from response-level
  faults** (non-2xx status, malformed body): a transport fault is a different code path (it never
  reaches `raise_for_status()`), and it is a real runtime path for *any* network call — even when a
  *configurable* timeout is (correctly) out of scope. Do not conflate "no configurable timeout" (a
  scope decision) with "no need to test timeout behavior" (a coverage gap).
- CODE-REVIEW's **reliability & resilience** dimension MUST confirm this transport-fault behavior for
  every network boundary, alongside response-level error handling.
- If there is no network boundary, this is skipped like any other situational check.

## Best-practices the reviews enforce
Modularity/cohesion · purity / minimal side-effects · clear naming · full type
annotations · docstrings on public surface · honor the constraints in `01-requirements.md`.

**Error-path tests assert the exception _message contract_, not just the type.** When the
interface specifies that an exception's message carries diagnostic content (e.g. the
offending type or value), use `pytest.raises(T, match=…)` — a bare `pytest.raises(T)` lets
a mutated/garbled message ship undetected.
