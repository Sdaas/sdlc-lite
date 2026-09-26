---
name: fix
description: Fix one bug-labelled GitHub issue for this repo (plugin prose, hooks, or guard/policy/agentdefs/analyzer code) through the repo-local spine — reproduce it first, gates 0–11 with 4 human STOPs (scope, design, tests, implementation), then deposit the reproducing case so it stays fixed. No commit before approval. Declines non-bug, docs-only and shell-only issues.
disable-model-invocation: true
argument-hint: "#NN [optional note]"
---

# /fix — one bug through gates 0–11, plus REPRODUCE and DEPOSIT

Take the issue in `$ARGUMENTS` through the gates of [`.claude/sdlc/gates.md`](../../sdlc/gates.md)
in this order — **0, 1, 1b REPRODUCE, 2 … 8, 8b DEPOSIT, 9, 10, 11** — executed per
[`.claude/sdlc/runbook.md`](../../sdlc/runbook.md). **Read both first** — `gates.md` defines every
gate (1b and 8b under *Gates added by `/fix`*), the four STOPs, the fast checks, both review
checklists, finding routing, the eval budget and the inherited rules; `runbook.md` holds the hard
rules and how to execute each gate here, including the `/fix` notes. Where they seem to disagree,
`gates.md` wins.

## Entry

Applied at Gate 0, step 2, once the issue is found and conforms: the issue is not labelled `bug` →
point to `/feature` and exit.
