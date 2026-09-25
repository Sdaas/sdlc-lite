# ADR-11 — Isolation is proven by intent *and* effect: one policy, two legs

**Context**
- Enforcer and detective once kept hand-copied predicates ("KEEP IN SYNC"), so one Bash trick
  bypassed both.
- A string-inspecting hook cannot know what `python -c …` or `cd handoff && cat *` actually reads.

**Decision**
- One declarative policy: [`policy.py`](../../sdlc-lite-plugin/policy.py) (rule table +
  `decide(agent_type, access, path)`).
- Two independent legs import it:
  - **Intent** — `guard.py`, real-time, best-effort for Bash.
  - **Effect** — the analyzer's auditor: scans each gate's tool *output* for protected content.
    Authoritative and trust-voiding. Path extraction only corroborates.

**Consequences**
- The legs cannot drift; a role's rules are tightened in one place.
- A leak lands in one scan however it was read (Bash `stdout`, Read `file.content`, Edit
  `originalFile`).
- No transcript → **UNKNOWN**, never PASS.
