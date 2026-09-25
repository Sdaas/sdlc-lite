# Developer Guide — architecture, decisions, and how to work on the plugin

This guide is for someone improving `implement-feature`. It covers the architecture, the real code
(the guard hook and the analyzer), the decisions behind them (ADRs), the design principles, and the
testing method. To *run* the plugin, read the [README](../README.md). For the underlying concepts,
start with the [Tutorial](tutorial.md). For versioning, issue triage, and releases, see
[`RELEASING.md`](RELEASING.md).

---

## 0. Recommended reading order

Read §1 and §2 first. Read §6 (ADRs) before you propose a structural change. Read §8, §9 and §10
(this repo's own slash commands) when you are ready to make a change. The other sections are
reference.

---

## 1–5. Architecture

Moved to [`architecture.md`](architecture.md): gates, handoff, model pins, guard hook, analyzer.

---

## 6. Architecture decision records (ADRs)

Moved to [`adr/`](adr/README.md): one file per ADR, with a one-line index.

---

## 7. Design principles (distilled)

The load-bearing principles for anyone changing the plugin.

**Skills & workflow**
- **Trigger-oriented descriptions.** A skill's `description` decides when it activates. Write it about
  situations and phrasings, not just what the skill is.
- **One name, one surface; explicit entry (ADR-14).** A command never shares a skill's name, and this
  plugin's skills run only when a human types the slash command.
- **Driverless workflow.** The skill body is an ordered English script; numbered gates, machine
  conditions and "repeat until" loops replace orchestration code.
- **Gate = approval checkpoint.** The approver is a human (STOP-until-APPROVED, worded imperatively) or
  a machine-checkable condition ("until all tests pass"). Choose per phase.
- **Bound every automated loop** and surface to the human on no progress.

**Subagents & handoff**
- **Context-as-files handoff.** Each gate reads a defined inbox and writes a defined outbox as files.
  Files are durable, and they let you choose what an agent sees.
- **Asymmetric inboxes** — blind the producer (test-writer), inform the critic (test-reviewer).
- **Standards live in one file, not in each brief.** Briefs load `quality-standards.md`; to raise the
  bar, edit that file. Per-feature numbers (coverage/mutation) live in the test plan; universal
  commands and the definition of "green" live in `quality-standards.md`.
- **Anchored defaults beat free choice.** Ship a documented anchor (mutation kill-rate 80%) and require
  a justification to deviate, surfaced at approval. An agent given a metric with no anchor drifts.

**Quality gating**
- **Split checks by speed.** Fast checks (`ruff` + `mypy` + `pytest`) define the implementer's
  inner-loop "green"; slow checks (`pytest-cov` + `mutmut`) gate CODE-REVIEW.
- **Situational checks are boundary-driven.** Concurrency testing is required only when the boundary
  inventory shows the feature is concurrent/async; otherwise it is skipped with a stated reason.
- **VERIFY ≠ green tests.** Drive the real feature on each AC and exercise every boundary un-mocked; a
  mocked test only proves the mock. Unit-green is the inner loop (IMPLEMENT); observed behavior is the
  outer loop (VERIFY, a fresh read-only agent).
- **Mutation grades tests after the fact.** A surviving mutant is an injected bug no test caught, so
  mutation at CODE-REVIEW scores the test-writer and test-reviewer.
- **A critic may probe, never implement.** A reviewer may write tiny throwaway probes but must not
  build a reference implementation. Empirical mutation belongs at CODE-REVIEW, against the real code.
- **Don't let the producer grade its own homework.** When an agent's acceptance criteria live in
  files it could edit (the implementer and the tests), deny it write access to them by role.

**Enforcement & observability**
- **Defense-in-depth** — role instruction *and* hook.
- **Ship reliability-critical config with the plugin**, not project settings (headless-fire).
- **Verify runtime behavior; don't trust docs or config.** Model, tool blocks, hook firing and agent
  naming were all confirmed empirically. The docs were wrong on plugin-agent naming (it is namespaced,
  `plugin:agent`) and unsure on headless hooks.
- **Attribute every tool call** via `agent_type`/`agent_id`, for per-agent rules and a trustworthy
  audit.

---

## 8. Testing & dry-run methodology

- Tiers and release gate: [`verification-ladder.md`](verification-ladder.md).
- Container, auth, entry-point check, reading run files: [`DEVCONTAINER.md`](DEVCONTAINER.md).
- Fixtures and how to run one: [`test-fixtures/README.md`](../test-fixtures/README.md).
- Dry-run history and the transport-fault rule: [finding](findings/dry-run-fault-injection-findings.md).

---

## 9. When you edit the product

- **Behavior lives in Markdown** — `SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`. Editing the
  workflow means editing these, not writing code.
- **Change a gate's model/effort/tools** → edit the matching `agents/*.md` frontmatter (effort is
  frontmatter-only).
- **Change what an agent may read/write** → update *both* the agent's prose inbox **and** `policy.py`
  (defense-in-depth). `guard.py` and the analyzer both import it, so there is nothing to mirror.
- **Change "green" or a threshold policy** → edit `references/quality-standards.md` (the single source
  of truth), not individual briefs.
- **Verify before you rely on runtime behavior** — do a container dry run; the transcript and the
  guard's audit log are your ground truth.

---

## 10. Repo-local skills (for working on this repo)

This repo carries its own slash commands in `.claude/skills/`. They are **not** part of the shipped
plugin — they load only when you run Claude Code from this repo's root, and only a human can start
them (type the command; the model never invokes them). All share one process,
[`.claude/sdlc/gates.md`](../.claude/sdlc/gates.md); why this repo needs its own rather than using
`sdlc-lite` on itself: [`verification-ladder.md`](verification-ladder.md) §6.

| Command | What it does | Status |
|---|---|---|
| `/issue` | Files one GitHub issue per [`issue-template.md`](issue-template.md), after you approve the draft | available |
| `/feature` | Implements an issue through gates 0–8 with 4 approval STOPs | planned — #52 |
| `/fix` | `/feature` plus REPRODUCE and DEPOSIT gates for bugs | planned — #53 |
| `/regression` | Runs the whole eval suite, 3 runs per case | planned — #64 |
