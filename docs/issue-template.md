# GitHub Issue Template

Use this for every GitHub issue in this repo. Goal: **human-understandable at a glance,
AI-actionable without the transcript that spawned it.**

## Rules

- **~300 words max.** The issue must fit on one screen.
- **Omit sections that don't apply** — never an empty heading, never "N/A".
- **No transcripts, chat logs, or session narrative.** *Exception:* verbatim program output —
  stack traces, logs, test failures, hook denials — in a fenced block.
- **Reference issues by `#NN` only.** Never copy an issue's spec into `release-plan.md` or
  another issue.
- **Don't restate what the repo already documents** — link to it.
- **Labels & milestones** (see `RELEASING.md` §3): exactly one type label matching the `**Type:**`
  line; `other` has no label, so leave such issues label-less. Milestone only if committed to a
  release — **no milestone = backlog**.

## Title

`<type>(<area>): <imperative summary>` — mirrors our commit style.

Area is one of: `gate-N` · `skill` · `guard-hook` · `analyzer` · `docs` · `release` · `toolchain`.

> `fix(guard-hook): test-writer can read the internal design`
> `feat(gate-0): auto-install the pinned toolchain`

## Sections by type

| Section | bug | enhancement | documentation | other |
|---|---|---|---|---|
| `**Type:**` line | req | req | req | req |
| Problem | req | req | req | req |
| Steps to Reproduce | req | — | — | opt |
| Evidence | — | req | req | req |
| Acceptance Criteria | req | req | req | req |
| Verification | req | req | opt | opt |
| Suggested Approach | opt | opt | opt | opt |
| Out of Scope | opt | opt | opt | opt |
| Open Questions | opt | opt | opt | opt |
| Context | req | req | req | req |

**What goes in each:**

1. **Problem** — 1–3 sentences, plainly what is wrong or missing. No history, no narrative.
2. **Steps to Reproduce** — numbered steps, then one-line `**Observed:**` / `**Expected:**`.
3. **Evidence** — 1–2 bullets: where the gap surfaced (dry run, review, user report) + link.
   Replaces Steps to Reproduce for non-bugs.
4. **Acceptance Criteria** — `- [ ]` checkboxes, one line each, each independently checkable.
   Bullets only, no prose.
5. **Verification** — bullets naming the proof command or harness only. No explanation.
6. **Suggested Approach** — **must open with this exact sentence:** *Suggestion only — not a spec.
   The implementer may deviate with a one-line rationale.* Then bullets of files / functions /
   mechanisms to touch.
7. **Out of Scope** — bullets. Include only where scope creep is a real risk.
8. **Open Questions** — bullets. Anything here **blocks work until answered**.
9. **Context** — one line of links: `Related: #NN · Docs: <path>`.

## Skeleton

```markdown
**Type:** bug | enhancement | documentation | other

## Problem
...

## Steps to Reproduce
1. ...
2. ...
**Observed:** ...
**Expected:** ...

## Evidence
- ...

## Acceptance Criteria
- [ ] ...
- [ ] ...

## Verification
- ...

## Suggested Approach
Suggestion only — not a spec. The implementer may deviate with a one-line rationale.
- ...

## Out of Scope
- ...

## Open Questions
- ...

## Context
Related: #NN · Docs: <path>
```

## Example — bug

> **Title:** `fix(guard-hook): implementer can write test files via NotebookEdit`

```markdown
**Type:** bug

## Problem
The test-integrity rule in `guard.py` blocks the implementer from Edit/Write on test files, but
not NotebookEdit — so the implementer can still rewrite the tests it must satisfy.

## Steps to Reproduce
1. Run `/implement-feature` to gate 6 with a repo containing `tests/test_x.ipynb`.
2. Have the implementer call NotebookEdit on that file.

**Observed:** The call is allowed; the audit log records it with no denial.
**Expected:** Denied, same as Edit/Write on a test file.

## Acceptance Criteria
- [ ] NotebookEdit on any test path is denied for `implementer`
- [ ] The denial is recorded in the audit JSONL
- [ ] Other agents are unaffected

## Verification
- `python3 -m pytest sdlc-lite-plugin -q`
- Green end-to-end dry run in the dev container

## Suggested Approach
Suggestion only — not a spec. The implementer may deviate with a one-line rationale.
- `hooks/scripts/guard.py` — add NotebookEdit to the tool set the test-integrity check covers

## Context
Related: #12 · Docs: `docs/developer-guide.md`
```

## Example — enhancement

> **Title:** `feat(gate-0): auto-install the pinned toolchain`

```markdown
**Type:** enhancement

## Problem
Gate 0 hard-fails when a pinned tool is missing and tells the user to install it by hand. Every
first run of the plugin on a new repo fails at least once.

## Evidence
- User Guide FAQ documents the manual install as a known friction point (`docs/user-guide.md`)
- Deferred from v1 as a v1.1 backlog item

## Acceptance Criteria
- [ ] Gate 0 offers to install `toolchain/requirements-dev.txt` when a tool is missing
- [ ] Install is opt-in — never runs without explicit user approval
- [ ] Declining leaves today's hard-fail behavior unchanged
- [ ] User Guide prerequisites updated

## Verification
- Green end-to-end dry run in the dev container, starting from an environment missing `mutmut`

## Out of Scope
- Managing virtualenvs or choosing a Python interpreter for the user

## Context
Related: #19 · Docs: `docs/user-guide.md`
```
