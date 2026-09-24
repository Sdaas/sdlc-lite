# dev-docs — for people improving or maintaining `sdlc-lite` itself

If you just want to **run** the plugin against your own Python repo, you don't need anything in
here — the root [`README.md`](../README.md) is the complete user-facing doc. Everything under
`dev-docs/` is for someone reading, extending, testing, or releasing the plugin's own source.

## Where to start

- **[`developer-guide.md`](developer-guide.md)** — architecture (conductor + isolated gates), the
  guard hook, the analyzer, the design decisions (ADRs), and the container testing methodology.
- **[`tutorial.md`](tutorial.md)** — the underlying concepts (plugin vs command vs skill vs
  workflow) and subagent isolation, built up from a minimal runnable example (`toy-greet-plugin/`).
- **[`verification-ladder.md`](verification-ladder.md)** — how much proof a change owes before it
  counts as done: the T1/T2/T3 tiers, which tier each kind of change needs, and the budget. Start
  here before changing any of the plugin's prose.
- **[`eval-tutorial.md`](eval-tutorial.md)** — how to author and run a `claude plugin eval` case
  (T1 on that ladder): case format, graders, the ablation delta, and the environment gotchas.
- **[`DEVCONTAINER.md`](DEVCONTAINER.md)** — the dev-container test harness lifecycle.
- **[`RELEASING.md`](RELEASING.md)** — versioning, issue triage, and how a release is cut and
  consumed.
- **[`release-plan.md`](release-plan.md)** — the current + next release roadmap (narrative +
  execution order; GitHub milestones are the source of truth for *which* issues ship).
- **[`issue-template.md`](issue-template.md)** — the required structure for every GitHub issue in
  this repo.

## `findings/` vs `proposals/`

Two directories hold write-ups that are easy to confuse — the split is:

- **`findings/`** — dated records of an investigation that already happened: what was probed, what
  was found, and the decision it fed into. **Settled** — referenced by the ADRs in the Developer
  Guide as the evidence behind a decision that's already in force.
- **`proposals/`** — design sketches for capabilities that are **not yet built**. Unwired: nothing
  in the shipped product depends on them, and they may never be built as written. Treat a proposal
  as a starting point for discussion, not as documentation of current behavior.

A reader should be able to tell which one they're looking at from the directory alone, without
checking the file's content or date.
