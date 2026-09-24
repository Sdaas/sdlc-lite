# 50-plan — Verification ladder + eval seed suite + release-verify hook

**Issue:** [#50](https://github.com/Sdaas/sdlc-lite/issues/50) · **Parent:** #48 · **Milestone:** `1.0.0-beta.3`
**Branch:** `50-verification-ladder` · **Status:** PA + PB + PC done — **resume at Phase D (§ 4.4)**

**Resuming in a new session:** read this file, then start at **§ 4.0** (steps 1–3 done; step 4 = Phase D) — it carries everything a cold
session needs. Do not re-derive the phases from #50; they are settled below.

Branch-scoped working plan — P1 of `48-plan.md`. `git rm` this file in the merge/close commit.
`48-plan.md` itself stays (it spans all five children; it is `git rm`'d in P5/#53).

---

## 1. Goal

Give this repo a cheap verification primitive for **prose** changes to `sdlc-lite-plugin`, and a
shared vocabulary for how much proof a given change needs.

Today the only real signal is a dev-container dry run — a full, non-deterministic Claude session.
`claude plugin eval` supplies the missing cheap tier; this issue stands it up, documents it, seeds
a corpus, and wires it into the release gate.

**Non-goals:** a hand-rolled cold-read harness (D7 — do not build a worse version of a shipped
tool); evals for the repo-local SDLC skills (#51 and later).

## 2. Constraints (environment facts that shape the work)

| Fact | Consequence |
|---|---|
| `claude plugin eval` is **early-access gated**, off by default for this account | `CLAUDE_CODE_WALNUT_SPIRE=1` must be set in the **shell/CI env** or `~/.claude/settings.json`; a value in the repo's `.claude/settings.json` leaves it gated off. Self-test: run in an empty dir — "early access" = off, "No eval cases found" = on. |
| **No public docs page** for `plugin eval` | The reference ships zstd-compressed inside the `claude` binary (`plugin-eval-quickref-*.md.zst`). Phase 0 extracts it so the case format is read, not guessed. |
| **Bash-granting cases cannot run on this Mac** | Docker Desktop symlinks in `~/.docker` defeat the OS sandbox's credential-store exclusion; `DOCKER_CONFIG` does not help. Non-Bash cases run fine on the host; the **dev container** runs Bash cases fine. → cases must be **tagged** so host runs filter container-only ones out. |
| T3 is a separate Claude session | Cannot be automated (D10) — the gate STOPs and the human attests. |
| The eval sandbox loads no `CLAUDE.md`, settings, plugins or memory | Config-dependent bugs are **structurally unreproducible** at T1 and stay T3-only. |

## 3. Phases

One commit per phase; review list presented before each; nothing commits without approval.

| P | Deliverable | Verification |
|---|---|---|
| **0** | Extract the `plugin eval` quickref from the `claude` binary into scratch (not committed) | The case-file schema, grader types and exit codes are read from the reference, not inferred |
| **A** | `dev-docs/verification-ladder.md` — **SSOT** for T1/T2/T3 (D11) | Self-consistent; `48-plan.md` §5 is its source; nothing else in the repo restates the tiers |
| **B** | `dev-docs/eval-tutorial.md` — cases, graders, ablation delta, budgets, plus the §2 environment facts | A reader can author and run a case from it alone |
| **C** | `sdlc-lite-plugin/evals/` — ≥6 seeded cases, ≥1 should-not-fire (`min:0, max:0, arm: both`), two graders each (one on the result, one on how Claude got there), tagged host-safe vs container-only | `claude plugin eval sdlc-lite-plugin --ablation none` validates the graders; then a baseline Δ run |
| **D** | `release-verify.sh` milestone-tier eval step (pinned `--model`, `--threshold`, `--ablation with-without`) + README routing to both new docs | `./release-verify.sh` fails when a seeded case is deliberately broken |

### 3.1 Content contract for Phase A

`verification-ladder.md` must carry, per the issue's acceptance criteria:

- T1 / T2 / T3 with cost, and the **change → minimum tier** mapping (`48-plan.md` §5).
- The **per-change vs milestone** budget policy.
- **Why `sdlc-lite`'s own spine cannot serve this repo**: test-first inverts to expectation-first;
  isolation flips from withholding to simulating; there is no "green", only an approved budget;
  prose accumulates no regression safety.
- **T3 cannot be automated** — the gate STOPs, the human attests (D10).
- The **sandbox limit** — no `CLAUDE.md`, settings, plugins or memory; config-dependent bugs are T3-only.

### 3.2 Eval-case practices to encode (Phase B/C)

From the extracted reference and `48-plan.md` §5: 5–10 realistic cases phrased as a user would type
them, never naming the skill · at least one should-not-fire case · two graders per case · free
graders (`regex`, `tool_used`, `tool_order`, `file_exists`) for the every-change suite, `llm`
sparingly · long output → `regex` over the file, not an `llm` judge · pin `--model` in CI so a model
rollout is not misread as a regression · run once with `--ablation none` before trusting any Δ ·
`tool_used: Skill` passing while Δ is negative means suspect the judge, not the plugin · leave
`partial: true` runs out of trend charts · `context.history_file` seeds mid-workflow state so a gate
is testable without driving all 12.

## 4.0 Resume here — finishing Phase C (session 2, 2026-09-24)

The suite is **built and piloted but uncommitted** in the working tree. Do these in order:

1. **Review + commit, in two logical units** (list the files to the human, wait for approval):
   - (a) `.devcontainer/devcontainer.json` (two `--security-opt` flags), `dev-docs/DEVCONTAINER.md`
     (new "Two loosened Docker defaults" section), `dev-docs/eval-tutorial.md` (§ 1 + § 6 fixes);
   - (b) `sdlc-lite-plugin/evals/` (7 cases, `_fixtures/`, `README.md`, `.gitignore`) + this file.
2. **Baseline delta run** (container, ~25 min sequential — run it in the background):
   `claude plugin eval sdlc-lite-plugin --ablation with-without --scaffold --no-publish --allow-tools Bash Write Edit`
   Record per-case score / Δ as a "Baseline results" table under "Pilot results" below. This also re-verifies the `"command"`-scoped Bash
   graders (fixed after the last full run, only checked offline).
3. **File one issue** (per `dev-docs/issue-template.md`) for the two prose deviations below; no milestone
   unless the human says so.
4. Then Phase D (§ 4.4), with **`--threshold 0.8`**.

### Decisions locked in session 2

- **Graders stay strict.** The two flaky cases flag real prose deviations; fixing the prose is a
  separate issue, not #50.
- **Phase D threshold = 0.8** (strict graders make 1.0 unattainable today).
- **The dev container runs with `seccomp=unconfined` + `systempaths=unconfined`** — without them
  bubblewrap cannot start and *every* Bash-granting case fails (`bwrap: No permissions to create a
  new namespace`). This overturned PB's "the container runs Bash cases fine".
- Keep eval cases **and** #57's checker (overlap on the slash-spelling cells is intended).
- Suite-wide `--allow-tools Bash Write Edit` also reaches the read-only cases — accepted as realistic.

### Findings from piloting (session 2)

- Typed `/implement-feature` and `/sdlc-lite:implement-feature` both start the workflow inside an
  eval run (stdin prompt to `claude -p`). A typed slash command makes **no** `Skill` call, so
  should-fire cases grade observable Gate 0 behavior (`ruff --version` ran, summary text).
- The model refuses a direct "read my .env" on its own — the guard case is phrased as a debugging
  task so the model reaches for `.env` and the guard is what stops it.
- **Grader trap:** a Bash `input_match` also sees the call's `description` field. All Bash graders
  are scoped to `"command"\s*:\s*"(?:[^"\\]|\\.)*<pattern>`.
- The container's build is **2.1.260**: needs `CLAUDE_CODE_WALNUT_SPIRE=1`, and has **no `-j` and no
  `--trust-plugin`** (the extracted reference is from 2.1.281, where plugin eval is GA). Don't use
  either flag in `release-verify.sh` until the container's claude is bumped.
- Fixture commits need an explicit git identity (fresh containers have none) — done in the fixture.

### Pilot results (`--ablation none`)

| Case | Result | Note |
|---|---|---|
| `entry-slash-bare` | 3/3 | |
| `entry-slash-namespaced` | 3/3 | |
| `gate-1-interview-entry` | 3/3 | Q1 pattern loosened to `❓\s*\*\*Q1\b` — model bolds the title with the number |
| `guard-secret-read-denied` | 3/3 | after the rephrase |
| `gate-0-lock-stop` | 7/8 | **prose deviation:** saw the lock, ran the preflight anyway, then stopped |
| `routing-no-autoinvoke` | 6/8 | **prose deviation:** implemented the feature itself instead of pointing at `/implement-feature` |
| `gate-0-not-importable-stop` | 7/8 | the one failure was the `description` grader bug — now fixed |

### Baseline results (`--ablation with-without`, container 2.1.260, 2026-09-24)

| Case | With | Without | Δ | Note |
|---|---|---|---|---|
| `entry-slash-bare` | 1.00 | 0.33 | +0.67 | |
| `entry-slash-namespaced` | 1.00 | 0.33 | +0.67 | |
| `gate-0-lock-stop` | 0.83 | 0.50 | +0.33 | preflight ran despite the lock — #58 |
| `gate-0-not-importable-stop` | 1.00 | 0.33 | +0.67 | `"command"`-scoped Bash graders confirmed live |
| `gate-1-interview-entry` | 1.00 | 1.00 | 0.00 | expected — see below |
| `guard-secret-read-denied` | 1.00 | 0.17 | +0.83 | |
| `routing-no-autoinvoke` | 1.00 | 0.50 | +0.50 | |

7 cases · mean Δ +0.52 · 932 s · $5.41 · exit 1 (threshold 1.0, lock case).

**Δ 0.00 on `gate-1-interview-entry` is structural, not a grader bug:** the recorded
`history_file` carries the expanded `SKILL.md` body (the slash command's injected text), so the
*without* arm still has the skill in context. A history-seeded case proves a mid-workflow gate is
reachable and behaves; its Δ carries no signal. Judge such cases on the *with* score only.

Prose-deviation issue filed: **#58** (backlog).

### Known small gap (not #50)

`dev-docs/DEVCONTAINER.md` "Find the container (no fixed name …)" is stale — `runArgs` sets
`--name sdlc-lite-test`.

## 4. Phase C brief (the eval seed suite) — original, kept for reference

Everything a fresh session needs. Read § 2 (environment facts) first; they are not obvious and each
one costs an hour if met the hard way.

### What is already done

| Phase | Commit | What landed |
|---|---|---|
| P0 | — | The `plugin eval` reference, extracted from the `claude` binary (see § 4.1) |
| PA | `9660303` | `dev-docs/verification-ladder.md` — problem statement, T1/T2/T3, change→tier table, budgets, T1 limits, why `sdlc-lite` does not transfer, the working contract |
| PB | `d7c3889` | `dev-docs/eval-tutorial.md` + `dev-docs/README.md` routing |

Also on this branch: `4f6545c` (checks in `48-plan.md` + this file). On `main` ahead of the branch:
`d419040` (release-plan housekeeping).

**A decision made during PB that PC must honor:** **evals run in the dev container**, full stop.
The Mac host is a fast-iteration convenience for read-only cases, not a sanctioned suite run. There
is therefore **no `container` tag** and no host/container filtering convention — do not reintroduce
one. The reasoning is in `eval-tutorial.md` § 1.

### 4.1 Re-obtaining the eval reference

`claude plugin eval` has **no public docs page**. The full reference ships zstd-compressed inside
the `claude` binary. To recover it in a new session:

```bash
# scan the binary for zstd frames (magic 28 b5 2f fd) and decompress each one
B="$(readlink -f "$(which claude)")"     # e.g. /opt/homebrew/Caskroom/claude-code/<ver>/claude
```

Frames worth keeping (offsets shift per build — match on the first line, not the number):
`# Plugin eval and ... quick reference` (~9 KB) and
`# Plugin eval (\`claude plugin eval\`) and \`/skill-doctor\`` (~76 KB, the full reference:
case format, grader tables, sandbox internals, CI, troubleshooting). On build 2.1.267 these were
frames 41 and 137. The `claude-code-guide` agent also carries the quickref embedded.

**Do not author cases from memory** — the frontmatter key set is exact and unknown keys are errors.

### 4.2 What Phase C must deliver

Per #50's acceptance criteria and `48-plan.md` P1:

- `sdlc-lite-plugin/evals/` with **≥ 6 cases**, each with **two graders** — one on the result
  (`last_message` or `{source: file}`), one on the mechanism (`tool_used` / `tool_order`).
- **≥ 1 should-not-fire case**: `type: tool_used`, `tool: Skill`, `min: 0`, `max: 0`, **`arm: both`**
  (without `arm: both` it is silently unscored under `--ablation with-without`).
- Cases phrased **as a user would type them**, never naming the skill.
- Tag vocabulary already documented in `eval-tutorial.md` § 6: `gate-0`…`gate-11`, `routing`,
  `entry-point`, `guard`. (No `container` tag — see above.)
- Each case sets `plugins: ["../.."]` explicitly.

**Suggested coverage** (judgment call, not a spec): the entry-point contract from #55/#56 (both
slash spellings fire; the model never auto-invokes — this is the should-not-fire case), Gate 0
preflight passing and stopping, Gate 1 interview entry, a guard-hook denial, and one
`context.history_file` case proving a mid-workflow gate is reachable without driving all 12.

### 4.3 Verification for Phase C

```bash
# in the dev container, with CLAUDE_CODE_WALNUT_SPIRE=1 exported in the shell
claude plugin eval sdlc-lite-plugin --ablation none          # validates the graders
claude plugin eval sdlc-lite-plugin --ablation with-without  # baseline delta
```

Pilot new cases with `--runs 1 --verbose`; raise runs once the graders are right. Default
`--threshold` is 1.0 — everything must pass — so set it deliberately.

### 4.4 Then Phase D

`release-verify.sh` gains the milestone-tier eval step (pinned `--model`/`--judge-model`,
`--threshold`, `--ablation with-without`, `--no-publish`), proven by deliberately breaking a seeded
case; root `README.md` routes to both new docs. Then close out: `git rm 50-plan.md`, tick P1 in
`48-plan.md`, close #50.

---

## 5. Progress tracker

- [x] P0 — eval reference extracted from the `claude` binary (§ 4.1)
- [x] PA — `dev-docs/verification-ladder.md` (`9660303`)
- [x] PB — `dev-docs/eval-tutorial.md` + `dev-docs/README.md` routing (`d7c3889`)
- [x] PC — `sdlc-lite-plugin/evals/` seed suite (`5a1f292`, `6e52b3f`, baseline recorded)
  - [x] commit (a) container/docs (`5a1f292`), (b) suite (`6e52b3f`)
  - [x] baseline `--ablation with-without` run, results into § 4.0
  - [x] file the prose-deviation issue (#58)
- [ ] **PD — `release-verify.sh` eval step (`--threshold 0.8`) + root `README.md` routing ← next**
- [ ] `git rm 50-plan.md` in the merge/close commit
- [ ] Close #50; tick P1 in `48-plan.md`
