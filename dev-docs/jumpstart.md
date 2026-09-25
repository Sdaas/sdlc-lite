# Jumpstart — a first read of this repo

The map for a developer new to this repo: what it ships, how a run flows, where each piece lives, and
how it's tested. It stays short on purpose. For depth, follow the links, mostly into
[`architecture.md`](architecture.md) (how it works), [`adr/`](adr/README.md) (why), and
[`developer-guide.md`](developer-guide.md) (how to change it).

---

## 1. What it is

- **Ships:** `sdlc-lite`, a Claude Code plugin. `/implement-feature <request>` turns a one-line
  request into a reviewed, tested, committed **Python** change.
- **How:** an interview → design → test-first → review workflow with a human at the approval gates.
- **Core idea: behavior lives in Markdown.** No Python drives the workflow. The agent reads
  `SKILL.md` and executes it.
- **Code only enforces or measures, never orchestrates ([ADR-5](adr/ADR-05-measure-never-orchestrate.md)).** The only real code:

  | Code | Job |
  |---|---|
  | `policy.py` + `hooks/scripts/guard.py` | **enforce** isolation on every tool call, in real time |
  | `analyzer/` + `agentdefs.py` | **measure** what actually happened, after the run |

---

## 2. Repo layout

```
sdlc-lite/
├── sdlc-lite-plugin/          # THE PRODUCT (what ships)
│   ├── skills/implement-feature/
│   │   ├── SKILL.md           # the conductor's score: every gate, in order
│   │   └── references/        # quality-standards.md (what "green" means) + handoff templates
│   ├── agents/*.md            # one per isolated gate: model / effort / tools + role brief
│   ├── hooks/hooks.json       # registers guard.py as a PreToolUse hook
│   ├── hooks/scripts/guard.py # real-time enforcer
│   ├── policy.py              # allow/deny rules (SSOT for guard + analyzer)
│   ├── agentdefs.py           # reads model/effort pins from agents/*.md
│   ├── analyzer/              # post-run reporter + receipt
│   ├── commands/analyze-run.md# /sdlc-lite:analyze-run (re-analyze a past run)
│   ├── tests/  hooks/tests/  analyzer/tests/   # pytest (T2)
│   └── evals/                 # `claude plugin eval` cases (T1)
├── toy-greet-plugin/          # minimal teaching example (tutorial.md)
├── test-fixtures/python-starter/  # committed fixture repo for dry runs (T3)
├── verify-entry-points.py     # scripted T3 slice: entry-point contract (ADR-14)
├── release.sh / release-verify.sh # cut / verify a release (RELEASING.md)
├── .devcontainer/             # the dev container: the only place to run the plugin
├── .claude/skills/, .claude/sdlc/ # repo-local tooling (/issue), not shipped
└── dev-docs/                  # you are here
```

---

## 3. One run, end to end

**Roles:**
- **[C] conductor**: your interactive session, running `SKILL.md`. It talks to you.
- **[I] isolated subagent**: fresh context, pinned model, file-only inbox. It's spawned by the
  namespaced type, e.g. `sdlc-lite:test-writer`.

**Why isolate:** a critic who watched the code get written shares the author's blind spots (so: fresh
context), and one model's blind spots repeat at every gate (so: reviews run on a stronger model).

Each gate below is a `## Gate N` section in
[`SKILL.md`](../sdlc-lite-plugin/skills/implement-feature/SKILL.md). Handoff files are written to
`.implement-feature/<run>/handoff/` (gitignored).

| # | Gate | Runs as (model) | Writes | Guard / rule enforced here |
|---|---|---|---|---|
| 0 | Classify + preflight | [C] | `.active-run` lock, run-log | lock check, toolchain preflight, layout + branch confirm. **You approve** |
| 1 | Interview | [C] | `01-requirements.md` | draft → you review the real file → promote ([ADR-8](adr/ADR-08-draft-review-promote.md)). **You approve** |
| 2 | Design | [C] | `02-design-interface`, `03-design-internal`, `04-test-plan` | **You approve** |
| 3 | Write tests | [I] `test-writer` (sonnet) | tests + `05-test-intent` | **cannot read `03`** (algorithm-blind, [ADR-3](adr/ADR-03-interface-internal-design-split.md)). Suite must go red |
| 4 | Test review | [I] `test-reviewer` (opus, dated) | `06-test-review-findings` | writes only to its outbox. Loops ↔ 3 |
| 5 | Implement | [I] `implementer` (sonnet) | code in `<code_root>` | **cannot edit tests** |
| 6 | Verify | [I] `verifier` (sonnet) | `07-verify-report` | read-only. Drives the real code un-mocked. Loops ↔ 5 |
| 7 | Code review | [I] `code-reviewer` (opus, dated) | `08-code-review-findings` | read-only. Tags findings `→IMPLEMENT` / `→TESTS` |
| 8 | Review guide | [C] | — (chat) | points you at files + findings |
| 9 | **Human review** | [C] | — | analyzer fast pass (`--no-transcript`). **You approve = ship** |
| 10 | Commit | [C] | git commit on the feature branch | never on the default branch ([ADR-7](adr/ADR-07-never-commit-default-branch.md)). Clears the lock |
| 11 | Report | [C] | `run-report.md` | full analyzer pass |

