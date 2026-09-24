# Finding — a same-named command suppresses the `implement-feature` SKILL.md body

_Issue **#55**. Measured 2026-09-23 in the dev container, Claude Code **2.1.260**, model `sonnet`.
Phase 0 of `55-plan.md`: measurement only — **no fix applied at the time of measurement** (AC #1)._

## Result in one line

**All three load paths suppress the body, 6/6 runs.** Removing
`sdlc-lite-plugin/commands/implement-feature.md` fixes it on all three, 6/6 runs. The load path is
irrelevant; the **name collision** is the whole story.

## The two arms

| Arm | Plugin contents |
|---|---|
| **arm-a** | the plugin as shipped — `commands/implement-feature.md` **and** `skills/implement-feature/SKILL.md` |
| **arm-b** | identical, with `commands/implement-feature.md` **deleted** |

## The metric (deterministic, not model-judged)

Earlier probes asked the model to *report* a `SKILL.md`-only fact; the answers were noisy
(model flake and cold-cache first runs both read as failures). The measurement below instead
inspects the **session stream** (`--output-format stream-json --verbose`) for `SKILL.md`-only text:

- **canary:** `05-test-intent.md` — the Gate 3 WRITE-TESTS outbox filename. It occurs 5x in
  `SKILL.md` and **never** in the command shim.
- Prompt: `Invoke the Skill tool for sdlc-lite:implement-feature. Then reply DONE.`
- **Body loaded** ⇔ the canary appears anywhere in the stream. Byte size corroborates
  (~9-10 KB suppressed vs ~48-51 KB loaded).

`tool_result` alone is **not** a usable signal: it is the same 44-byte
`Launching skill: sdlc-lite:implement-feature` in **both** arms. The body (or its absence) arrives
in the *following* injected user message, which is why the issue's symptom looks like "the tool
returned nothing".

## The matrix — 3 load paths x 2 arms x 2 runs

| Load path | arm-a run1 | arm-a run2 | arm-b run1 | arm-b run2 |
|---|---|---|---|---|
| **A — directory marketplace** (container sessions) | SUPPRESSED (9.5 KB) | SUPPRESSED (9.5 KB) | **loaded** (51.3 KB) | **loaded** (48.1 KB) |
| **B — `--plugin-dir`** (what `claude plugin eval` uses) | SUPPRESSED (10.3 KB) | SUPPRESSED (10.4 KB) | **loaded** (50.2 KB) | **loaded** (48.1 KB) |
| **C — installed from umbrella** (`sdlc-lite@sdaas`, 1.0.0-beta.2) | SUPPRESSED (9.6 KB) | SUPPRESSED (9.4 KB) | **loaded** (48.5 KB) | **loaded** (48.1 KB) |

Path C's arm-b was produced by deleting the shim from the **installed** copy
(`~/.claude/plugins/cache/sdaas/sdlc-lite/1.0.0-beta.2/commands/implement-feature.md`), so it is a
real measurement of the installed path, not a stand-in.

## Root cause — what actually gets injected

In arm-a the runtime resolves `Skill(sdlc-lite:implement-feature)` to the **command file**, injects
the command's own markdown, and then marks the skill as already loaded. Verbatim from an arm-a
stream:

```
tool_use   Skill {"skill": "sdlc-lite:implement-feature", "args": "add a to_roman(n) helper"}
tool_result "Launching skill: sdlc-lite:implement-feature"
user text   "Skill /sdlc-lite:implement-feature is already loaded above; instructions unchanged."
user text   "# /sdlc-lite:implement-feature — conductor entry point\n\nYou are the **conductor** ..."
```

That last block is `commands/implement-feature.md`, not `SKILL.md`. A **re-invocation does not
recover** — it returns *"the skill instructions were previously loaded"*. The conductor, holding a
12-line shim that tells it to "load the skill", has nothing to walk; in one observed run it
dispatched a subagent to **go find `SKILL.md` on disk**, and otherwise it improvises gate prose from
the shim plus the skill `description`.

Both arms register the same entry point: `sdlc-lite:implement-feature` appears in the session's
`slash_commands` **and** `skills` lists in arm-a *and* arm-b. The shim adds no reachability — it only
shadows.

## What the human's typed `/implement-feature` actually does

The matrix above measures the **`Skill` tool** path. The typed slash command is a *different*
mechanism, and it is broken differently — measured from the on-disk session transcripts
(`~/.claude/projects/<cwd>/<session>.jsonl`), in both interactive and headless `-p` sessions,
which behave identically:

**arm-a (as shipped)** — the slash expands to **the command shim**, not the score:

```
USER[0]  <command-name>/sdlc-lite:implement-feature</command-name> <command-args>...</command-args>
USER[1]  "# /sdlc-lite:implement-feature — conductor entry point\n You are the **conductor** ...
          Load and follow the **implement-feature skill** — its SKILL.md is your full score."
TOOL     Skill {"skill": "sdlc-lite:implement-feature"}
USER[2]  tool_result "Launching skill: sdlc-lite:implement-feature"
USER[3]  "Skill /sdlc-lite:implement-feature is already loaded above; instructions unchanged."
TOOL     Bash  find / -type d -iname "*implement-feature*"      <- hunting for SKILL.md on disk
```

The shim tells the conductor to load the skill; the skill load returns *"already loaded"*; the body
never arrives. The score reaches context only later, and only because the conductor **searched the
filesystem and `Read` the file itself** — the canary first appears at transcript line 74 inside a
`Read` result, complete with `cat -n` line numbers. That is recovery by improvisation, not an
entry point.

**arm-b (shim deleted)** — the slash expands to the score directly:

```
USER[0]  <command-name>/sdlc-lite:implement-feature</command-name> <command-args>...</command-args>
USER[1]  "Base directory for this skill: .../skills/implement-feature
          # implement-feature — the conductor's score ..."
```

No `Skill` tool call at all. The bare `/implement-feature` resolves to the namespaced form.

## The two entry mechanisms are distinct — which is what makes explicit-entry enforceable

| | the human types `/implement-feature` | the model auto-invokes from a phrasing match |
|---|---|---|
| interactive | CLI expands the slash command, injects `SKILL.md` — **no `Skill` tool call** | goes through the **`Skill` tool** |
| headless `-p` | identical — also expands | goes through the **`Skill` tool** |

```
you type /implement-feature   ──►  CLI expands  ──►  SKILL.md injected as a user message
                                   (no tool call  ──►  no PreToolUse  ──►  guard never runs)

model decides from phrasing    ──►  Skill tool  ──►  PreToolUse  ──►  guard DENIES
```

Denying the `Skill` tool therefore blocks auto-invocation **without touching** the human's path — not
because the guard can tell the two apart (it cannot see intent; it denies every `sdlc-lite:` skill
call unconditionally), but because the human's path makes no such call. The standing assumption is
that Claude Code keeps expanding typed slash commands outside the `Skill` tool; re-measure if its
skill/command resolution changes.
Auto-invocation is not hypothetical: the prompt *"I want to add a to_roman(n) helper to this python
repo, built test-first with staged approvals"* loaded the entire score, unasked, in arm-b.

**Measurement caveat that cost two wrong conclusions.** `--output-format stream-json` does **not**
surface the expanded command message or the injected skill body. Read the **on-disk transcript** for
anything about the slash path; the stream is fine for the `Skill`-tool path. An earlier draft of this
finding claimed headless never expands slash commands, and that `release-verify.sh` had therefore
never exercised the real entry point. Both were artifacts of reading the stream — headless expands
exactly like interactive, and the smoke does drive the real entry point.

## Why "Preflight passed" is still not evidence

`release-verify.sh`'s Gate-0 smoke asserts gate markers (`Preflight passed`, a STOP marker). **arm-a
reaches those markers anyway** — by hunting down `SKILL.md` or by improvising from the shim — so the
smoke stays green while the entry point is broken. Any regression check for this bug must assert
`SKILL.md`-only text arriving *through the entry point*, not gate markers. (Evidence behind the
behavioral canary in `55-plan.md` Phase 2.)

## Reproduce

The probe was a throwaway `.tmp.sh`, deleted after the measurement (the durable checks are
`sdlc-lite-plugin/tests/test_entry_points.py` and the `release-verify.sh` body canary). To rebuild it:

1. Copy `sdlc-lite-plugin` to `/tmp/arm-a` and `/tmp/arm-b`; delete
   `commands/implement-feature.md` from **arm-b** only.
2. For the directory-marketplace path, wrap each arm in a `/tmp/mkt-<arm>/` holding a
   `.claude-plugin/marketplace.json` with a `directory` source, and install it into a per-arm
   `CLAUDE_CONFIG_DIR`. For the installed path, `marketplace add Sdaas/claude-plugins` +
   `install sdlc-lite@sdaas` into an isolated config, then delete the shim from the versioned cache
   dir to make its arm-b.
3. Per cell, run in a scratch cwd:
   `claude -p "Invoke the Skill tool for sdlc-lite:implement-feature. Then reply DONE." --model sonnet
   --allowed-tools Skill --output-format stream-json --verbose` and grep the stream for
   `05-test-intent.md`.
4. For anything about the **typed slash** path, read the on-disk transcript instead (see the caveat
   above), and drive an interactive session through a pty — a fresh `CLAUDE_CONFIG_DIR` needs a
   seeded `.claude.json` (`hasCompletedOnboarding`, per-project `hasTrustDialogAccepted`) or the
   session stops at the theme/trust wizards.
