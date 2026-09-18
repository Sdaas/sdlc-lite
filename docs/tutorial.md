# Tutorial — how a workflow plugin like this is built

This tutorial teaches the concepts behind `implement-feature` from the ground up: the four building
blocks (plugin, command, skill, subagent), how a *workflow* is just a skill whose body is an ordered
script of gates, and how to launch and **isolate** subagents safely. It uses a tiny runnable example,
`toy-greet`, so you can see the pattern fire before reading the real product.

If you want to *run* the product, read the [User Guide](user-guide.md); to work on it, the
[Developer Guide](developer-guide.md).

---

## 1. The four building blocks

Four things nest together, smallest to biggest:

- **Skill** — a folder whose heart is `SKILL.md` (a `name` + `description` + plain-English
  instructions). A reusable *instruction packet* / "playbook." It contains guidance, not running code.
  A skill can **auto-activate** when its `description` matches the situation.
- **Slash command** — a user-triggered entry point (`/implement-feature`). *You* press the button on
  purpose. A command is usually a thin file that says "load this skill / run this workflow."
- **Subagent** — a separate Claude instance given a focused job. It runs in its **own fresh context
  window**, does the work, and returns only a result. Keeps the orchestrator's context clean and
  enables specialized, isolated work.
- **Plugin** — the distributable **package** bundling skills + commands + subagents + a manifest. How
  you install and share.

**Nesting:** plugin ⊃ (commands + skills + subagents); a command kicks off a skill; a skill may
delegate to subagents. **Key distinction:** a skill can *auto-activate* by description; a command is
*deliberate* invocation.

---

## 2. Anatomy of a skill

A skill is a **folder** whose heart is `SKILL.md`, with two parts:

1. **Frontmatter** (YAML between `---` fences): `name` + `description`. Claude reads *only* name +
   description to decide relevance — so write the `description` about **when to use it** (triggers,
   phrasings, situations), not merely what it is. A vague description makes the skill fire at the wrong
   time, or never.
2. **Body** (Markdown below): the actual instructions — steps, rules, gates, checklists.

**Progressive disclosure** is the key idea: Claude keeps only every skill's lightweight name +
description resident; the heavy **body loads on demand** when the skill triggers. So skills can hold
long, detailed instructions cheaply — they cost nothing until needed. A skill folder can also ship
**extra files** (templates, reference docs, scripts) referenced from the body and loaded only when a
step needs them — the same disclosure principle one level deeper. (The real product uses this for its
`references/` templates and its `quality-standards.md`.)

---

## 3. Subagents

A subagent is a **fresh Claude instance** the orchestrator spins up for one focused job.

1. **Isolated context.** It starts clean and sees only the brief + inputs you pass — not your whole
   conversation. You must brief it explicitly.
2. **Does work, returns a result.** It runs its own tool calls in its *private* context, then hands
   back only a summary. Its intermediate churn never enters the orchestrator's context.
3. **Can be specialized.** Named subagent types with their own instructions and even restricted
   toolsets (e.g. a read-only reviewer).

**Why it matters:** context-heavy, self-contained phases (write tests, deep review, mutation testing)
delegate cleanly, keeping the orchestrator focused on sequencing and talking to the user. **Trade-off:**
isolation means the subagent doesn't know what you discussed — pass everything it needs, ideally via
**context files**. Good delegation is a crisp, self-sufficient brief.

---

## 4. The workflow pattern & gates

A **workflow is a skill whose body is an ordered English script of steps and gates.** The **agent is
the runtime** — you don't write a loop that calls phase 1, phase 2; you write instructions the agent
executes conversationally. That is why "no driver code" is possible.

Three mechanisms:

1. **Sequenced steps** — numbered phases followed in order.
2. **Gates** — approval checkpoints that decide *whether* advancing is allowed. A gate's approver is
   either **a human** ("STOP until the user replies APPROVED" — for requirements, spec, final review)
   or **a machine-checkable condition** ("until all tests pass / mutation score ≥ threshold").
3. **Loops-as-instructions** — "run tests; if any fail, fix and re-run; repeat until all pass."

A trap worth remembering: **prose gates are only as strong as their wording.** Weak: "ask the user."
Strong: "**STOP. Do not write any code until the user replies APPROVED.**" Use imperative,
unambiguous, capitalized stop-words.

---

## 5. Plugin packaging

A plugin is a folder with a convention-based layout:

```
my-plugin/
├── .claude-plugin/plugin.json   ← manifest (identity metadata only)
├── commands/    ← one .md per slash command (filename = command name)
├── skills/      ← one folder per skill (each has SKILL.md)
├── agents/      ← one .md per subagent definition
└── hooks/       ← hooks.json + scripts (optional)
```

