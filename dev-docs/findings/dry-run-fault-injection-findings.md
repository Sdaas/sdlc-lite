# Finding: early dry runs, and transport-level vs response-level faults

**Status:** settled. The rule it produced is in force (see Consequence).

## Dry-run history

| Run | Result |
|---|---|
| `parse_duration` (first full run) | Core design validated; ~13 concrete improvements surfaced |
| `slugify` | Fixes confirmed |
| async `CachedFetcher` + fault injection | Invariants confirmed (below) |

Invariants confirmed across the later runs (transcript-proven):
- Reviews ran on Opus, producers on Sonnet.
- The test-writer stayed algorithm-blind.
- The implementer never touched a test file.
- The pipeline committed.

## Fault injection on `CachedFetcher`

**Method.** `httpx.MockTransport` through the feature's transport-injection seam: deterministic, no
network, no extra process. Injected:
- **Transport-level** faults: a handler that *raises* `ReadTimeout` / `ConnectTimeout` before any
  response exists (a different code path from `raise_for_status()`).
- **Response-level** faults: a handler returning a 5xx `Response`.
- Both under `asyncio.gather(...)`, to exercise request coalescing under fault.

**Result.** No bug:
- Timeouts and 5xx raise the right exception and are **not cached**.
- A coalesced wave issues one request; every caller sees the same fault.
- A fresh call afterwards recovers.

**Gap found in the method.** The test plan and resiliency review listed only response-level faults.
They confused "no *configurable* timeout" (a correct scope decision) with "no need to *test*
timeouts" (a coverage gap).

## Consequence

For any feature whose boundary inventory includes a **network boundary**, require at least one
**transport-level fault test** (timeout or connection failure raised before a response), asserting
it **propagates** and is **not cached**.

Applied to `quality-standards.md`, `test-plan-template.md`, `agents/test-writer.md`,
`agents/code-reviewer.md`.
