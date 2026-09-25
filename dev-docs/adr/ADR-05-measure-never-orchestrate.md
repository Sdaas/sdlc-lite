# ADR-5 — Observability measures; it never orchestrates

**Context**
- "Did the forbidden read happen?" is a grep-and-count fact.
- An LLM summarizer is non-deterministic and can hallucinate a compliance pass.
- An analyzer *agent* would be a second AI acting inside the system — a driver by another name.

**Decision**
- The analyzer is deterministic Python that runs after a run and only reads.
- Code is allowed only to **measure** (analyzer) or **enforce** (guard), never to orchestrate.

**Consequences**
- A monitoring tool must **fail loud**: route even unknown failures to a visible alarm.
- A silent, hollow report is worse than a false but loud alarm.