- Content is **auto-discovered by convention** — drop a file in `commands/` and it works; nothing is
  enumerated in the manifest.
- The **manifest is pure identity metadata** (`name` is the only required field; `version`,
  `description`, `author`, `license`, `keywords` are recommended/optional). Its presence in
  `.claude-plugin/` is what makes the folder a plugin.
- **Plugin commands are namespaced** `/<plugin>:<command>` — `toy-greet-plugin/commands/greet.md`
  becomes **`/toy-greet:greet`**, never bare `/greet`. Namespacing prevents collisions across installed
  plugins.
- Plugins install from a **marketplace** (a local folder or a git repo with a `marketplace.json`).
  `marketplace add` *registers a catalog* (nothing installed yet); `install <plugin>@<marketplace>`
  *materializes + activates* one plugin from it. Prefer the CLI installer for deterministic installs —
  typing `/plugin install X@Y` as a session one-liner can just open the manager UI and no-op.

---

## 6. The runnable example: `toy-greet`

`toy-greet-plugin/` is a minimal, two-file plugin — the whole workflow lives *inside the command file*
(short workflows can; long ones belong in a skill with a thin command caller, which is what the real
product does):

```
toy-greet-plugin/
├── .claude-plugin/plugin.json   ← identity metadata
└── commands/greet.md            ← the /greet command = a 2-gate workflow
```

`commands/greet.md` *is* the workflow made concrete: a `description` frontmatter + a body of ordered
prose — **Phase 1 (collect)** → **GATE 1 (confirm inputs)** → **Phase 2 (draft)** → **GATE 2 (approve
final)**. Both gates are human-approval gates worded imperatively. No Python, no loop code — the agent
is the runtime obeying the prose. Read it end-to-end; it's the whole pattern in ~35 lines.

### Run it in the dev container

Testing a plugin against your global `~/.claude` pollutes the host (an install writes both a config
entry *and* a cached copy under `~/.claude/plugins`). This repo instead runs Claude Code inside a
**dev container** with its own isolated `~/.claude` — zero host footprint, disposable clean slate, and
it exercises the real install path. (Full lifecycle: [DEVCONTAINER.md](../DEVCONTAINER.md).)

```bash
# on the host, from the repo root (Docker Desktop running):
devcontainer up --workspace-folder .            # build if needed + start (idempotent)
devcontainer exec --workspace-folder . claude   # jump into Claude Code inside
```

Then, inside the container's Claude session:

```bash
claude plugin marketplace add /workspaces/sdlc-lite   # CLI form is deterministic
```
```bash
claude plugin install toy-greet@sdaas-sdlc-lite   # CLI form is deterministic
```
```
/reload-plugins
/toy-greet:greet
```

Watch the two gates fire: Phase 1 collect → **GATE 1** confirm → Phase 2 draft → **GATE 2** approve.
That is the driverless-workflow pattern running under real Claude Code.

---

## 7. From toy to product: conductor + isolated gates

The real `implement-feature` is the same pattern scaled up: a **conductor** (the interactive session
running the skill) that walks gates in order and **delegates the bias-sensitive gates to isolated
subagents**. Two ideas make it more than a bigger `toy-greet`:

- **Isolation kills bias.** A reviewer who watched the code get written shares the author's blind spots
  (*anchoring*); one model at every gate repeats that model's blind spot (*monoculture*). Fix both:
  fresh context per critic + a stronger model at the review gates than at implementation.
- **Every handoff is a file.** Each gate reads a defined *inbox* and writes a defined *outbox* — never
  the prior gate's raw transcript. This is what lets you *choose* what each agent sees, which is what
  makes selective isolation (below) possible.

Two design touches are worth calling out because they recur in any serious workflow:

- **The interface/internal design split.** The design is written as two files — a public-contract
  interface (shared with the test-writer) and an internal algorithm (withheld). The test-writer is
  *algorithm-blind*, so its tests encode the **contract**, not the implementation — and a wrong
  implementation can actually fail them.
- **Per-gate model/effort pinning via agent-definition files.** To run each gate on a chosen
  model *and* effort, each isolated gate becomes a named agent type in `agents/<role>.md` whose
  frontmatter pins `model`, `effort`, and `tools`. (The Agent tool can set model inline but **not**
  effort — so effort must live in the file.)

The Developer Guide walks the full twelve-gate score.

---

## 8. Launching & isolating subagents (the reusable playbook)

Spawning a subagent is easy; spawning one *safely* means deciding, up front, what it runs as, what it
can touch, and how you'll know what it did. A fresh subagent starts with broad default capabilities, so
each of these is a control problem with a supported mechanism.

