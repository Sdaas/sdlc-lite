#!/usr/bin/env python3
"""verify-entry-points.py — the 8-cell entry-point contract, checked against the working tree (#57).

The contract (ADR-14, measured by hand while closing #55/#56):

  A. Explicit entry must work — the human's slash command loads SKILL.md
       1  /implement-feature             headless
       2  /sdlc-lite:implement-feature   headless
       3  /implement-feature             interactive
       4  /sdlc-lite:implement-feature   interactive
  B. Auto-trigger must never fire — the model does not start the workflow on its own
       5  natural phrasing               headless     no body injected
       6  natural phrasing               interactive  no body injected
       7  explicit "call the Skill tool" headless     Skill call made -> guard denies it
       8  explicit "call the Skill tool" interactive  Skill call made -> guard denies it
     (7-8 isolate the hook: they run against a copy whose skill `description` is neutral, so the
      prose layer does not pre-empt the call — see NEUTRAL_DESCRIPTION. A run where the model
      still makes no Skill call is INCONCLUSIVE and re-run, up to MAX_ATTEMPTS.)

Every cell runs on BOTH load paths — `--plugin-dir` and the directory marketplace — because
assuming the paths behave alike is what let #55 hide. Verdicts come from deterministic
signatures in the on-disk session transcript (never a model-judged answer, and never
`--output-format stream-json`, which omits the expanded command and the injected body).

Each cell gets a throwaway CLAUDE_CONFIG_DIR and scratch cwd under /tmp, and a fixed
`--session-id`, so exactly one transcript is in play and its path is known up front.

Runs INSIDE the dev container (it makes real model calls and needs the pinned claude):

    devcontainer exec --workspace-folder . python3 /workspaces/sdlc-lite/verify-entry-points.py
        [--interactive]      also run the 4 pty-driven interactive cells (default: headless only)
        [--plugin-src PATH]  check this plugin directory instead of the workspace's (e.g. a
                             scratch copy with a regression planted in it)
        [--keep]             keep the scratch configs/cwds for debugging

Exit 0 only when every cell that ran is green. Auth: CLAUDE_CODE_OAUTH_TOKEN or
ANTHROPIC_API_KEY from the environment, else sourced from the repo-root .env.
"""
from __future__ import annotations

import argparse
import json
import os
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent
MODEL = "sonnet"
HEADLESS_TIMEOUT = 300
INTERACTIVE_TIMEOUT = 300
# Only an INCONCLUSIVE cell is re-run: the model declined to make the Skill call (cells 7-8), so
# the guard was never exercised. GREEN and RED are final on the first attempt — a single run that
# starts the workflow is a red cell, however many others would not have.
MAX_ATTEMPTS = 4

REQUEST = "add a to_roman(n) helper"
NATURAL = ("I want to add a `to_roman(n)` helper to this python repo, "
           "built test-first with staged approvals")
EXPLICIT = "Invoke the Skill tool for sdlc-lite:implement-feature. Then reply DONE."

# Cells 7-8 prove the HOOK layer, so they must make the Skill call — but the prose layer (the
# skill `description`) is strong enough that the model refuses even a system-prompt instruction
# to (measured: 0/4 calls in an interactive marketplace session). So those cells run against a
# scratch copy of the plugin whose `description` is neutral — guard, hooks and body unchanged.
# Cells 5-6 still test the full, as-shipped stack.
NEUTRAL_DESCRIPTION = ("description: Build a Python feature through an interview-driven, "
                       "test-first workflow with staged approvals.")

# --- transcript signatures ----------------------------------------------------------
BODY = "Base directory for this skill"                      # slash/Skill injected SKILL.md
SHIM = ("already loaded above; instructions unchanged",     # a command shadowed the skill (#55)
        "conductor entry point")                             # the deleted shim's own heading
DENIAL = "workflow is explicit-entry only"                  # policy.skill_invoke_decision()
SKILL_IDS = {"implement-feature", "sdlc-lite:implement-feature"}


