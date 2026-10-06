# Acceptance container — a stranger's machine

The acceptance container is a disposable Docker container that acts as the machine of a
stranger. A human uses it to install a **released** sdlc-lite plugin from GitHub and to run it on
a small Python repo, with `README.md` as the only guide. This is the last check of a release
([`RELEASING.md`](RELEASING.md) §4).

It is **not** the dev container. Read §2 before you use either one.

---

## 1. Why it exists

The release bar is: a stranger installs the plugin, runs it on their own Python repo and finishes
without damage and without undocumented workarounds. Before this container, the human run used a
fixture in the dev container. That run did not test the bar:

- The dev container has the pinned toolchain installed. `/sdlc-init` had nothing to install.
- The fixture had the `/sdlc-init` config already in it.
- The fixture had a `BRIEF.md` test file. The workflow read it as a spec (#100).
- The dev container has a dev profile, a mounted repo and a token from `.env`. A stranger has
  none of these.

The acceptance container starts from what a stranger has, and nothing more.

## 2. Two containers — do not mix them up

| | Dev container | Acceptance container |
|---|---|---|
| Name | `sdlc-lite-test` | `sdlc-lite-acceptance` |
| Defined in | `.devcontainer/` | `acceptance/` |
| Start with | `devcontainer up --workspace-folder .` | `./acceptance.sh up` |
| Purpose | Develop and test the plugin | Accept a release, as a stranger |
| Plugin source | The workspace (live), or GitHub in a `~/.claude-verify` profile | GitHub only, installed by the human |
| Python toolchain | Pre-installed, pinned | None. `/sdlc-init` installs it |
| Claude Code | Pinned version, no auto-update | Latest at build time, auto-update on |
| Mounts | This repo at `/workspaces/sdlc-lite` | None |
| Login | Token from `.env` | The human runs `/login` |
| Shell prompt | normal | `[ACCEPTANCE]`, plus a banner |

"Clean-room" in `release-verify.sh` and [`DEVCONTAINER.md`](DEVCONTAINER.md) means a fresh Claude
profile **inside the dev container**. It is not this container.

## 3. Use it for / do not use it for

**Use it for:**
- The human run of a release, after `release-verify.sh` is green.
- Checking that the README alone is enough to install, set up and run the plugin.
- Reproducing a problem that a user reports from a clean machine.

**Do not use it for:**
- Developing or debugging plugin source. It has no access to this repo. Use the dev container.
- Unreleased code. It installs only what the release channel (`Sdaas/claude-plugins`) serves.
- Automated runs, evals or T3 runs. Those belong to the dev container (`dev-docs/t3-runs.md`).
- Fixing a README gap inside the container. Write the gap down; fix the README in this repo.

## 4. What the user does

Do these steps in order. From step 3 on, use only `README.md` as your guide. Write down each place
where the README is wrong, unclear or silent.

**On the Mac, in this repo's root (`/Users/sdaas/dev/sdlc-lite`). Docker Desktop must run.**

1. Start a fresh container: `./acceptance.sh up`. It builds the image and prints the Claude Code
   version. If the container exists, run `./acceptance.sh down` first.
2. Open a shell in it: `./acceptance.sh shell`. You are user `stranger` in `~/mypackage`, and the
   prompt shows `[ACCEPTANCE]`.

**In the acceptance shell.**

3. Open the README on GitHub (`https://github.com/Sdaas/sdlc-lite`) in a browser on the Mac.
4. Make a virtualenv and activate it (README Quick start step 1):
   `python3 -m venv .venv && source .venv/bin/activate`. The fixture's `.gitignore` already
   lists `.venv/`.
5. Add the read rule to `~/.claude/settings.json` (README Quick start step 2). The file does not
   exist yet, so make it with the JSON from the README.
6. Start Claude Code from the same shell: `claude`. Do the first-run setup and log in with
   `/login`.
7. Install the plugin **inside the session** (README Quick start step 4):
   `/plugin marketplace add Sdaas/claude-plugins`, then `/plugin install sdlc-lite@sdaas`, then
   `/reload-plugins`. If the install does nothing, exit claude, use the terminal form in the
   README (One-time setup §1), and start `claude` again. Write down which form worked.
8. Check the install: `/plugin`, then the **Installed** tab shows `sdlc-lite`.
9. Run `/sdlc-init`. Read the plan and approve it. The plan must include `pip install -e .`.
   Then run the commit command it prints, with `!` in front, or in a second shell.
10. Run `/sdlc-init` again. It must change nothing.
11. Run `/implement-feature <a feature of your choice for mypackage>`. Answer each STOP. Go on
    until the run commits on a feature branch (Gate 11).
12. Exit claude: `/exit`.
13. Exit the acceptance shell: `exit`.

**Back on the Mac.**

14. Tell the developer agent the result, and your list of README gaps. The agent runs
    `./acceptance.sh logs` and reads the evidence.
15. When the agent has the evidence, remove the container: `./acceptance.sh down`.

If you exit the shell early, the container keeps its state until `down`. Run
`./acceptance.sh shell` to go back in.

## 5. Pass criteria

The run passes when all of these are true:

1. Every step came from the README. Each gap is written down.
2. `/sdlc-init` installed the toolchain into the venv, and its second run changed nothing.
3. `/implement-feature` finished Gate 11 with one commit on a feature branch.
4. `git status` is clean. The project has no `.coverage*`, `mutants/` or `if-runlog.jsonl`.
5. Nothing was installed outside the venv.

A bug that damages the repo or the environment is a release stopper. Fix it in a patch release
(for example `0.1.1`). File any other problem against the next milestone.

## 6. How it works

`acceptance.sh` has four commands. It never does a user step (venv, login, plugin install,
`/sdlc-init`), because those steps are the test.

| Command | What it does |
|---|---|
| `up` | Builds image `sdlc-lite-acceptance` with `--pull --no-cache`, then starts the container. Stops if the container exists. |
| `shell` | Opens `bash` as `stranger` in `~/mypackage`. Starts the container if it is stopped. |
| `logs` | Copies the evidence to `acceptance-logs.tmp/` at the repo root (gitignored). |
| `down` | Removes the container and the image. Keeps `acceptance-logs.tmp/`. |

**The image** (`acceptance/Dockerfile`):
- `python:3.12-slim`, `git`, `curl` and the latest Claude Code from the official installer.
- User `stranger`, with a git identity. No venv, no dev toolchain, no plugin, no login.
- `~/mypackage`: a src-layout repo with `textstats.word_count`, two tests and one commit. The
  build runs the two tests in a throwaway venv, then deletes it. The repo has no tool config and
  no `BRIEF.md`.

**The evidence** that `logs` copies:
- `transcripts/`: the session transcripts (`~/.claude/projects/`).
- `implement-feature/`: the run folder, with the handoff files and `run-log.jsonl`.
- `versions.txt`: the Claude Code version, the installed plugins and the plugin cache.
- `python.txt`: `pip list` for each venv, the system Python and the user site.
- `git.txt`: branches, status, log, and any stray artifacts in the project.
- `claude-settings.json`, `claude-installed_plugins.json`, `claude-known_marketplaces.json`.

`logs` never copies `~/.claude.json` or the credentials file.

## 7. Constraints

- No mounts. Files go in only through the image build. Evidence comes out only through `logs`.
- No auth is passed in. The human logs in, as a stranger does.
- The Claude Code version is not pinned. A difference between versions is a finding, not noise.
- One container at a time. `up` makes a fresh one, so `down` the old one first.
- Keep the image minimal. Each thing you add can hide a step that the README must describe.

Related: #100 · [`RELEASING.md`](RELEASING.md) §4 · [`DEVCONTAINER.md`](DEVCONTAINER.md)
