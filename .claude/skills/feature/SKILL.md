---
name: feature
description: Implement one GitHub issue for this repo (plugin prose, hooks, or guard/policy/agentdefs/analyzer code) through the repo-local spine — gates 0–11 with 4 human STOPs (scope, design, tests, implementation), eval cases before prose, opus reviews before the verify spend, and no commit before approval. Declines docs-only and shell-only changes.
disable-model-invocation: true
argument-hint: "#NN [optional note]"
---

# /feature — one issue through gates 0–11

Take the issue in `$ARGUMENTS` through **all twelve gates** of
[`.claude/sdlc/gates.md`](../../sdlc/gates.md), executed per
[`.claude/sdlc/runbook.md`](../../sdlc/runbook.md). **Read both first** — `gates.md` defines every
gate, the four STOPs, the fast checks, both review checklists, finding routing, the eval budget and
the inherited rules; `runbook.md` holds the hard rules and how to execute each gate here. Where they
seem to disagree, `gates.md` wins.

## Entry

Applied at Gate 0, step 2, once the issue is found and conforms: the issue is a `bug` → point to
`/fix` and exit.
