# Release Management

How this repo is versioned, how issues are triaged, and how a release is cut and consumed.

> **Status (2026-09-18):** the **conventions** below are settled and in force *now*. The
> **procedure** (§4) is **not yet proven** — it is filled in and verified against a real
> clean install→run as part of **[#41 — release engineering](../../issues/41)**. Do not
> treat §4 as authoritative until #41 closes.

---

## 1. Versioning scheme

Semantic versioning (`MAJOR.MINOR.PATCH`) with **prerelease identifiers**:

- `1.0.0-beta.N` — a shippable, 1.0-quality build being **validated with early customers**
  before we commit to GA. This is *not* "half-built"; it is 1.0 on probation.
- `1.0.0-rc.N` — release candidate (optional, if beta stabilizes and we want a final gate).
- `1.0.0` — GA.
- Post-GA: `1.0.1` (patch), `1.1.0` (minor), `2.0.0` (breaking).

The version lives in **`implement-feature-plugin/.claude-plugin/plugin.json`** (`version` field)
and is mirrored by a git **tag** `v<version>` on the release commit.

> **Why not `0.5`?** `0.x` signals "expect churn / not feature-complete." Our first release is
> feature-complete and hardened — we are only validating it in the wild. `1.0.0-beta.1` says
> exactly that.

## 2. Distribution — two channels

The platform pins a plugin's version **only for git/archive sources**, *not* for a
**local-directory source loaded in place**. So the repo runs two channels:

| Channel | Audience | Marketplace source | Moves when |
|---|---|---|---|
| **dev / in-place** | maintainer + dev container | local **directory** source (`./implement-feature-plugin`) | every workspace edit (no release needed) |
| **release / stable** | real customers | **github** source **pinned to a tag** (`ref: v1.0.0-beta.1`, optionally `sha`) | only when a release is cut |

- The dev container keeps loading the plugin from the workspace directory (see `DEVCONTAINER.md`)
  — unchanged.
- Customers add the **release** marketplace and get exactly the tagged commit. The maintainer can
  keep committing to `main` (toward the next release) without affecting installed customers.
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

> ⚠️ **TBD — proven and finalized by [#41](../../issues/41).** The steps below are the *intended*
> shape; they are not yet run end-to-end. #41's done-criterion is that this section matches a real
> clean install→run exactly.

Intended shape (to be verified):

1. Confirm the release milestone's issues are closed (or explicitly punted).
2. Bump `plugin.json` `version` → `<version>`.
3. Commit, tag `v<version>`, push tag.
4. Update the **release** marketplace entry to pin `ref`/`sha` to the tag.
5. **Verify (the gate):** from a *clean* environment — add the release marketplace,
   `/plugin install`, run `/implement-feature` on a fixture end-to-end. It must succeed.
6. Only after the clean install→run passes is the release real.

`release.sh` (also delivered by #41) automates steps 2–4 and hands off to the verify step.

## 5. Consuming a release (customer)

> ⚠️ **TBD — finalized by [#41](../../issues/41)** and mirrored into the User Guide once verified.

Intended shape: add the release marketplace, `/plugin install implement-feature@<marketplace>`,
install the pinned toolchain, run `/implement-feature`. Exact commands live in the User Guide
after #41 verifies them.

## 6. Roadmap

Forward-looking scope lives in **`plan.md`** (current + next release only). Decision history lives
in the **GitHub issues** and the **ADRs** (Developer Guide), not in `plan.md`.
