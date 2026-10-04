# Full-repo review — spec for `/review-repo`

> **Status:** this file is the spec for the repo-local skill `/review-repo` (#86). The
> skill runs the review below with the area agents and the consolidator pinned to
> `claude-opus-5-5` at `effort: high` in `.claude/agents/`. A measurement script reads the
> transcripts and confirms the actual model and effort. A wrong or UNKNOWN value is a hard stop:
> the report is headed `INVALID — not Opus 5.5 / high` and nothing is triaged. Until the skill
> exists, this file is not a safe way to run the review.

Run this before each release. It reviews every tracked file with parallel area agents and one
consolidator. The output is one ranked file, `review-YYYYMMDD.md` (today's date), in the repo root.
It is a kept record, not a temporary file. If the file exists, add `-2`, `-3` and so on.

**Models.** Every area agent and the consolidator use `claude-opus-5-5` at high effort. The
conductor (you) only dispatches and files; it does no review itself.

**Run it.** Tell Claude Code: *"Run `dev-docs/proposals/full-repo-review-prompt.md` for release
`<version>`."* Run it on a clean `main`, after the last product change.

---

## Conductor instructions

1. Run `git ls-files` and assign every tracked file to exactly one area below. Report any file that
   fits no area. Do not skip it.
2. Spawn one **area agent** per area, all in one message so they run in parallel. Use
   `model: opus`. Give each agent: its area's file list, the **Area brief** below, the **Audience
   rules**, the **Triage rule** and the **Finding format**.
3. Collect the area reports. Do not edit them.
4. Spawn one **consolidator** (`model: opus`). Give it every area report and the **Consolidator
   brief**. It writes `review-YYYYMMDD.md`.
5. Show the user the top of `review-YYYYMMDD.md` (counts per bucket). Do not file issues and do not
   change any file until the user approves.

### Areas

| # | Area | Files |
|---|---|---|
| 1 | Skill and agent prose (product, agent-read) | `sdlc-lite-plugin/skills/**` (including each skill's `references/`), `sdlc-lite-plugin/agents/**` |
| 2 | Enforcement code and its tests | `sdlc-lite-plugin/hooks/**`, `policy.py`, `agentdefs.py`, `conftest.py`, `sdlc-lite-plugin/commands/**`, `sdlc-lite-plugin/tests/**` |
| 3 | Analyzer and toolchain | `sdlc-lite-plugin/analyzer/**` (with its tests), `sdlc-lite-plugin/toolchain/**` |
| 4 | Evals and fixtures | `sdlc-lite-plugin/evals/**`, `test-fixtures/**`, `.devcontainer/**` |
| 5 | User docs and install path | `README.md`, `.claude-plugin/**`, `sdlc-lite-plugin/.claude-plugin/**`, `release*.sh`, `release.test.sh`, `Makefile`, `clean-run.sh`, `t3-run.sh`, `verify-entry-points.py`, `.gitignore`, `.env.example`, `LICENSE` |
| 6 | Developer docs | `dev-docs/*.md` (not `adr/`, `findings/`, `proposals/`) |
| 7 | Historical records | `dev-docs/adr/**`, `dev-docs/findings/**`, `dev-docs/proposals/**`, earlier `review-*.md` files |
| 8 | Repo-local skills and process | `.claude/**`, `CLAUDE.md`, `dev-docs/issue-template.md`, `toy-greet-plugin/**` |
| 9 | Overall repo structure | The whole `git ls-files` list and the directory tree, not file contents (read a file only to check a claim) |

---

## Area brief (give to every area agent)

You review one area of the `sdlc-lite` repo. Read the files in your list in full. Read other files
only to check a claim. For area 9, review the layout instead: see **Structure checks** below.
Look for:

- **Inconsistency.** Two places say different things: a doc and the code, a skill and an agent
  file, a model id in prose and in frontmatter, a command name, a path, a count, a threshold.
- **Gaps.** Something the product promises that nothing implements or tests. A rule in prose with
  no enforcement where the developer guide says it needs one. A gate with no approver. A loop with
  no bound.
- **Stale content.** A reference to a file, issue state, flag or command that no longer exists.
- **Anti-patterns.** One fact kept in two places (no single source of truth). A spec copied where
  a link belongs. A prose rule with no enforcement or test. Dead config, dead files, unused flags.
  A comment or doc that restates code and will drift. A loop, retry or budget without a bound.
- **Internal contradictions inside one document.** An early section that a later section
  contradicts. Counts, names, thresholds or steps that differ within the same file.
- **Install-path failures.** Anything a stranger would hit when they install from GitHub and run
  `/sdlc-init` then `/implement-feature` on their own Python repo.

Rules:

- **Report only what you verified by reading.** Quote the exact lines. If you cannot show it, drop it.
- **Do not review style or taste.** Report wording only when it is wrong or ambiguous in a way that
  can change what an agent does, or what a user does.
- **Do not fix anything.** Do not edit files. Do not run the plugin or the evals.
- **Check the repo's own rules.** Read `CLAUDE.md` and `dev-docs/developer-guide.md` §3 first. Test
  your area against that checklist.
- If your area is clean, say so in one line. Do not invent findings.

### Structure checks (area 9)

- Files in the wrong place, or named against the repo's own conventions.
- Root clutter: scripts, files or directories that belong under a subdirectory.
- Orphans: files that nothing references, or that the maps (`CLAUDE.md` Repo Contents,
  `dev-docs/README.md`) do not list.
- The maps list things that do not exist, or omit things that do.
- Duplicate or overlapping files and directories. Tracked files that should be ignored, and ignored
  files that should be tracked.
- A directory that mixes audiences (agent-read, human-read, historical) without a reason.

### Audience rules

Tag every file you report on with its audience:

- **agent-read:** `SKILL.md`, `agents/*.md`, `references/*`, `.claude/skills/`,
  `.claude/sdlc/gates.md`, `CLAUDE.md`.
- **human-read:** `README.md`, `tutorial.md`, `developer-guide.md`, `architecture.md`,
  `DEVCONTAINER.md`, `RELEASING.md`, `CHANGELOG.md`.
- **historical:** `adr/`, `findings/`, `proposals/`, earlier `review-YYYYMMDD.md` files. Report a broken link or a false claim about
  current behavior. Do not report prose style.
- **code / test / script:** everything else.

### Triage rule

Put each finding in exactly one bucket:

- **0.1.0** (fix before this release): a stranger following the README would hit a failure, a
  wrong output, or a contradiction between a doc and the code. Also: anything that could damage the
  user's repo or environment.
- **next-release:** real, but it affects maintainers or an uncommon path. Ordering matters.
- **backlog:** low impact, or taste, or a nice-to-have.

When unsure between two buckets, choose the later one and say why in the evidence.

### Finding format

One block per finding. No other prose.

```
- id: <area#>-<n>
  file: <repo path>:<line>      # more than one is fine
  audience: agent-read | human-read | historical | code
  claim: <one sentence: what is wrong>
  evidence: <exact quote(s) or command output that prove it>
  severity: high | medium | low
  bucket: 0.1.0 | next-release | backlog
  fix: <one sentence, optional>
```

---

## Consolidator brief

You receive the reports of all area agents. Produce `review-YYYYMMDD.md` in the repo root.

1. **Verify.** For every `high` finding and every `0.1.0` finding, re-read the cited lines yourself.
   Drop a finding you cannot reproduce. Mark the survivors `verified`.
2. **Dedupe.** Merge findings that describe one root cause across areas. Keep every file reference.
3. **Cross-area contradictions.** Areas were reviewed separately. Compare them now: README vs
   skills, skills vs agents vs `policy.py`, docs vs code, tests vs behavior. Add the contradictions
   no single agent could see.
4. **Rank** within each bucket: severity, then the number of users affected.
5. **Write the file** in this order:
   - A summary: counts per bucket, per audience, and the three most important findings.
   - The `0.1.0` bucket. Then `next-release`. Then `backlog`.
   - For each finding: id, file(s), claim, evidence, fix. Keep the area agents' wording where it
     is already clear.
   - A last section **Not reviewed**: files that fit no area, files an agent could not read.
6. Do not file issues. Do not change any other file.
