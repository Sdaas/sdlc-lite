# 49-plan.md — docs(repo): restructure into README (user) + dev-docs/ (developer)

Branch-scoped working plan for #49. Checked in on `49-docs-restructure`, `git rm`'d in the
merge/close commit. Resumable with **"read 49-plan.md and continue."**

## Locked decisions

- **New layout:**
  ```
  README.md                # absorbs docs/user-guide.md content; single user-facing doc
  dev-docs/
    README.md              # NEW — states audience + findings-vs-proposals split
    developer-guide.md
    tutorial.md
    RELEASING.md
    DEVCONTAINER.md
    issue-template.md      # + new "repo" area
    release-plan.md
    findings/              # was root design/ (4 files)
    proposals/             # was docs/design/ (4 files)
  ```
  `docs/`, `design/` deleted. `REVIEW-PROMPT.md` deleted (no `REVIEW.md` ledger exists —
  already dead; confirmed by `ls REVIEW.md` → not found).
- **Content rule:** move + repair links only. Do not rewrite doc prose (issue's own Out of
  Scope). Exception: `release-plan.md`'s own forward-looking note ("this file moves to
  dev-docs/release-plan.md as part of it") gets a light tense fix since the move will already
  be done — that's a move-artifact, not a content rewrite.
- **Judgment calls on stale-looking paths, decided during research (do not re-litigate):**
  - `docs/planning-suite-architecture` in issues #32/#47 is a **git branch name**, not a doc
    link — leave untouched.
  - #9's "see git history for `design/acceptance-31biii-...findings.md` (removed 2026-09-20)"
    is a historical citation of a since-deleted file's old path — leave untouched (rewriting it
    to `dev-docs/findings/...` would be factually wrong; the file never lived there).
  - #46's `docs/research/2026-09-20-*.md` mentions are a **naming drift** — those exact
    filenames actually live at `docs/design/2026-09-20-*.md` today → map to
    `dev-docs/proposals/2026-09-20-*.md` (fixes the move **and** the drift in one edit).
  - `docs/design/plan-feature.md`'s own internal mentions of `docs/plans/<X>/` (a hypothetical
    future output location, appears twice) are proposal content, not a live repo link — leave
    unchanged.
  - `2026-09-20-agentic-sdlc-gap-analysis.md`'s generic mention of "the `design/*-findings.md`
    files in this repo" **is** a live structural reference — update to `dev-docs/findings/`.
- **Relative-link checker:** new early step in `release-verify.sh`, runs host-only (no Docker),
  reachable standalone via a new `--links-only` flag, scans all `*.md` for
  markdown links whose target is a relative path, failing on any that doesn't resolve on disk.
- **Issues to edit** (path only, never re-copy spec into them): #9, #19, #21, #32, #34, #37,
  #39, #40, #42, #43, #44, #45, #46, #47, #48.
- **`48-plan.md` also updated** (untracked, on this same working tree) — its planned artifact
  paths (`docs/verification-ladder.md`, `docs/eval-tutorial.md`, etc.) get the `dev-docs/`
  prefix so #48 doesn't plan into a directory #49 just deleted.

## Phases (commit per phase, each shown for approval before committing)

- [x] **P1** — Branch `49-docs-restructure`. `git mv` all files into new layout, `git rm
      REVIEW-PROMPT.md`. Rewrite `README.md` to absorb `docs/user-guide.md` content +
      one-line dev-docs route + updated tree. Write `dev-docs/README.md`.
- [x] **P2** — Fix all relative links *inside* the moved files (depth-from-root changed for
      developer-guide.md, tutorial.md, RELEASING.md, release-plan.md, findings/*, proposals/*).
- [x] **P3** — Fix all references *outside* docs: `CLAUDE.md`; shipped `SKILL.md` path strings
      at `:142` and `:275`; `analyzer/TRANSCRIPT-FORMAT.md` + `SAMPLE-RECEIPT.md`;
      `agentdefs.py` comment; `release.sh` comments. Add `repo` area to `issue-template.md`.
- [x] **P4** — Update `48-plan.md` artifact paths.
- [x] **P5** — Add the relative-link checker + `--links-only` flag to `release-verify.sh`.
- [x] **P6** — Verify: `python3 -m pytest sdlc-lite-plugin -q`; `./release-verify.sh
      --links-only`; `grep -rn "docs/\|REVIEW-PROMPT\|DEVCONTAINER.md\|RELEASING.md"
      sdlc-lite-plugin/ *.md *.sh` clean; `gh issue list --state open --search "design/
      in:body"` clean.
- [x] **P7** — Edited 14 of the 15 listed issues (path-only substitutions, verified diff before
      push). #37 needed no edit — its only `design/` mention is the historical citation of a
      deleted file, deliberately left per the judgment call above. Confirmed clean via direct
      `gh issue view <n> --json body` greps on all 15 (not the `gh issue list --search`
      shortcut, which false-positives on "docs/" as a substring of "dev-docs/"). Closing #49.

## Post-review fixes (independent Opus review, pre-commit)

An independent read-only review agent checked P1–P6 against #49 and this plan before any
commit. Findings and resolutions:
- `SKILL.md:104`, `:185` still said "the User Guide" (deleted doc) — only `:275`'s rendered
  template had been fixed. Fixed both to "the sdlc-lite README".
- `SKILL.md:275`'s `README.md` wording is ambiguous at runtime — the plugin runs inside the
  *user's* repo, where `README.md` means their project's, not sdlc-lite's. Changed to "the
  sdlc-lite README (https://github.com/Sdaas/sdlc-lite)".
- `CLAUDE.md:75` still said "the User Guide's job" — fixed to `README.md`'s job.
- `dev-docs/findings/model-pinning-findings.md` — the dead `isolation-experiments.md` link had
  been silently deleted rather than de-linked with provenance kept, inconsistent with this
  plan's own rule (historical citations of deleted files stay, as text). Restored as plain text:
  "the since-removed `isolation-experiments.md` — see git history".
- `release-verify.sh`'s pass message said "tracked *.md files" but the checker scans **all**
  `*.md` via `find`, not `git ls-files` — fixed the wording to match actual behavior.
- `48-plan.md`'s doc-parity checklist still said "user-guide / developer-guide" — fixed to
  "README / developer-guide".

## Progress

All phases P1–P7 done. Repo changes committed in 3 logical units on `49-docs-restructure`
(040356c docs restructure, de7b666 plugin reference fixes, fa4cb0a link-checker). 14 GitHub
issues edited for path-only fixes; #49 closed. `git rm 49-plan.md` still pending as part of the
merge/close commit per its own stated convention.
