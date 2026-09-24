# 50-plan — Verification ladder + eval seed suite + release-verify hook

**Issue:** [#50](https://github.com/Sdaas/sdlc-lite/issues/50) · **Parent:** #48 · **Milestone:** `1.0.0-beta.3`
**Branch:** `50-verification-ladder` · **Status:** in progress

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

## 4. Progress tracker

- [x] P0 — quickref extracted (`plugin-eval-quickref.md` + the full `plugin-eval.md`, frames 41 and 137 of the 2.1.267 binary)
- [ ] PA — `dev-docs/verification-ladder.md`
- [ ] PB — `dev-docs/eval-tutorial.md`
- [ ] PC — `sdlc-lite-plugin/evals/` seed suite
- [ ] PD — `release-verify.sh` eval step + README routing
- [ ] `git rm 50-plan.md` in the merge/close commit
- [ ] Close #50; tick P1 in `48-plan.md`
