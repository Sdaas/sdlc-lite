# 41-plan.md — execution & progress tracker for #41 (release engineering)

_Resumable with **"read 41-plan.md and continue."** Scratch/working plan for [#41](../../issues/41);
the durable rationale is **ADR-13** in `docs/developer-guide.md` §6. Delete this file when #41 closes._

_Last updated: 2026-09-18. Branch: `41-release-engineering`._

---

## Why this doc exists

#41 grew from "add a release channel" into a **structural rename + a two-repo marketplace split**
(decided via a grilling session, 2026-09-18). It is too big for one session, so this file carries the
locked decisions, the phased plan (with testing), and a checkbox tracker across sessions.

## Locked decisions (grilling, 2026-09-18)

| # | Decision |
|---|---|
| Q1 | **One plugin**, `sdlc-lite`, bundles the whole SDLC workflow (commands `implement-feature`, `analyze-run`, future `plan-feature`) over the shared guard hook + 5 gates + quality-standards. **Boundary rule:** a command joins `sdlc-lite` iff it uses that shared isolation infra; unrelated tools → separate plugin in its own repo. |
| Q2/Q5 | **Two channels = two marketplaces in two repos** (not the earlier two-entries-in-one-catalog). Future plugins live in **separate repos**, aggregated by an umbrella marketplace. |
| Q3 | `toy-greet` is a **tutorial-only prop** — stays in this repo's dev catalog for the Tutorial; **never** published to the customer/umbrella channel. |
| Q4 | Plugin name `sdlc-lite`; folder `implement-feature-plugin/` → `sdlc-lite-plugin/`; agents dispatch `sdlc-lite:<agent>`; **command names unchanged** (`/implement-feature`, `/analyze-run`). |
| Q6 | Umbrella repo = **`Sdaas/claude-plugins`** (public), catalog `name: "sdaas"`. Customers: `marketplace add Sdaas/claude-plugins` → `install sdlc-lite@sdaas`. |
| Q7 | This repo's root catalog is **dev-only**: `name: "sdlc-lite-dev"`, single directory entry `sdlc-lite` → `./sdlc-lite-plugin`, plus `toy-greet`. Container enables `sdlc-lite@sdlc-lite-dev`. README routes customers to the umbrella (avoid unpinned-install footgun). |
| Q8 | Do the rename/namespace churn **now** (pre-tag; breaking after release). |
| Q9 | `release.sh` becomes **cross-repo** — see Phase D for the resolved mechanism. |

## Target end-state (the picture)

```
Sdaas/sdlc-lite   (this repo — product + DEV channel)
  .claude-plugin/marketplace.json   name: sdlc-lite-dev
    plugins: [ {sdlc-lite -> ./sdlc-lite-plugin (directory, live)}, {toy-greet -> ./toy-greet-plugin} ]
  sdlc-lite-plugin/                 (was implement-feature-plugin/)
    .claude-plugin/plugin.json      name: sdlc-lite, version bumped per release
    commands/  implement-feature.md  analyze-run.md
    agents/    -> dispatched as sdlc-lite:test-writer, etc.
    hooks/ guard.py  analyzer/  skills/  toolchain/
  release.sh                        cross-repo: tag here + repoint umbrella
  dev container enables: sdlc-lite@sdlc-lite-dev

Sdaas/claude-plugins   (NEW umbrella repo — RELEASE channel)
  .claude-plugin/marketplace.json   name: sdaas
    plugins: [ {sdlc-lite -> github Sdaas/sdlc-lite, ref: vX.Y.Z, sha: ...} ]
  README.md
  customer: marketplace add Sdaas/claude-plugins ; install sdlc-lite@sdaas
```

## Current branch state (what's committed vs. to rework)

Commits on `41-release-engineering`:
1. `docs: ADR-13 ...` — **revised this session** to the umbrella design (correct; keep).
2. `feat: two-channel marketplace (github release + dev entry) + release.sh` — **SUPERSEDED**. Its
   `.claude-plugin/marketplace.json` (two entries in one catalog) and single-repo `release.sh` get
   reworked in Phases B & D. Keep the commit in history; do not try to un-commit.
3. `docs: replan #41 ...` — this doc + the ADR-13 revision (+ any leftover intermediate-name edits).

⚠️ **Intermediate names still in the tree** from an abandoned pass: some files may say
`sdaas-sdlc-lite` (marketplace) and `implement-feature-dev` (entry). These are **not final** — Phases
A/B rename everything to the locked names (`sdaas`, `sdlc-lite-dev`, plugin `sdlc-lite`). A grep sweep
in Phase B's tests catches stragglers.

⚠️ **Dev container** was rebuilt this session on the intermediate names; it will be **re-provisioned**
in Phase B against the final names (fresh volume; needs interactive OAuth login — a human step).

---

## Phased execution plan (+ testing per phase)

Commit per logical unit; **never commit before human approval**; **never push/tag** until Phase E.

### Phase A — Rename & restructure the plugin (this repo)
- `git mv implement-feature-plugin sdlc-lite-plugin` (preserve history).
- `plugin.json` `name` → `sdlc-lite`.
- Replace agent-namespace refs `implement-feature:` → `sdlc-lite:` (~93 refs across `SKILL.md`,
  `agents/*.md`, `guard.py`/`policy.py`, `hooks.json`, references). **Leave command names alone.**
- Update path refs to the old folder name (`implement-feature-plugin/…`) in docs/tests/configs.
- **Test:** `python3 -m pytest sdlc-lite-plugin -q` green (160+); `grep -rn "implement-feature:" .`
  and `grep -rn "implement-feature-plugin" .` return only intentional historical mentions (ideally
  none). Guard/analyzer unit tests are the safety net for the namespace change.

### Phase B — Dev catalog + dev container (this repo)
- Root `.claude-plugin/marketplace.json` → `name: "sdlc-lite-dev"`; single directory entry
  `sdlc-lite` → `./sdlc-lite-plugin`; keep `toy-greet`. **Remove any github/release entry** (moves to
  umbrella).
- `.devcontainer/claude/settings.json`: `extraKnownMarketplaces` key → `sdlc-lite-dev`;
  `enabledPlugins` → `sdlc-lite@sdlc-lite-dev`.
- Update `DEVCONTAINER.md` + `docs/developer-guide.md` §8 to the final names.
- **Test (in-container, THE Phase-B gate):** fresh volume rebuild → OAuth login (human) →
  `claude plugin install sdlc-lite@sdlc-lite-dev` → `/implement-feature` loads **live** from the
  workspace. Confirm settings self-healed with the final names.

### Phase C — Umbrella repo `Sdaas/claude-plugins` (NEW, public)
- Create repo (human-authorized outward action; `gh repo create Sdaas/claude-plugins --public`).
- Add `.claude-plugin/marketplace.json` `name: "sdaas"` with one entry: `sdlc-lite` → github
  `Sdaas/sdlc-lite`, `ref: v1.0.0-beta.1` (sha filled by `release.sh` at cut). Add a short `README.md`.
- **Test:** `claude plugin marketplace add Sdaas/claude-plugins` validates the catalog (full install
  test waits for the first tag → Phase E).

### Phase D — `release.sh` (cross-repo)
- Rework to: validate (clean tree, on `main`, semver, tag absent) → bump `plugin.json` version →
  commit + annotated tag in this repo → resolve sha → **update the umbrella catalog**: takes
  `--umbrella <path-to-local-clone-of-Sdaas/claude-plugins>` (or env), edits its `sdlc-lite` entry
  `ref`/`sha`, commits, and (with confirmation) pushes **both** repos. If `--umbrella` is absent, print
  the exact manual umbrella edit. Print the clean-room verify handoff.
- **Test:** `bash -n release.sh`; unit-test the JSON-surgery on temp copies of both catalogs
  (as done for the v1 script); do **not** run for real until Phase E.

### Phase E — Clean-room verify (THE RELEASE GATE)
- Isolated Claude config (own `CLAUDE_CONFIG_DIR`/HOME, toolchain installed, **no dev marketplace**):
  `marketplace add Sdaas/claude-plugins` → `install sdlc-lite@sdaas` → confirm a genuine GitHub
  clone/checkout of `v1.0.0-beta.1` (not a directory source) and cached version `1.0.0-beta.1` →
  run `/implement-feature` end-to-end on `test-fixtures/python-starter` (must pass).
- Confirm `/plugin update` picks up a version bump (bump → re-tag → repoint → update pulls).
- Only after this passes is the tag a real release.

### Phase F — Docs finalize (match exactly what was run)
- `RELEASING.md` §2 (channels table → two repos), §4 (procedure), §5 (customer consume) to the
  verified commands.
- `README.md` + `docs/user-guide.md` install/use → the umbrella commands, verified.
- Flip ADR-13 status → proven; update `release-plan.md` narrative when beta ships; close #41; `git rm` this file in the merge/close commit.

---

## Progress tracker

- [x] **A** — plugin rename/restructure (`sdlc-lite-plugin/`, name, namespace) + tests green
- [ ] **B** — dev catalog + container to final names + in-container live-load verified
- [ ] **C** — umbrella repo `Sdaas/claude-plugins` created + catalog + README
- [ ] **D** — cross-repo `release.sh` + surgery unit-tests
- [ ] **E** — clean-room verify (isolated config) install→run + `/plugin update` check  ← **the gate**
- [ ] **F** — RELEASING.md / README / User Guide finalized; ADR-13 proven; #41 closed

## Open items / risks
- **Namespace churn safety** — the 93-ref `sdlc-lite:` change is only as safe as the guard/analyzer
  unit tests; run them after Phase A before anything else.
- **Cross-repo push auth** in `release.sh` (Phase D) — new failure surface; confirmation-gated.
- **Umbrella footgun** — someone adds `Sdaas/sdlc-lite` (product repo) instead of the umbrella and gets
  an unpinned live install; mitigate with a clear README pointer (Phase B/C/F).
- **Backlog** — [#42](../../issues/42) release automation (release-please) still applies, now
  cross-repo aware.