**What's true at every gate:**
- The guard audits every call and blocks secret reads for **all** agents.
- No subagent may read `handoff/draft/`.
- Every loop is **bounded**: no progress after N rounds → it stops and asks you.

**Two trees ([ADR-4](adr/ADR-04-product-vs-process.md)):**
- **Product:** code + tests, written in place on the branch.
- **Process:** handoff files + logs under gitignored `.implement-feature/`, never committed.

More detail: [`architecture.md`](architecture.md) §2–§3 (gate table, inbox/outbox table).

---

## 4. Key components

**`SKILL.md`: the score.**
- It's the authoritative description of the workflow. [`architecture.md`](architecture.md) is only a map of it.
- "Green" and all thresholds live in `references/quality-standards.md`. Change them there, not in
  the briefs.

**`agents/*.md`: casting.**
- Frontmatter pins `model`, `effort`, `tools` / `disallowedTools`. The body is the role brief.
- Reviewers pin a dated `claude-opus-4-8` (reproducible). Producers pin the `sonnet` alias
  ([ADR-2](adr/ADR-02-dated-reviewer-pins.md)).
- Invariant: design + reviews run on a higher model than implementation.

**`policy.py` + `guard.py`: enforcement** ([`architecture.md`](architecture.md) §5).
- `policy.py`: `POLICY` (per-role rules) and `decide()` (the single verdict function), plus path
  predicates (`is_secret_path`, `is_design_internal`, `is_draft`, …).
- `guard.py`: `main()` reads the hook's stdin JSON, then `_deny_reason()` / `_bash_deny_reason()`
  call `policy.py`. A deny exits with code 2.
- It finds the current run through the `.implement-feature/.active-run` pointer, because a hook
  doesn't inherit the conductor's env.
- Bash checks are **best-effort** (string matching, not a sandbox). The analyzer's auditor covers
  the gap.

**`analyzer/`: measurement** ([`architecture.md`](architecture.md) §6, [`analyzer/README.md`](../sdlc-lite-plugin/analyzer/README.md)).
- Entry: `analyze_run.py` → `main()` / `build_report()`.
- `runlog.py`: the guard's audit log → intent-level verdicts (blocked attempts). Load-bearing.
- `auditor.py`: the authoritative isolation leg. It fingerprints protected files and scans
  subagent tool *output* for leaks. A hit → `THIS RUN IS UNTRUSTED`.
- `transcript.py`: parses the session transcript. Best-effort, and it fails loudly as *absent* or
  *drifted*.
- `receipt.py`: the headline. One row per agent, pinned vs actual model/effort. Model mismatch =
  FAIL, effort mismatch = WARN.
- `report.py`: renders Markdown.

**`agentdefs.py`**: `load_pins()` / `pin_for()`. One reader of the pins, so the dispatch plan and the
receipt can't disagree.

---

## 5. Platform facts that shaped the design

All of these were verified in real container runs. Don't trust the docs over them. Re-verify if you
change the related code.

- **Slash command ≠ Skill tool call.** Typing `/implement-feature` makes no tool call. A
  model-initiated start does, so the guard denies it (explicit entry only, [ADR-14](adr/ADR-14-explicit-entry.md)).
- **`commands/<x>.md` shadows `skills/<x>/`.** `SKILL.md` silently never loads
  ([finding](findings/2026-09-23-skill-suppression-findings.md), [ADR-14](adr/ADR-14-explicit-entry.md)).
- **Tool lists don't confine reads.** A critic with `Bash` can still write via `cat >`. Hence the
  guard ([ADR-1](adr/ADR-01-isolation-plugin-hook.md)).
- **Project-settings hooks didn't fire headless. Plugin hooks do,** for the conductor and every
  subagent ([ADR-1](adr/ADR-01-isolation-plugin-hook.md)).
- **Inline `model` accepts aliases only,** so gates are dispatched bare. **Effort is
  frontmatter-only** and can only be audited, never enforced ([ADR-12](adr/ADR-12-model-effort-integrity.md),
  [finding](findings/model-pinning-findings.md)).
