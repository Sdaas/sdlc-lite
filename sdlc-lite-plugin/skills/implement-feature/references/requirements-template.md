# Requirements — <feature name>

> Canonical handoff file: **`01-requirements.md`** (drafted at `handoff/draft/`, promoted
> to `handoff/` on approval). Written by the conductor at Gate 1 (INTERVIEW), approved by
> the human. This file — not the conversation — is the inbox for downstream gates. Keep it
> self-sufficient.

## 1. Summary
One paragraph: what the feature does and why, in the user's words.

### Scope boundary — smallest viable (confirmed FIRST, P57)
State the **minimal version** the human confirmed up front, and what is **deferred / out of
scope**. This is the anchor the interview grilled *within* — expansions beyond it were explicit
human opt-ins, not assumptions. (The detailed out-of-scope list lives in §6.)
- **Minimal version:** …
- **Deferred (not in this feature):** …

## 2. Functional acceptance criteria
Numbered, testable "done when…" statements. Cover inputs/outputs, core behavior,
error conditions, and edge cases.
- **AC1** — …
- **AC2** — …

## 3. Non-functional acceptance criteria
Explicit expectations (write "N/A — <reason>" if truly none):
- **Scale** — data sizes, request volumes, concurrency expected.
- **Performance** — latency/throughput targets, resource limits.
- **Security** — trust boundaries, input validation, secrets, authz/authn, data handling.
- **Other** — reliability, observability, compatibility, as applicable.

## 4. Constraints (mandated / forbidden)
Technology and design constraints the implementation MUST honor — e.g. "use jdbc not
spring", allowed/forbidden libraries, required patterns, style/version pins.
- **Must use** — …
- **Must not use** — …
- **Must follow** — …

## 5. Boundary inventory
Every external boundary this feature touches (drives VERIFY + the mock-obligation rule).
Write "None (pure feature)" if there are none.
| Boundary | Kind (network/subprocess/fs/entrypoint/dep) | How it will be exercised un-mocked at VERIFY |
|---|---|---|
| … | … | … |

## 6. Out of scope / assumptions
What this feature explicitly does NOT do; assumptions confirmed with the human.