@dataclass(frozen=True)
class Cell:
    n: int
    typed: str       # label for the matrix
    mode: str        # "headless" | "interactive"
    prompt: str
    kind: str        # "slash" | "natural" | "explicit"
    tools: str       # --tools value: the built-in tools the session may use
    hook_only: bool = False  # run against the neutral-description copy (NEUTRAL_DESCRIPTION)


CELLS = [
    Cell(1, "/implement-feature", "headless", f"/implement-feature {REQUEST}", "slash", ""),
    Cell(2, "/sdlc-lite:implement-feature", "headless", f"/sdlc-lite:implement-feature {REQUEST}", "slash", ""),
    Cell(3, "/implement-feature", "interactive", f"/implement-feature {REQUEST}", "slash", ""),
    Cell(4, "/sdlc-lite:implement-feature", "interactive", f"/sdlc-lite:implement-feature {REQUEST}", "slash", ""),
    Cell(5, "natural phrasing", "headless", NATURAL, "natural", "Skill"),
    Cell(6, "natural phrasing", "interactive", NATURAL, "natural", "Skill"),
    Cell(7, "explicit Skill call", "headless", EXPLICIT, "explicit", "Skill", hook_only=True),
    Cell(8, "explicit Skill call", "interactive", EXPLICIT, "explicit", "Skill", hook_only=True),
]
LOAD_PATHS = ("plugin-dir", "marketplace")


# --- transcript reading ---------------------------------------------------------------

@dataclass
class Transcript:
    body: int = 0
    shim: int = 0
    skill_calls: int = 0
    denied: int = 0
    allowed: int = 0          # Skill calls for our skill that were NOT denied
    ended: bool = False       # an assistant turn ended (end_turn)
    exists: bool = False


def _texts(content) -> list[str]:
    if isinstance(content, str):
        return [content]
    out = []
    for b in content or []:
        if b.get("type") == "text":
            out.append(b.get("text", ""))
        elif b.get("type") == "tool_result":
            out.extend(_texts(b.get("content")))
    return out


def read_transcript(path: Path) -> Transcript:
    t = Transcript()
    if not path.is_file():
        return t
    t.exists = True
    calls: dict[str, bool] = {}          # tool_use_id -> is our skill
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue                      # a line mid-write while polling
        msg = rec.get("message") or {}
        content = msg.get("content")
        if rec.get("type") == "user":
            for txt in _texts(content):
                t.body += BODY in txt
                t.shim += any(s in txt for s in SHIM)
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_result" and calls.get(b.get("tool_use_id")):
                    if any(DENIAL in s for s in _texts(b.get("content"))):
                        t.denied += 1
                    else:
                        t.allowed += 1
        elif rec.get("type") == "assistant":
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_use" and b.get("name") == "Skill":
                    ours = (b.get("input") or {}).get("skill") in SKILL_IDS
                    calls[b.get("id")] = ours
                    t.skill_calls += ours
            if msg.get("stop_reason") == "end_turn":
                t.ended = True
    return t


def verdict(cell: Cell, t: Transcript) -> tuple[str, str]:
    """(GREEN|RED|INCONCLUSIVE, evidence). Pure function of the transcript signatures."""
    if not t.exists:
        return "RED", "no transcript"
    ev = f"body={t.body} shim={t.shim} skill_calls={t.skill_calls} denied={t.denied}"
    if cell.kind == "slash":
        ok = t.body >= 1 and t.shim == 0
        return ("GREEN" if ok else "RED"), ev
    if t.body or t.allowed or t.shim:
        return "RED", ev + " (workflow started without the human)"
    if cell.kind == "natural":
        return "GREEN", ev
    # explicit: the guard must have been exercised, not merely unneeded
    if t.skill_calls and t.denied == t.skill_calls:
        return "GREEN", ev
    return "INCONCLUSIVE", ev + " (no Skill call made; guard not exercised)"


# --- session setup --------------------------------------------------------------------

