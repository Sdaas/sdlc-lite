# Finding: the dated reviewer pin (`claude-opus-4-8`) IS honored, dispatched bare

**Date:** 2026-09-11 · **Updated:** 2026-09-14 · **Status:** ✅ RESOLVED

Feeds the Developer Guide's model-pinning ADR.

## Conclusion

The two reviewer gates pin the explicit dated ID `claude-opus-4-8` in their agent-def frontmatter
(`agents/test-reviewer.md`, `agents/code-reviewer.md`). **The pin is honored** when the subagent
is dispatched **bare** (no inline `model` argument on the Agent/Task call) — frontmatter is rank-2
in Claude Code's model resolution order, below only an explicit per-invocation `model`. No
fallback, no coercion, no override env var observed.

> ⚠️ **Caveat — do not re-add a "dispatch with inline model" step.** Issue #22 once added a guard
> hook that denied any bare dispatch of a pinned subagent, forcing the conductor to name a model
> inline. The Agent tool's inline `model` argument is enum-restricted to family aliases
> (`sonnet`/`opus`/`haiku`/`fable`) — it cannot carry a dated ID. So a forced inline dispatch can
> only name `opus`, which as a **rank-1** argument *overrides* the rank-2 frontmatter pin and
> silently runs the floating latest Opus instead of the pinned dated version — destroying the exact
> reproducibility the pin exists for. Fixed in #36 by removing that hook; subagents are dispatched
> bare and the frontmatter pin governs. If this needs to change, re-read #36 first.

**What the plugin can and cannot guarantee:**

| Knob | Guarantee | Mechanism |
|---|---|---|
| Family model (`sonnet`/`opus`/`haiku`) | ✅ Pin + verify | Frontmatter honored; conductor may also name the same-family alias inline. |
| Exact dated model (`claude-opus-4-8`) | ✅ Pin + verify, **bare dispatch only** | Rank-2 frontmatter; see caveat above. |
| Effort (`low`/`medium`/`high`) | ❌ Cannot enforce, audit-only | No inline lever on this platform; the receipt WARNs on deviation. |

In all cases the post-run receipt reports the actual resolved model/effort from the transcript, so
a broken pin surfaces as ❌/⚠️ rather than being hidden.

## Evidence

Ground truth is each subagent transcript's `message.model` field, not the conductor's self-report.
Four sessions read directly, spanning the pin landing on 2026-09-11 03:44 UTC:

| Session (start UTC) | vs pin | Reviewer `message.model` | Sonnet gates |
|---|---|---|---|
| `c50fd39c` — Sep-10 03:01 | before | `claude-opus-5` (floating alias) | `claude-sonnet-5` |
| `fba1dac5` — Sep-10 07:34 | before | `claude-opus-5` (floating alias) | `claude-sonnet-5` |
| `c8d1ff00` — Sep-11 04:42 | after | `claude-opus-4-8` | `claude-sonnet-5` |
| `251d3474` — Sep-11 08:07 | after | `claude-opus-4-8` | `claude-sonnet-5` |

Confirmed no model-override env vars set (`CLAUDE_CODE_SUBAGENT_MODEL` etc.), and `claude-opus-4-8`
is available to the account (it ran, not substituted). A clean re-probe on 2026-09-14 (Claude Code
2.1.266) reconfirmed bare dispatch honors the frontmatter pin independent of the parent session's
own model.

The #22 regression was caught live in the #31b-i acceptance run (2026-09-14): with the deny-if-
unnamed hook in place, the conductor hit "Invalid tool parameters" trying to pass the dated ID
inline, fell back to the `opus` alias, and the receipt flagged
`test-reviewer: ❌ claude-opus-4-8 → claude-opus-5` — exactly the failure mode the caveat above
describes.

## Sources

- [Model configuration — Claude Code Docs](https://code.claude.com/docs/en/model-config)
- [Issue #10993 — subagent model selection & `CLAUDE_CODE_SUBAGENT_MODEL`](https://github.com/anthropics/claude-code/issues/10993)
