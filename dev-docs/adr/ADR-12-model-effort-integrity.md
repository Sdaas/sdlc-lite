# ADR-12 — Model and effort integrity: honored pins, verified by the receipt

**Context**
- #22 added a hook denying any dispatch without an inline model, assuming frontmatter pins are
  dropped otherwise. That premise is false
  ([`model-pinning-findings.md`](../findings/model-pinning-findings.md) §2, §7).
- The inline `model` slot accepts only family aliases, so forcing it collapsed the dated reviewer
  pin to floating `opus`. #36 reverted #22.

**Decision**
- Pinned gates are dispatched **bare** (no inline `model`), so the frontmatter pin governs.
- Nothing enforces model or effort at dispatch.
- The receipt compares actual vs pin: model mismatch = **FAIL**, effort deviation = **WARN**.
- Both pins come from one reader, [`agentdefs.py`](../../sdlc-lite-plugin/agentdefs.py).

**Consequences**
- Bare dispatch is the only way to honor a dated pin (ADR-2).
- Effort has no inline override: it can only be proven, never forced.
- The receipt always reports actual model and effort, so a broken pin is never hidden.