def make_hook_only(plugin_src: Path, root: Path) -> Path:
    """A copy of the plugin whose skill `description` no longer tells the model to refuse."""
    dst = root / "hook-only" / "sdlc-lite-plugin"
    shutil.copytree(plugin_src, dst, symlinks=True)
    skill = dst / "skills/implement-feature/SKILL.md"
    lines = skill.read_text().split("\n")
    lines = [NEUTRAL_DESCRIPTION if ln.startswith("description:") else ln for ln in lines]
    skill.write_text("\n".join(lines))
    return dst


def make_marketplace(plugin_src: Path, root: Path) -> Path:
    """The workspace IS the dev marketplace; any other plugin dir needs a wrapper around it."""
    if plugin_src == REPO / "sdlc-lite-plugin":
        return REPO
    mkt = root / f"mkt-{plugin_src.parent.name}"
    (mkt / ".claude-plugin").mkdir(parents=True)
    (mkt / "sdlc-lite").symlink_to(plugin_src)
    (mkt / ".claude-plugin/marketplace.json").write_text(json.dumps({
        "name": "sdlc-lite-dev", "owner": {"name": "verify-entry-points"},
        "plugins": [{"name": "sdlc-lite", "source": "./sdlc-lite"}],
    }))
    return mkt


def make_config(cfg: Path, cwd: Path, load_path: str, marketplace: Path) -> None:
    """A fresh config: onboarding + trust pre-accepted; the dev marketplace enabled the same
    way the container's seeded settings.json does it (ADR-13) — or nothing, for --plugin-dir."""
    cfg.mkdir(parents=True)
    (cfg / ".claude.json").write_text(json.dumps({
        "hasCompletedOnboarding": True, "theme": "dark",
        "projects": {str(cwd): {"hasTrustDialogAccepted": True}},
    }))
    settings: dict = {"model": MODEL}
    if load_path == "marketplace":
        settings["extraKnownMarketplaces"] = {
            "sdlc-lite-dev": {"source": {"source": "directory", "path": str(marketplace)}}}
        settings["enabledPlugins"] = {"sdlc-lite@sdlc-lite-dev": True}
    (cfg / "settings.json").write_text(json.dumps(settings))


def argv(cell: Cell, load_path: str, plugin_src: Path, sid: str) -> list[str]:
    a = ["claude"]
    if cell.mode == "headless":
        a += ["-p", cell.prompt]
    a += ["--model", MODEL, "--session-id", sid, "--tools", cell.tools]
    if load_path == "plugin-dir":
        a += ["--plugin-dir", str(plugin_src)]
    return a


def transcript_path(cfg: Path, sid: str) -> Path:
    hits = list((cfg / "projects").glob(f"*/{sid}.jsonl"))
    return hits[0] if hits else cfg / "projects" / "missing" / f"{sid}.jsonl"


def run_headless(cmd: list[str], cwd: Path, env: dict) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=HEADLESS_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        pass                              # the transcript is the verdict either way


def run_interactive(cmd: list[str], cwd: Path, env: dict, prompt: str, cfg: Path, sid: str) -> None:
    """Drive a real TUI session through a pty: wait for it to settle, type the prompt like a
    human, then poll the transcript until the turn ends (or a signature decides it early)."""
    pid, fd = pty.fork()
    if pid == 0:                          # child
        os.chdir(cwd)
        os.execvpe(cmd[0], cmd, env)
    screen = b""

    def pump(secs: float) -> None:
        nonlocal screen
        end = time.time() + secs
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.2)
            if r:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    return
                screen = (screen + chunk)[-20000:]
                if b"trust" in chunk.lower() and b"folder" in chunk.lower():
                    os.write(fd, b"\r")   # folder-trust dialog, should the seed be ignored

    try:
        pump(8)                           # let the TUI boot and settle
        for ch in prompt:                 # type it, so slash autocomplete sees keystrokes
            os.write(fd, ch.encode())
            pump(0.02)
        pump(1.5)
        os.write(fd, b"\r")
        deadline = time.time() + INTERACTIVE_TIMEOUT
        tpath = None
        while time.time() < deadline:
            pump(2)
            tpath = transcript_path(cfg, sid)
            t = read_transcript(tpath)
            if t.ended or t.body or t.shim:
                pump(2)                   # let the final records flush
                break
    finally:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        os.close(fd)


