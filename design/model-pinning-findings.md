# Finding: the dated reviewer pin (`claude-opus-4-8`) IS honored in the dev container

**Date:** 2026-09-11 · **Updated:** 2026-09-14 · **Branch:** `refactor/shippable-plugin` (orig),
`v1-trust-claim` (close-out) · **Status:** ✅ RESOLVED as a *platform* fact (the frontmatter pin
**is** honored) — but a later change (#22's "Witt" hook) **regressed** it for dated pins. See the
**§7 close-out** for the settled conclusion; fix tracked in **#36**. (Earlier "not honored" claim in
§5 was a transcript misattribution, unrelated to the #22 regression.)

Feeds the Developer Guide's **model-pinning ADR** (Phase 3), alongside
[`isolation-experiments.md`](./isolation-experiments.md).

---

## 1. Conclusion (settled)

The two reviewer gates pin the **explicit dated ID** `claude-opus-4-8` in their agent defs
(commit `e093182`):

- `implement-feature-plugin/agents/test-reviewer.md` → `model: claude-opus-4-8`
- `implement-feature-plugin/agents/code-reviewer.md` → `model: claude-opus-4-8`

**The pin is honored.** In every session that ran *after* the pin landed, both reviewer gates'
subagent transcripts report `message.model = claude-opus-4-8` — including the committed Phase 4
async-fetcher run. The `sonnet`-alias gates resolve to `claude-sonnet-5` in every session. No
fallback, no coercion, no override env var. The Gate 0 SKILL.md note ("the two reviewer rows
always read `claude-opus-4-8`, never the `opus` alias", commit `133025c`) is therefore
**accurate as written** and needs no correction.

## 2. Ground-truth evidence (raw `message.model`, not the conductor's self-report)

Ground truth is each subagent transcript's `message.model` field
(`~/.claude/projects/<slug>/<session>/subagents/agent-*.jsonl`, typed by the sibling
`.meta.json` `agentType`) — **not** the conductor's hand-written `run-log.jsonl` `model` field.
The container's project slug `-home-vscode-test-implement-feature` accumulated transcripts from
**four** `/implement-feature` runs (the dir was reused across Phase 2 and Phase 4). The pin
landed **2026-09-11 03:44 UTC** (commit `e093182`). Reading every reviewer transcript directly:

| Session (start UTC) | Feature / phase | vs pin | Reviewer `message.model` | Sonnet gates |
|---|---|---|---|---|
| `c50fd39c` — Sep-10 03:01 | `parse_duration` (Phase 2) | **before** | `claude-opus-5` | `claude-sonnet-5` |
| `fba1dac5` — Sep-10 07:34 | `parse_duration` (Phase 2) | **before** | `claude-opus-5` | `claude-sonnet-5` |
| `c8d1ff00` — Sep-11 04:42 | partial (aborted) | **after** | `claude-opus-4-8` | `claude-sonnet-5` |
| **`251d3474` — Sep-11 08:07** | **`CachedFetcher` (Phase 4, commit `7047829`)** | **after** | **`claude-opus-4-8`** | `claude-sonnet-5` |

Every row is internally consistent: **before** the pin the reviewers used the floating `opus`
alias, which correctly resolved to the latest Opus (`claude-opus-5`); **after** the pin they ran
the dated `claude-opus-4-8`. There is no session in which the pin was in effect and *not*
honored.

Method (reproducible in-container):
```bash
BASE=~/.claude/projects/-home-vscode-test-implement-feature
for s in <session-uuids>; do
  for meta in "$BASE/$s"/subagents/*.meta.json; do
    grep -o '"agentType":"[^"]*"' "$meta"
    grep -o '"model":"[^"]*"' "${meta%.meta.json}.jsonl" | sort -u
  done
done
```

## 3. Model resolution (why the pin sticks)

Per the official [model-config docs](https://code.claude.com/docs/en/model-config), the subagent
model is resolved highest-wins:

1. Per-invocation `model` passed to the Agent tool
2. **Subagent frontmatter `model:`** ← our `claude-opus-4-8` lives here (rank 2)
3. `CLAUDE_CODE_SUBAGENT_MODEL` env var
4. Session model
5. Account default

The frontmatter field **accepts a full dated ID** (`claude-opus-4-8` is the docs' own example),
so the syntax is correct, and — confirmed below — nothing at ranks 1/3 overrides it in the
container.

## 4. Deferred checks — run, all clear

- [x] `env | grep -Ei 'CLAUDE_CODE_SUBAGENT_MODEL|ANTHROPIC_.*MODEL|CLAUDE_.*MODEL'` → **no
  model-override env vars set.** So the frontmatter pin (rank 2) is authoritative; the
  [issue #10993](https://github.com/anthropics/claude-code/issues/10993)
  `CLAUDE_CODE_SUBAGENT_MODEL`-always-wins trap does **not** apply here (the var is unset).
- [x] Is `claude-opus-4-8` actually offered to the container's account? **Yes — it ran**, in
  both post-pin sessions, so it is available and not excluded by `availableModels`.
- [x] Fallback substitution (docs: an unavailable model is swapped rather than failing) is
  **not** occurring for the reviewers — they land on the exact dated ID, not a substitute.

## 5. Why the earlier draft said the opposite (root cause of the confusion)

The first draft of this file (commit `69ace10`) concluded the pin was *not* honored. That was a
**misattribution**, not a real fallback failure. It identified the Phase 4 run as session
`fba1dac5` and reported its reviewers as `claude-opus-5`. But `fba1dac5` is a **Sep-10
`parse_duration` (Phase 2) run that predates the pin by a full day** — at that time the reviewers
were still the floating `opus` alias, so `claude-opus-5` was exactly correct. The **actual**
Phase 4 async-fetcher run (workdir `00-async-cached-json-fetcher-202609110808`, commit
`7047829`) is session **`251d3474`** (55 `CachedFetcher` refs, 100 workdir refs, 3 commit refs),
whose reviewers ran `claude-opus-4-8`. Once the run↔session mapping is correct, both the earlier
"opus-5" observation and the later "opus-4-8" observation are simultaneously true — of different
runs — and the pin comes out honored.

**Lesson (worth an ADR note):** always tie a transcript session to its run by grepping the
feature identity / workdir slug / commit SHA in the *main* transcript before reading its
subagents — a reused project dir mixes sessions from multiple runs, and mtime alone is not proof.

## 6. Consequences (as of 2026-09-11 — later partially reversed, see §7)

- Commit `e093182`'s reproducibility goal (a dated reviewer version) **is achieved** in this
  environment **when the subagent is dispatched bare** (no inline model). ⚠️ Later regressed by the
  #22 hook — see §7.
- The Gate 0 SKILL.md note from commit `133025c` was **correct** at the time.
- No product change was required *then*. Carry the §2 evidence table and the §5 lesson into the
  model-pinning ADR (ADR-12).

## 7. Close-out (2026-09-14): the #22 "Witt" hook regressed this; its premise was false

This capture concluded — **correctly** — that a **frontmatter** model pin is honored on this
platform with no inline override (rank-2 in the resolution order, §3), proven across four real
sessions (§2). A clean **re-probe on 2026-09-14** (Claude Code 2.1.266) reconfirms it: an agent-def
pinning `model: claude-opus-4-8`, dispatched **by `subagent_type` alone with no inline `model`**, ran
on exactly `claude-opus-4-8` while its parent session ran `claude-sonnet-5` — the pin applied,
distinct from the session default.

**But issue #22 (closed 2026-09-14) shipped a guard hook built on the *opposite* premise** — that a
"frontmatter pin is silently droppable if the dispatch omits a model" (the Thomas-Witt technique) —
and it **denies any dispatch of a pinned subagent that names no model**, forcing the conductor to
name the model inline. That premise is **false here** (this capture + the re-probe both show a
bare-dispatch pin is honored), and the hook is **actively counterproductive for the dated reviewer
pins**:

- The Agent/Task tool's **inline `model` is enum-restricted to family aliases** `{sonnet, opus,
  haiku, fable}` — it cannot carry a dated id.
- So a hook-forced re-dispatch of a `claude-opus-4-8`-pinned reviewer can only name the `opus`
  **alias** — a **rank-1** per-invocation argument that **overrides** the rank-2 frontmatter pin →
  the reviewer runs the *floating latest* Opus (`claude-opus-5`), not the pinned `claude-opus-4-8`.
- Net: the deny-if-unnamed hook **destroys the exact-version reproducibility (ADR-2) the dated
  reviewer pins exist to guarantee** — it re-creates the very "wrong model" failure it was meant to
  prevent, but only for dated pins. For **alias** pins it is harmless (the conductor names the
  same-family alias, which matches) and merely redundant.

Observed live in the **#31b-i acceptance run (2026-09-14)**: the conductor hit "Invalid tool
parameters" trying to honor the dated pin inline, fell back to `opus`, and the receipt flagged
`test-reviewer: ❌ claude-opus-4-8 → claude-opus-5`.

### What the plugin *can* and *cannot* guarantee about model/effort — the honest statement

| Knob | Guarantee | Mechanism |
|---|---|---|
| **Family model** (`sonnet` / `opus` / `haiku`) | ✅ Can pin **and** verify | Frontmatter pin honored; the conductor may also name the same-family alias inline; the receipt confirms actual == family. |
| **Exact dated model** (`claude-opus-4-8`) | ✅ Achievable via frontmatter (dispatch **bare**) — restored by **#36** | Rank-2 frontmatter is honored when no inline model is named; #36 removed the deny-if-unnamed hook that had forced an overriding alias-only inline name. |
| **Effort** (`low` / `medium` / `high`) | ❌ Cannot enforce; **audit-only** | Frontmatter-only, no inline lever on this platform; the receipt WARNs on deviation but nothing prevents it. |

In **all** cases the post-run receipt reports the **actual** resolved model/effort from the
transcript — so a broken pin is never hidden; it surfaces as a ❌/⚠️. **Observability holds even where
prevention does not.**

### Fix (#36, done 2026-09-14 — supersedes #22's model-enforcement leg)

The correction was the **inverse** of deny-if-unnamed: dispatch a pinned subagent **bare** (no inline
model) and let the honored frontmatter pin govern. Shipped in #36 — the guard's `_dispatch_deny_reason`
was removed (Task/Agent dispatches are audited but never model-enforced), and the conductor's SKILL.md
instruction now says to dispatch bare. The receipt remains the authoritative model/effort verifier.

## Sources

- [Model configuration — Claude Code Docs](https://code.claude.com/docs/en/model-config)
- [Issue #10993 — subagent model selection & `CLAUDE_CODE_SUBAGENT_MODEL`](https://github.com/anthropics/claude-code/issues/10993)
- [Subagent Frontmatter — Developers Digest](https://www.developersdigest.tech/guides/subagent-frontmatter)
- [Subagent model pinning field report — Thomas Witt](https://www.thomas-witt.com/blog/blog-subagent-model-pin/)
</content>
</invoke>
