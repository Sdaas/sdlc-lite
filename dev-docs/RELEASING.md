# Release Management

How this repo is versioned, how issues are triaged, and how a release is cut and consumed.

---

## 1. Versioning scheme

Semantic versioning (`MAJOR.MINOR.PATCH`) with **prerelease identifiers**:

- `1.0.0-beta.N` — a shippable, 1.0-quality build being **validated with early customers**
  before we commit to GA. This is *not* "half-built"; it is 1.0 on probation.
- `1.0.0-rc.N` — release candidate (optional, if beta stabilizes and we want a final gate).
- `1.0.0` — GA.
- Post-GA: `1.0.1` (patch), `1.1.0` (minor), `2.0.0` (breaking).

The version lives in **`sdlc-lite-plugin/.claude-plugin/plugin.json`** (`version` field)
and is mirrored by a git **tag** `v<version>` on the release commit.

> **Why not `0.5`?** `0.x` signals "expect churn / not feature-complete." Our first release is
> feature-complete and hardened — we are only validating it in the wild. `1.0.0-beta.1` says
> exactly that.

## 2. Distribution — two channels in two repos

The platform pins a plugin's version **only for git/archive sources**, *not* for a
**local-directory source loaded in place**. So the product runs two channels — each a **separate
marketplace in a separate repo** (ADR-13):

| Channel | Repo · catalog name | Audience | Marketplace source | Moves when |
|---|---|---|---|---|
| **dev / in-place** | `Sdaas/sdlc-lite` (this repo) · `sdlc-lite-dev` | maintainer + dev container | local **directory** source (`./sdlc-lite-plugin`) | every workspace edit (no release needed) |
| **release / stable** | `Sdaas/claude-plugins` (umbrella) · `sdaas` | real customers | **git-subdir** source pinned to a tag (explicit https url, `path: sdlc-lite-plugin`, `ref: v1.0.0-beta.1` + `sha`) | only when a release is cut |

- The dev container keeps loading the plugin from the workspace directory (see `DEVCONTAINER.md`)
  — unchanged.
- Customers add the **umbrella** marketplace (`Sdaas/claude-plugins`) and get exactly the tagged
  commit. The maintainer can keep committing to `main` (toward the next release) without affecting
  installed customers.
- **Why `git-subdir`, not `github`:** the plugin lives in the `sdlc-lite-plugin/` **subdirectory**;
  a plain `github` source can only target a repo root, so it installed **zero commands**. A
  `git-subdir` source with `path: sdlc-lite-plugin` targets the subdir. The url is an **explicit
  https url** (not the `owner/repo` shorthand) to avoid an SSH-default clone failure in clean-room
  environments.
- **`sha` beats `ref`** when both are set (exact pin). Each channel must resolve to a **distinct
  version string or SHA**, or `/plugin update` treats them as identical and skips the update.

## 3. Issue triage & labels

**Releases are GitHub milestones. Labels describe *type* only. No milestone = backlog.**

- **Milestones** = releases: `1.0.0-beta.1`, `1.0.0`, … An issue in a milestone is *committed to
  that release*.
- **Backlog** = **no milestone**. Deferred, not blocking any committed release.
- **Type labels** (the only labels we use for triage): `bug`, `enhancement`, `documentation`.
  (Standard GitHub labels like `good first issue`, `help wanted`, `duplicate`, `wontfix` remain
  available but are not part of triage.)
- **Do not** reintroduce sequencing labels (`v1`, `v1.1`, `v2`, `backlog`) — they duplicated
  milestone meaning and drifted. They were removed 2026-09-18.

**When you file or triage an issue:** give it exactly one type label; assign it to the target
release milestone if it's committed, otherwise leave it milestone-less (backlog).

## 4. Cutting a release — procedure

`release.sh` is **cross-repo**: it tags in this repo **and** repoints the umbrella catalog. Run it
from a clean `main`:

```bash
./release.sh <version> --umbrella <path-to-local-clone-of-Sdaas/claude-plugins>
# e.g. ./release.sh 1.0.0-beta.2 --umbrella /Users/sdaas/dev/claude-plugins
# (--umbrella may be supplied via $UMBRELLA_DIR instead)
```

What it does (each push is confirmation-gated):

1. **Validate:** clean tree, on `main`, `<version>` is valid semver, tag `v<version>` absent.
2. **Bump** `sdlc-lite-plugin/.claude-plugin/plugin.json` `version` → `<version>`; commit.
3. **Tag** `v<version>` (annotated) on the release commit; resolve its `sha`.
4. **Repoint the umbrella:** in the `--umbrella` clone, edit the `sdlc-lite` **git-subdir** entry's
   `ref`/`sha` to the new tag; commit. (Without `--umbrella` it prints the exact manual edit.)
5. **Push both repos** (confirmation-gated), then print the clean-room verify handoff.

Then **verify (the gate)** with `./release-verify.sh` — the automated clean-room install, Gate 0/1
smoke, `/plugin update` proof and milestone eval suite, described in
[`verification-ladder.md`](verification-ladder.md) §8 — and confirm the milestone's issues are closed
or explicitly punted before announcing the release. The full human-driven `/implement-feature` run
to green + commit is the final belt-and-suspenders check.

## 5. Consuming a release (customer)

```bash
claude plugin marketplace add Sdaas/claude-plugins   # the umbrella / release channel
claude plugin install sdlc-lite@sdaas                # version-pinned to the released tag
```

Then install the pinned toolchain and run `/implement-feature` — full walkthrough in the
[README](../README.md). To update to a newer release: refresh the marketplace, then
`claude plugin update sdlc-lite`.

## 6. Roadmap

Forward-looking scope lives in **`release-plan.md`** (current + next release only) — the narrative
plus the **execution order** of the milestone's issues (GitHub is the SSOT for *which* issues ship;
`release-plan.md` adds the order, by issue number only). Decision history lives in the **GitHub
issues** and the **ADRs** (Developer Guide), not in `release-plan.md`. Large, plan-mode-worthy issues
also get a branch-scoped **`<NN>-plan.md`** working plan (checked in, deleted at merge) — see
`CLAUDE.md` → Working conventions.
