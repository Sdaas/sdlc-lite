# The verification ladder — how much proof a change needs

---

## 1. The problem

**This product's source is prose.** The behavior of `sdlc-lite` lives in `SKILL.md`,
`agents/*.md`, `references/*` and `hooks.json`. The only real code is `guard.py` + `policy.py` (the
guard hook and its rules), `agentdefs.py` and `analyzer/` — a small surface in a product that is
otherwise Markdown.

That creates four problems a normal repo does not have.

**1. There is no compiler and no failing test.** Editing a paragraph produces no signal at all.
Nothing goes red, nothing refuses to build, and nothing tells you the gate you just reworded is now
ambiguous. A typo and a logic inversion look identical to the toolchain.

**2. The one real signal is far too expensive to use.** What actually proves the product works is a
dev-container dry run: a full, interactive Claude session against a fixture repo, minutes to hours,
non-deterministic, with a human sitting at the approval gates. You cannot run that after every
paragraph, so in practice it gets run rarely — or "verification" quietly degrades into re-reading
your own diff.

**3. Re-reading your own diff does not work.** The bias in a Python repo is that the implementer
weakens the tests. The bias here is the **author's curse of knowledge**: your prose reads correctly
to you because you already know what you meant. The agent that executes it at runtime knows none of
that. Self-review is structurally blind in exactly the place that matters.

**4. Fixes do not accumulate safety.** A fixed Python bug leaves a `pytest` case behind forever. A
fixed prose bug leaves nothing — the next edit to that paragraph can silently undo it, and no one
finds out until a dry run months later behaves strangely. The repo gets no safer over time.

So: changes land with no verification, or with verification so expensive it is skipped, and nothing
that is fixed stays fixed. **This file is the answer to "how much proof does this change owe, and
how do I get it cheaply?"**

For *how to author and run* an eval case, see **[`eval-tutorial.md`](eval-tutorial.md)** — that file
teaches the tool, this one decides how much of it a given change needs.

---

## 2. The answer: three tiers

Three levels of proof, cheapest first. Together they are **the ladder**; a change declares which
rung it must reach.

| Tier | What it is | Cost | What it actually proves |
|---|---|---|---|
| **T1** | `claude plugin eval` — seeded cases run in a fresh isolated `claude -p` session with only this plugin loaded, 3 runs each, scored by graders | seconds–minutes | A cold agent reads the prose the way you intended |
| **T2** | `python3 -m pytest sdlc-lite-plugin -q` | seconds | The executable surface (`guard.py`, `analyzer/`) is correct |
| **T3** | A dev-container end-to-end dry run ([`DEVCONTAINER.md`](DEVCONTAINER.md)) | a full session | The plugin loads, the hook fires, the gate is reached |

### T1 — `claude plugin eval`

The rung that did not exist before, and the one that solves problems 1, 3 and 4 above. A case is a
prompt plus graders; the harness runs it several times in a throwaway sandbox and scores it. Free
(structural) graders — `regex`, `tool_used`, `tool_order`, `file_exists` — cost nothing beyond the
agent runs; `llm` and `baseline` graders call a judge model and are used sparingly.

Two properties make it fit this repo specifically:

- **It is a genuinely cold reader.** The case is phrased the way a user would type it, never naming
  the skill, and the sandbox carries none of your context — which is the only honest test of prose
  whose failure mode is "obvious to the author".
- **`context.history_file` replays a known-good transcript up to turn N−1 and evaluates turn N**, so
  a mid-workflow gate is testable without driving all 12 gates to reach it.

The suite lives in [`../sdlc-lite-plugin/evals/`](../sdlc-lite-plugin/evals/) and **ships with the
plugin** — for a workflow plugin selling rigor, a runnable suite is a feature, not test scaffolding.

### T2 — `pytest`

Ordinary test-first development applies here and nowhere else in this repo. `guard.py` and
`analyzer/` are real code with real unit tests; a change to either goes red-then-green like any
Python change. Runs on the host.

### T3 — the dev-container dry run

The only rung that proves a hook actually **fires**, a gate is actually **reached**, or the plugin
loads at all — because it is the only one that runs the real thing end to end.

