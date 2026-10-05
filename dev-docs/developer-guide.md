# Developer Guide — how to change the plugin

The hub for someone changing `sdlc-lite`. New here? Read [`jumpstart.md`](jumpstart.md) first.
To *run* the plugin, see the [README](../README.md).

---

## 1. Where things are explained

| I want to understand… | Read |
|---|---|
| The repo, one run end to end, key components | [`jumpstart.md`](jumpstart.md) |
| Concepts (plugin, skill, subagent isolation) | [`tutorial.md`](tutorial.md) |
| Gates, handoff, model pins, guard rules, analyzer | [`architecture.md`](architecture.md) |
| *Why* a part is shaped this way | [`adr/`](adr/README.md) |
| How much proof a change needs | [`verification-ladder.md`](verification-ladder.md) |
| Writing an eval case | [`evals/README.md`](../sdlc-lite-plugin/evals/README.md) |
| Container, auth, entry-point check | [`DEVCONTAINER.md`](DEVCONTAINER.md) |
| Dry-run fixtures; reset for a run: `make clean-run` | [`test-fixtures/README.md`](../test-fixtures/README.md) |
| Hands-off T3 run (tmux; you attach and answer STOPs): `make t3-start SLUG=<slug>` | [`t3-runs.md`](t3-runs.md) |
| Channels, releases, issue triage | [`RELEASING.md`](RELEASING.md) |
| Evidence behind decisions | [`findings/`](findings/) |

---

## 2. Change X → edit Y → verify with Z

Paths are under `sdlc-lite-plugin/`. Tiers: T1 = eval, T2 = pytest, T3 = container dry run
([ladder](verification-ladder.md) §3).

| Change | Edit | Also update | Verify |
|---|---|---|---|
| Gate wording, templates | `skills/implement-feature/SKILL.md`, `references/*-template.md` | — | T1 |
| Gate behavior (routing, loops, STOPs) | `SKILL.md` | [`architecture.md`](architecture.md) §2 if gates/loops change | T1 + T3 |
| "Green" or a threshold | `references/quality-standards.md` (only there) | — | T1 |
| A gate's model / effort / tools | `agents/<role>.md` frontmatter (effort is frontmatter-only) | [`architecture.md`](architecture.md) §2, §4 | T1 + T2, receipt on T3 |
| Bump a dated model pin | `agents/<role>.md` frontmatter (all five gates) | SKILL.md model table + Gate 0 render line, `tests/test_agentdefs.py` `EXPECTED`, ADR-2, architecture §2/§4 | T3 + receipt shows the exact id (#63) |
| What an agent may read / write | the agent's prose inbox **and** `policy.py` | [`architecture.md`](architecture.md) §3 inbox table, §5 rules | T2 (`tests/test_policy.py`) + T1 |
| A new guard rule | `policy.py` (+ `hooks/scripts/guard.py` / `hooks.json` matcher for a new tool) | architecture §5 rules table | T2 (+ T3 if `hooks.json`) |
| Add or rename a skill / command | `skills/<x>/` — **never** a `commands/<x>.md` of the same name (ADR-14) | `policy.PLUGIN_SKILL_NAMES` | T2 (`tests/test_entry_points.py`) + `verify-entry-points.py` |
| The toolchain floors or what `/sdlc-init` sets up | `toolchain/requirements-dev.txt`, `toolchain/setup_check.py` (measure only), `skills/sdlc-init/SKILL.md` | fixtures (`test-fixtures/`, `evals/_fixtures/python-starter.sh`) must match what it writes | T2 (`tests/test_setup_check.py`) + T1 `--tag sdlc-init` + T3 (`ENTRY=/sdlc-init VENV=1`) |
| Analyzer logic | `analyzer/*.py` | [`analyzer/README.md`](../sdlc-lite-plugin/analyzer/README.md) | T2 |
| Transcript format drifted | `analyzer/transcript.py` | [`TRANSCRIPT-FORMAT.md`](../sdlc-lite-plugin/analyzer/TRANSCRIPT-FORMAT.md) | T2 + a T3 run |
| A structural decision | new `adr/ADR-NN-slug.md` | row in [`adr/README.md`](adr/README.md) | review |
| Docs only | the doc | — | `./release-verify.sh --links-only` |

**Always:** runtime behavior is verified in a container run, not taken from docs. The transcript and
the guard's run-log are ground truth.

---

## 3. Review checklist

Check a change against these before approving it.

**Workflow prose**
- [ ] Skill `description` names trigger situations and says explicit-entry only (ADR-14).
- [ ] No `commands/<x>.md` shares a name with `skills/<x>/` (ADR-14).
- [ ] Every gate has an approver: a human STOP-until-APPROVED (imperative wording) or a
      machine-checkable condition.
- [ ] Every automated loop is bounded and surfaces to the human on no progress.
- [ ] Interview changes keep minimal-scope-first (ADR-9).

**Subagents & handoff**
- [ ] Context passes as files with a defined inbox/outbox, never a prior transcript.
- [ ] Producer blind, critic informed (ADR-3).
- [ ] Briefs load `quality-standards.md`; no standard is copied into a brief.
- [ ] Any metric ships with an anchored default (e.g. mutation kill-rate 80%); deviating needs a
      justification surfaced at approval.

**Quality gating**
- [ ] Fast checks (`ruff`, `mypy`, `pytest`) = implementer's green; slow checks (`pytest-cov`,
      `mutmut`) gate CODE-REVIEW.
