# ADR-13 — One `sdlc-lite` plugin; two channels are two marketplaces in two repos

**Context**
- A marketplace is one catalog in one repo, and a directory source is never version-pinned: a
  broken push to `main` would reach customers without a release (#41).
- The maintainer will ship unrelated plugins that should not share a repo.

**Decision**
- **One plugin.** `sdlc-lite` (folder `sdlc-lite-plugin/`) bundles the workflow over one guard, one
  set of pinned gates, one quality-standards SSOT. A new command joins only if it uses that shared
  isolation infrastructure.
- **Two channels.**
  - Dev: this repo's root catalog `sdlc-lite-dev` (live directory source, dev container only).
  - Release: umbrella repo `Sdaas/claude-plugins` (`sdaas`, `git-subdir` source pinned to a tag SHA).

**Consequences**
- Customers move only when a release is cut and they run `plugin update`.
- A release = `version` bump + tag + umbrella repoint (`plugin update` skips an unchanged version).
- The dev container cannot simulate a customer; the release check uses an isolated Claude config.
- Mechanics: [`RELEASING.md`](../RELEASING.md) §2, §4.