One slice of T3 *is* scripted: **`verify-entry-points.py`** (#57) proves the entry points — the slash
command loads the body, and the model cannot start the workflow itself — on both load paths, with no
human in the loop. See [`DEVCONTAINER.md`](DEVCONTAINER.md#entry-point-check--verify-entry-pointspy).

**The rest of T3 cannot be automated, and that is a design fact, not a gap.** A full dry run *is*
another Claude session with a human at the approval gates; past the entry points there is nothing
for a script to assert. So a gate that requires T3 **STOPs and the human attests** — they ran it,
and here is what they saw. No skill, no
script and no agent may mark a T3 requirement satisfied on its own.

---

## 3. How much proof does my change need?

The tier is a **floor**, not a ceiling. Find the row that matches the change; when a change spans
rows, take the union.

| Change | Minimum tier |
|---|---|
| Gate wording, human-facing output, a `references/*` template | **T1** |
| Gate behavior: routing, loop bounds, a new or removed gate | **T1 + T3** |
| `agents/*.md` inbox, model/effort, or tool permission | **T1 + T2**, and **T3** if the flow changes |
| `guard.py` / `analyzer/` | **T2** (+ **T1** if the paired prose changed too) |
| `hooks.json` registration | **T3** — nothing else proves a hook fires |
| Docs only (`README.md`, `dev-docs/**`) | none — see below |

**Docs-only changes are not gated.** Gating a README edit is theater (the repo-local
`/feature` skill declines docs-only and shell-only changes outright). The one exception: a doc whose path the *shipped* `SKILL.md` prints
at runtime — changing that is a prose change to the product, not a doc change.

**Enforcement parity.** A new prose rule that the guard hook is meant to enforce needs its matching
`guard.py` denial *and* a T2 test for it. A rule that exists only in prose is a suggestion.

---

## 4. Budget

Two budgets, not one. The point is that the every-change loop stays cheap enough that nobody routes
around it.

**Every change (the default).** Free graders only, no baseline arm, filtered to what the diff
touches:

```bash
claude plugin eval sdlc-lite-plugin --ablation none --tag <area>
```

`--ablation none` skips the no-plugin comparison — you are asking "does it still do the right
thing", not "is the plugin worth its tokens". Run it this way once before trusting any delta.

**Milestone / pre-release (the full gate).** The whole suite, both arms, pinned models, a threshold,
run in the dev container and wired into `release-verify.sh` (§8):

```bash
claude plugin eval sdlc-lite-plugin \
  --ablation with-without --model <pinned> --judge-model <pinned> \
  --threshold <t> --json results.json --no-publish
```

Pin `--model` so a model rollout is not misread as a plugin regression, and drop `partial: true`
documents out of any trend you keep.

---

## 5. What T1 cannot prove

These limits are structural. Read them before authoring cases, not after.

- **The sandbox loads no `CLAUDE.md`, no project or user settings, no hooks of your own, no other
  plugins, no MCP servers and no memory.** The child runs with a fresh `HOME` and
  `CLAUDE_CONFIG_DIR` under `--setting-sources user`, with `CLAUDE.md` disabled entirely; only the
  plugin under test loads. **A bug that depends on project config is structurally unreproducible at
  T1 and stays T3-only** — for example the "read outside working directories" prompt, which comes
  from settings the sandbox never loads.
- **The Artifact tool is unavailable inside a run.** Grade what a skill *produces*, up to any
  publish step.
- **T1 runs in the dev container, not on the Mac host.** Any case granting `Bash` is refused on the
  host: the OS sandbox must exclude `~/.docker` (a credential store), Docker Desktop fills it with
  symlinks, and path-based exclusions cannot cover a link graph — so the harness fails closed.
  The host still runs read-only cases, which is handy while writing graders, but it is a
  convenience and not the harness. Full explanation: `eval-tutorial.md` § 1.
- **`claude plugin eval` needs claude ≥ 2.1.281** (GA; the container's pin). Older builds gate it
  off and reject the pinned `claude-opus-5-5`: `eval-tutorial.md` § 1.
- **Network is not blocked, and the plugin's own hooks run unconfined as you.** Evaluating a plugin
  is the same trust decision as `--plugin-dir`.

---

## 6. Why not just use `sdlc-lite` on itself?

The obvious question, since this repo ships a gated, test-first workflow for exactly this purpose.
It does not transfer, because its spine rests on three assumptions and §1 breaks all three.

| Assumption in `sdlc-lite` | Reality here |
|---|---|
| The artifact is executable, so tests can go red before code exists | The product is prose. "Red" is undefined for Markdown. |
| A cheap deterministic green signal exists (`pytest` / `ruff` / `mypy`, seconds) | The real signal is a dry run: minutes to hours, non-deterministic. |
| The bias worth isolating is "the implementer weakens the tests" | The bias is the author's curse of knowledge. |

Three of its gates therefore change shape rather than carrying over:

- **Test-first becomes expectation-first.** You cannot cold-read a `SKILL.md` section that does not
  exist yet, so "write the failing test" does not transfer literally. What transfers is the
  assertion coming first: **write the eval case and its expected answer before editing the prose.**
  Run it; it fails, or passes for the wrong reason. That is this repo's honest "red".
- **Isolation flips from withholding to simulating.** `sdlc-lite` curates inboxes to *withhold* —
  the test-writer never sees the internal design. Here the verifying agent must see **exactly what
  the real runtime agent will see, and nothing more.** Leaking your intent into the case — "check
  that the gate refuses X" — voids it: you have told it the answer.
- **"Green" becomes an approved budget.** T3 is expensive and non-deterministic, so done is not a
  threshold a machine reports. It is **a tier the human approved at plan time, whose evidence the
  human then judged sufficient.** The human is the oracle here in a way they never are in the
  Python flow.

**What transfers unchanged:** human approval gates, never-commit-before-approval, bounded loops,
curated handoffs, branch discipline, GitHub-as-SSOT, and review on a stronger model than
implementation.
**What does not survive the move:** mutation testing, coverage percentages, `ruff` / `mypy` outside
`guard.py` and `analyzer/`, red-before-green on prose, and dated model pins.

---

## 7. The working contract

Declare the tier **at plan time**, before implementing — it is part of what the human approves.
Write the eval case **before** the prose it verifies. Run the declared tier and present the
evidence, not a claim. If the tier includes T3, stop and let the human attest. If the change fixed a
bug, deposit the case that reproduces it, so the next edit cannot silently undo the fix.

---

## 8. The release gate — `release-verify.sh`

`release-verify.sh` (repo root, run on the Mac) automates the customer path end to end and hands off
only the irreducibly-human step. [`RELEASING.md`](RELEASING.md) §4 says *when* to run it; this
section says what it checks. It starts with a relative-link check over every `*.md`
(`--links-only` runs just that, on the host), then:

1. **Clean-room install.** A fresh isolated `CLAUDE_CONFIG_DIR` in the container (no dev marketplace
   — see [`DEVCONTAINER.md`](DEVCONTAINER.md) → Two Claude profiles) installs `sdlc-lite@sdaas` from
   the umbrella on GitHub and asserts a genuine `git-subdir` install: cached version equals
   `plugin.json`, commands/agents/hooks present.
2. **Gate 0/1 smoke (headless, two calls)** on a fresh fixture: `claude -p "/implement-feature …"`
   must print Gate 0 "Preflight passed" and write `.active-run`; `claude --continue -p "APPROVED …"`
   must start the Gate 1 interview. A body canary reads the session transcript and fails if the
   skill body was shadowed or never injected (ADR-14).
3. **`/plugin update` proof** (git/fs only, no model calls). Rebuilds the umbrella catalog as of the
   previous tag in a throwaway clone, installs that release, advances the catalog, and runs
   `marketplace update` + `plugin update` — the installed version must move `<prev>` → `<current>`.
   Skipped on the first release.
4. **Milestone eval suite (T1, §4).** `claude plugin eval` over `sdlc-lite-plugin/evals/`, both arms,
   pinned `--model`, `--threshold 0.8`. It grades the plugin **source at the checkout** (the tag, at
   release time), not the installed copy.

The whole run is **18/18** when a previous tag exists. The full gated run past Gate 1 stays a
**human** step (T3), which the script prints as a handoff.

Auth comes from the repo-root `.env` (see [`DEVCONTAINER.md`](DEVCONTAINER.md) → Authentication).
Flags: `--keep` retains the config/fixture, `--no-smoke` does install-verify only, `--no-evals`
skips the ~15-minute eval suite, `--evals-only` runs just that suite.

---

*Maintenance note: this file is where T1, T2 and T3 are defined. Everything else that needs them —
`.claude/sdlc/gates.md`, a skill, an issue, `release-verify.sh` — should link here rather than
restate them, because two definitions drift.*