- [ ] Situational checks (e.g. concurrency) run only when the boundary inventory calls for them;
      otherwise skipped with a stated reason.
- [ ] VERIFY drives the real code un-mocked; unit-green is not "done".
- [ ] Network boundary → at least one transport-level fault test
      ([finding](findings/dry-run-fault-injection-findings.md)).
- [ ] A critic may probe, never build a reference implementation.
- [ ] No agent can edit the files its own acceptance depends on.

**Human-read docs** (§5)
- [ ] Short sentences, active voice, imperative steps; one word for one meaning.
- [ ] No version numbers in `README.md`; it links to `CHANGELOG.md` for releases.

**Enforcement & observability**
- [ ] A prose rule the guard should enforce has a `policy.py` rule **and** a T2 test.
- [ ] Reliability-critical config ships in the plugin, not project settings (ADR-1).
- [ ] Every tool call stays attributable via `agent_type` / `agent_id`.
- [ ] Measurement fails loud; no evidence = UNKNOWN, never PASS (ADR-5, ADR-11).
- [ ] Design and every review run on a higher model than implementation (ADR-2).
- [ ] Nothing commits before human approval, and never on the default branch (ADR-7).

---

## 4. Repo-local skills

Slash commands for working on **this repo**, in `.claude/skills/`. Not shipped. Human-typed only.
Gates, STOPs, when each fires and why they diverge from `sdlc-lite`:
[`repo-local-skills.md`](repo-local-skills.md).

| Command | What it does | Status |
|---|---|---|
| `/issue` | Files one GitHub issue per [`issue-template.md`](issue-template.md), after you approve the draft | available |
| `/feature` | Implements an issue through gates 0–11; you approve scope, design, tests and implementation | available |
| `/fix` | Fixes a `bug` issue: reproduces it first, runs `/feature`'s gates, and commits the reproducing case with the fix | available |
| `/review-repo` | Reviews the whole repo before a release with three area agents and one consolidator, pinned to Opus 5.5 / high and measured | available |
| `/regression` | Runs the whole eval suite, 3 runs per case | planned — #64 |

---

## 5. Writing: two audiences

Write each file for its reader. The cleanup that fits one reader harms the other.

| Audience | Files | Rule |
|---|---|---|
| **Agent-read** | `skills/*/SKILL.md`, `agents/*.md`, `references/*`, `.claude/skills/`, `.claude/sdlc/gates.md`, `CLAUDE.md` | Precise and unambiguous. Tuned for the pinned model. A prose change here changes behavior, so verify it with the eval suite against the baseline. |
| **Human-read** | `README.md`, `tutorial.md`, `developer-guide.md`, `architecture.md`, `DEVCONTAINER.md`, `ACCEPTANCE.md`, `RELEASING.md`, `CHANGELOG.md` | **ASD-STE100 at about 80%.** A prose change here changes no behavior, so the link check is enough. |
| **Historical** | `adr/`, `findings/`, `proposals/`, `review-YYYYMMDD.md` (repo root) | Do not rewrite the prose. Fix a broken link only. |

**The human-read style.** The ASD-STE100 standard is a controlled language for maintenance
documentation. We follow about 80% of it. This is a target, not a lint rule.

- Keep sentences short. One idea in each sentence.
- Use the active voice. Write "Run `/sdlc-init`", not "`/sdlc-init` should be run".
- Write steps as commands (imperative), one action in each step.
- Use one word for one meaning. Do not swap "gate", "step" and "stage" for the same thing.
- Prefer a plain word to a clever one. Do not use idioms.

**Diagrams.** Add a mermaid diagram only where a picture shows a mechanism that prose cannot show
fast: the gate flow and the subagent isolation model. Do not add HTML pages.
