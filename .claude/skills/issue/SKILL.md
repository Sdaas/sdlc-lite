---
name: issue
description: File one GitHub issue for this repo from a short description — a triage-grade interview, a draft per dev-docs/issue-template.md, one human approval, then gh issue create. Never branches, never edits code.
disable-model-invocation: true
argument-hint: "[one-line description of the bug or idea]"
---

# /issue — capture, don't design

Turn `$ARGUMENTS` (or, if empty, the human's next message) into **one** GitHub issue that conforms
to [`dev-docs/issue-template.md`](../../../dev-docs/issue-template.md). Read that file first — it is
the spec for title, sections, labels and the word cap. This skill only adds *how to get there*.

This skill runs **none** of the spine's gates 0–8 ([`.claude/sdlc/gates.md`](../../sdlc/gates.md)).
Its one STOP is approving the draft.

## Hard rules

- **Never branch, never edit, never commit.** The only file you write is the temporary body file in
  step 4. Reading the repo to find evidence and paths is fine.
- **Triage-grade, not design-grade.** Stop interviewing once the issue says *what*, *why* and
  *impact* (plus repro and tier for a bug). Design belongs to `/feature` Gate 1. If you catch
  yourself choosing files, functions or wording for the fix, stop.
- **Nothing is filed before the human approves the draft.**

## 1. Interview — to triage-grade

Ask only what you cannot find yourself; look facts up (files, docs, related issues) instead of
asking. Ask in one batch, then follow up only on gaps.

Settle, in this order:

1. **Type** — `bug` · `enhancement` · `documentation` · `other`.
2. **What** — the problem in 1–3 plain sentences.
3. **Why / impact** — who hits it, how often, what it costs.
4. **Bug only — repro and tier.** Numbered steps, observed vs expected, and the tier it was
   reproduced at (T1 / T2 / T3, defined in
   [`dev-docs/verification-ladder.md`](../../../dev-docs/verification-ladder.md)). Not yet
   reproduced? Say so in the draft; do not guess steps.
5. **Milestone** — none (backlog) unless the human names one.

Then check for duplicates: `gh issue list --state all --search "<keywords>"`. A likely duplicate →
show it and ask whether to proceed.

## 2. Draft

- **Title:** `<type>(<area>): <imperative summary>`, area from the template's list.
- **Body:** only the sections the template requires or allows for this type; omit the rest, never
  an empty heading. Acceptance criteria state observable outcomes, not implementation.
  Suggested Approach only if the human offered one, opening with the template's exact sentence.
- **Label:** exactly one, matching `**Type:**`; `other` gets no label.
- **Word cap:** ~300. Count the body with `wc -w`; over the cap → cut, don't ask.

## 3. STOP — approve the draft

Show the title, label, milestone (or "none — backlog"), word count, and the full body. Wait for an
explicit approval. Edit and re-show on any change request. Silence is not approval.

## 4. File

```bash
body=$(mktemp /tmp/issue-body.XXXXXX)   # write the approved body into "$body"
gh issue create --title "<title>" --body-file "$body" [--label <type>] [--milestone "<m>"]
rm -f "$body"
```

Print the issue URL. Stop there — no follow-up work, no branch, no plan.