# --- main -----------------------------------------------------------------------------

def auth_env() -> dict:
    env = dict(os.environ)
    if not (env.get("CLAUDE_CODE_OAUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")):
        dotenv = REPO / ".env"
        if dotenv.is_file():
            for line in dotenv.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env.setdefault(k.removeprefix("export ").strip(), v.strip().strip("\"'"))
    if not (env.get("CLAUDE_CODE_OAUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")):
        sys.exit("no CLAUDE_CODE_OAUTH_TOKEN / ANTHROPIC_API_KEY in the environment or .env")
    return env


def run_cell(cell: Cell, lp: str, attempt: int, root: Path, env: dict,
             plugin_src: Path, marketplace: Path) -> tuple[str, str]:
    """One fresh session for one cell on one load path; the verdict is read off its transcript."""
    sid = str(uuid.uuid4())
    base = root / f"c{cell.n}-{lp}-a{attempt}"
    cfg, cwd = base / "cfg", base / "wd"
    cwd.mkdir(parents=True)
    make_config(cfg, cwd, lp, marketplace)
    cenv = {**env, "CLAUDE_CONFIG_DIR": str(cfg)}
    cmd = argv(cell, lp, plugin_src, sid)
    print(f"  running cell {cell.n} ({cell.mode}, {lp}) attempt {attempt} …", flush=True)
    if cell.mode == "headless":
        run_headless(cmd, cwd, cenv)
    else:
        run_interactive(cmd, cwd, cenv, cell.prompt, cfg, sid)
    return verdict(cell, read_transcript(transcript_path(cfg, sid)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--interactive", action="store_true", help="also run the 4 pty cells")
    ap.add_argument("--plugin-src", type=Path, default=REPO / "sdlc-lite-plugin")
    ap.add_argument("--keep", action="store_true", help="keep scratch dirs")
    ap.add_argument("--cells", type=lambda s: {int(x) for x in s.split(",")},
                    help="run only these cell numbers, e.g. 7,8 (for debugging)")
    args = ap.parse_args()

    if not shutil.which("claude"):
        sys.exit("claude not on PATH — run this inside the dev container (see dev-docs/DEVCONTAINER.md)")
    plugin_src = args.plugin_src.resolve()
    env = auth_env()
    root = Path(tempfile.mkdtemp(prefix="vep-"))
    hook_only = make_hook_only(plugin_src, root)
    sources = {False: (plugin_src, make_marketplace(plugin_src, root)),
               True: (hook_only, make_marketplace(hook_only, root))}
    cells = [c for c in CELLS if (args.interactive or c.mode == "headless")
             and (not args.cells or c.n in args.cells)]
    ver = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=False).stdout.strip()
    print(f"entry-point contract · claude {ver} · model {MODEL} · plugin {plugin_src}")

    rows = []
    for cell in cells:
        for lp in LOAD_PATHS:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                v, ev = run_cell(cell, lp, attempt, root, env, *sources[cell.hook_only])
                if v != "INCONCLUSIVE":
                    break
            rows.append((cell, lp, v, ev + (f" [attempt {attempt}]" if attempt > 1 else "")))

    print()
    print(f"{'#':>2}  {'typed':<30} {'session':<12} {'load path':<12} {'verdict':<13} evidence")
    for cell, lp, v, ev in rows:
        mark = "✅" if v == "GREEN" else "❌"
        print(f"{cell.n:>2}  {cell.typed:<30} {cell.mode:<12} {lp:<12} {mark} {v:<10} {ev}")
    red = [r for r in rows if r[2] != "GREEN"]
    print(f"\n{len(rows) - len(red)}/{len(rows)} green"
          + ("" if args.interactive else " (headless only; --interactive adds cells 3,4,6,8)"))
    if args.keep:
        print(f"scratch kept: {root}")
    else:
        shutil.rmtree(root, ignore_errors=True)
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