| Goal | Mechanism | Where configured |
|---|---|---|
| **Model** | `model:` frontmatter (or inline `model` param) | agent-def / spawn call |
| **Effort** | `effort:` frontmatter — **no inline override** | agent-def only |
| **Tool allow/deny** | `tools:` / `disallowedTools:` (hard restrictions) | agent-def |
| **Read confinement** | `permissions.blockReadsOutsideWorkingDirectories` (all-or-nothing fence) | settings |
| **Secrets guardrail** | PreToolUse hook denying `.env`/keys for every agent | plugin `hooks/hooks.json` |
| **Per-agent access** | the same hook, keyed on `agent_type` | plugin hook |
| **Side-effect isolation** | `isolation: worktree`, `permissionMode: plan` | agent-def |
| **Audit / attribution** | hook audit log (+ transcript for model/tokens) | plugin hook / transcript |
| **Context handoff** | curated files + a self-sufficient brief | spawn brief |
| **Discovery & naming** | scope precedence; namespaced `plugin:agent`; ship hooks | plugin / user settings |

### The hard-won gotchas (verify runtime behavior — don't trust the docs)

Everything below was confirmed empirically in a container, and in several places the docs or defaults
were *wrong*:

1. **Tool allow/deny does not confine reads.** `disallowedTools: Write` stops writing, not reading —
   and a critic that keeps `Bash` can *write* files anyway via `cat >`/heredocs. So "read-only" and
   "algorithm-blind" cannot be bought by tool-removal alone. Confine reads with the working-directory
   fence or a PreToolUse hook.
2. **Ship must-fire config with the plugin.** A *project* `.claude/settings.json` PreToolUse hook did
   **not** fire in headless runs; a **plugin** hook fired for the conductor *and* every subagent. Put
   reliability-critical hooks in the plugin (or user settings).
3. **Plugin agents are namespaced.** Address them as `plugin:agent` (e.g.
   `sdlc-lite:test-writer`) — the bare name will not resolve.
4. **Effort is frontmatter-only** — pin it in the agent-def; there's no spawn-time override.
5. **A worktree does not hide files** — `isolation: worktree` is a full branch copy. To keep a file
   from an agent, keep it out of the agent's lane (the fence) or deny it in the hook.
6. **Don't rely on parsing the transcript** for anything critical — its format is internal/unstable.
   The hook audit log is the dependable record; use the transcript only as a best-effort source for
   model/token figures.

### How `implement-feature` enforces isolation (the guard hook)

A single **plugin-shipped PreToolUse hook** (`hooks/hooks.json` → `hooks/scripts/guard.py`) does the
cross-cutting work on every `Read`/`Bash`/`Grep`/`Glob`/`Edit`/`Write`/`NotebookEdit`, from the
conductor *and* every subagent. It keys on the `agent_type` on stdin and: (a) **audits** every call to
a run-log; (b) denies **secrets** for all agents; (c) denies the **test-writer** reading the internal
design (algorithm-blind); (d) denies **any subagent** reading under `handoff/draft/`
(draft-confinement); (e) denies the **implementer** editing any test file (it must pass the tests, not
change them). A `deny` + exit code 2 hard-blocks the call. This is **defense-in-depth** with the
agents' own role instructions — in testing, the test-writer refused on its own *before* the hook even
fired.

### Proving it: measurement, not orchestration

Enforcing isolation *preventively* (the guard hook) is only half the story; you also want to *prove*
after the fact what each agent did. The `analyzer/` reads the two evidence sources a run leaves behind —
the guard's audit log (stable, load-bearing) and the session transcript (best-effort, for model/tokens)
— and reports the per-gate model split + an isolation-compliance pass/fail. Crucially it is
**deterministic Python that only reads**, never a summarizer subagent: "did the forbidden read happen?"
is a grep-and-count fact, and making the analyzer an agent would inject a second AI acting inside the
system — re-introducing the very "driver" the workflow avoids. **Code is allowed when it measures or
enforces, never when it orchestrates.**

---

## 9. Where to go next

- **Read the toy:** `toy-greet-plugin/commands/greet.md` — the whole pattern in one short file.
- **Read the real score:** `sdlc-lite-plugin/skills/implement-feature/SKILL.md` — the twelve
  gates as an ordered English script.
- **Read the enforcement:** `sdlc-lite-plugin/hooks/scripts/guard.py` and `analyzer/` — the
  only two pieces of real code, and why they're allowed to be code.
- **Understand the decisions:** the [Developer Guide](developer-guide.md)'s ADRs and design principles.