- **Plugin agents are namespaced:** `sdlc-lite:test-writer`. The bare name won't resolve.
- **The transcript format is internal and unstable,** yet it's the only ground truth for model and
  effort ([finding](findings/audit-observability-findings.md)).
- **`claude plugin eval` sandboxes Bash, fail-closed,** so some cases run only in the container
  ([`eval-tutorial.md`](eval-tutorial.md)).

---

## 6. Testing

Full detail: [`verification-ladder.md`](verification-ladder.md).

| Tier | What | Where / how | Proves |
|---|---|---|---|
| **T1** | `claude plugin eval`, graded cases | `sdlc-lite-plugin/evals/` ([README](../sdlc-lite-plugin/evals/README.md)) | a cold agent reads the prose as intended |
| **T2** | pytest | `python3 -m pytest sdlc-lite-plugin -q` (host) | `guard` / `policy` / `agentdefs` / `analyzer` are correct |
| **T3** | dev-container dry run | [`DEVCONTAINER.md`](DEVCONTAINER.md), fixture `test-fixtures/python-starter/` | the plugin loads, the hook fires, gates are reached |

**Minimum tier by change** (the ladder, §3):

| Change | Minimum tier |
|---|---|
| Gate wording, templates | T1 |
| Gate behavior (routing, loops) | T1 + T3 |
| `agents/*.md` | T1 + T2 (+ T3 if the flow changes) |
| `guard.py` / `analyzer/` | T2 |
| `hooks.json` | T3 |
| Docs only | none |

**Also good to know:**
- **Scripted T3 slice:** `verify-entry-points.py` checks the 8-cell entry-point contract in the
  container.
- **Release gate:** `release-verify.sh` does a clean-room install from the release channel, a
  smoke test, and runs the eval suite.
- **Enforcement parity:** a prose rule the guard should enforce needs a `guard.py` denial **and**
  a T2 test.
- **Where the unit tests are:** `tests/` (policy, agentdefs, entry points), `hooks/tests/`
  (guard), `analyzer/tests/`.

---

## 7. Conventions

- **Never install the plugin into the Mac's `~/.claude`.** Run it in the dev container.
- **Never commit before human approval**, both in the product (Gate 9) and in this repo.
- **Changing anything** → [`developer-guide.md`](developer-guide.md) §2 (what to edit, what to
  sync, how to verify).
- **Two channels ([ADR-13](adr/ADR-13-one-plugin-two-channels.md)):** this repo's `.claude-plugin/marketplace.json` is **dev**. The
  **release** channel is the `Sdaas/claude-plugins` repo.
- **Issues:** type labels only. A milestone = a release, no milestone = backlog. Follow
  [`issue-template.md`](issue-template.md), or use `/issue`.
- **Docs:** [`findings/`](findings/) = settled evidence. [`proposals/`](proposals/) = unbuilt
  sketches, not current behavior.
- **Process:** plan → approve → phased execution. Big issues get a checked-in `<NN>-plan.md` on
  their branch.

---

## 8. Where to go next: pick a track

**Fixing docs**
1. [`../README.md`](../README.md): the user's view.
2. [`README.md`](README.md): the doc map.
3. No test tier needed. Run `./release-verify.sh --links-only`.

**Changing workflow behavior (prose)**
1. [`tutorial.md`](tutorial.md) §1–§7: the concepts, via the `toy-greet` example.
2. `SKILL.md`: read it in full once.
3. One `agents/*.md` in full (e.g. `test-writer.md`), then skim the rest.
4. `references/quality-standards.md`.
5. [`verification-ladder.md`](verification-ladder.md) → [`eval-tutorial.md`](eval-tutorial.md):
   how you'll prove the change.
6. [`adr/`](adr/README.md) before any structural change; [`developer-guide.md`](developer-guide.md) §2–§3
   for what to edit and the review checklist.

**Changing enforcement or measurement code**
1. `policy.py`: the module docstring, then `POLICY` and `decide()`.
2. `guard.py`: `main()`, then `_deny_reason()` / `_bash_deny_reason()`.
3. `agentdefs.py`, then `analyzer/README.md` → `analyze_run.py` → `runlog` → `auditor` →
   `transcript` → `receipt`.
4. [`architecture.md`](architecture.md) §5–§6, and [ADR-10](adr/ADR-10-secrets-path-components.md)/[ADR-11](adr/ADR-11-intent-and-effect.md)/[ADR-12](adr/ADR-12-model-effort-integrity.md).
5. The matching tests, then T2.
