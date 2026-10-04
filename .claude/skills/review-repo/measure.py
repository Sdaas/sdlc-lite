"""measure.py — proves the full-repo review ran every agent on claude-opus-5-5 at effort high.

Why it exists: an inline `model: opus` dispatch of the review agents ran at effort `medium`.
Effort is frontmatter-only (no dispatch lever), so it can only be audited after the fact. This
script reads the session transcripts and checks them against FIXED required values (not the
pins alone, so a drifted pin cannot pass). Reuses agentdefs.load_pins,
analyzer.transcript.parse_subagents and analyzer.receipt.model_matches.

Phase `pins` (pre-flight) checks only the agent files and writes nothing. Otherwise it
prepends a measurement block to the report file (creates it if absent; a VALID `areas` phase
only prints, the consolidator creates the report next), prints it, and exits
0 if VALID, 1 if INVALID (argparse exits 2 on bad arguments). Never raises on bad input: any error is INVALID with the reason.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "sdlc-lite-plugin"))

import agentdefs  # noqa: E402
from analyzer.receipt import model_matches  # noqa: E402
from analyzer.transcript import parse_subagents  # noqa: E402

REQUIRED_MODEL = "claude-opus-5-5"
REQUIRED_EFFORT = "high"
AREA = "repo-area-reviewer"
CONSOLIDATOR = "repo-review-consolidator"
AGENTS = (AREA, CONSOLIDATOR)
EXPECTED = {
    "pins": None,  # pre-flight: the agent files only, before any agent is spawned
    "areas": {AREA: 9, CONSOLIDATOR: 0},
    "final": {AREA: 9, CONSOLIDATOR: 1},
}
INVALID_HEAD = "# INVALID — not Opus 5.5 / high"


def _find_main(projects_dir: Path, session: str) -> Path | None:
    hits = sorted(projects_dir.glob(f"*/{session}.jsonl"))
    return hits[0] if hits else None


def _measure(args) -> tuple[list[str], list[str], list[str]]:
    """Return (reasons, pin_lines, table_rows)."""
    reasons: list[str] = []
    pin_lines: list[str] = []
    rows: list[str] = []
    expected = EXPECTED[args.phase]

    pins = agentdefs.load_pins(str(args.agents_root))
    for name in AGENTS:
        pin = pins.get(name)
        if pin is None:
            reasons.append(f"agent file .claude/agents/{name}.md is missing")
            pin_lines.append(f"- pin .claude/agents/{name}.md: missing — FAIL")
            continue
        ok = pin.model == REQUIRED_MODEL and pin.effort == REQUIRED_EFFORT
        if not ok:
            reasons.append(f"pin of {name} is model {pin.model}, effort {pin.effort}; "
                           f"required {REQUIRED_MODEL} / {REQUIRED_EFFORT}")
        pin_lines.append(f"- pin .claude/agents/{name}.md: model {pin.model}, "
                         f"effort {pin.effort} — {'PASS' if ok else 'FAIL'}")

    if expected is None:
        return reasons, pin_lines, rows

    main = _find_main(args.projects_dir, args.session)
    if main is None:
        reasons.append(f"main transcript for session {args.session} not found under "
                       f"{args.projects_dir}")
        return reasons, pin_lines, rows

    subs = parse_subagents(main)
    for name, want in expected.items():
        mine = [s for s in subs if s.agent_label == name]
        if len(mine) != want:
            reasons.append(f"{name}: expected {want} agents, found {len(mine)}")
        for s in mine:
            bad: list[str] = []
            models = sorted(s.by_model)
            for m in models:
                if not model_matches(REQUIRED_MODEL, m):
                    bad.append(f"{name} ran model {m}; required {REQUIRED_MODEL}")
            for e in s.efforts:
                if e != REQUIRED_EFFORT:
                    bad.append(f"{name} ran effort {e}; required {REQUIRED_EFFORT}")
            known = sum(s.efforts.values())
            unknown = s.total_turns - known
            if unknown > 0:
                bad.append(f"{name} has {unknown} turn(s) with UNKNOWN effort")
            reasons.extend(bad)
            eff = [f"{e}×{c}" for e, c in sorted(s.efforts.items())]
            if unknown > 0:
                eff.append(f"UNKNOWN×{unknown}")
            rows.append(f"| {s.agent_label} | {', '.join(models)} | {', '.join(eff)} | "
                        f"{'FAIL' if bad else 'PASS'} |")
    return reasons, pin_lines, rows


def _block(args, reasons, pin_lines, rows) -> str:
    if reasons:
        head = [INVALID_HEAD, "", "Do not triage this report.", ""]
        head += [f"- {r}" for r in reasons]
    elif EXPECTED[args.phase] is None:
        head = [f"Measured: VALID — pins {REQUIRED_MODEL} / {REQUIRED_EFFORT} (phase pins)"]
    else:
        n = sum(EXPECTED[args.phase].values())
        head = [f"Measured: VALID — {n}/{n} agents {REQUIRED_MODEL} / {REQUIRED_EFFORT} "
                f"(phase {args.phase}, session {args.session})"]
    out = head + [""] + pin_lines
    if EXPECTED[args.phase] is None:
        return "\n".join(out) + "\n"
    out += ["", "| agent | models | efforts | verdict |", "|---|---|---|---|"] + rows
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--session", required=True)
    p.add_argument("--phase", required=True, choices=sorted(EXPECTED))
    p.add_argument("--report", required=True, type=Path)
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    p.add_argument("--projects-dir", type=Path,
                   default=Path(cfg) / "projects" if cfg else Path.home() / ".claude" / "projects")
    p.add_argument("--agents-root", type=Path, default=REPO / ".claude")
    args = p.parse_args(argv)

    try:
        reasons, pin_lines, rows = _measure(args)
    except Exception as exc:  # never raise on bad input: INVALID with the reason
        reasons, pin_lines, rows = [f"measurement failed: {exc!r}"], [], []
    block = _block(args, reasons, pin_lines, rows)
    if args.phase == "pins" or (args.phase == "areas" and not reasons):
        # pins: nothing reviewed yet; a VALID areas phase: the consolidator creates the report
        print(block, end="")
        return 1 if reasons else 0

    try:
        old = args.report.read_text(encoding="utf-8") if args.report.exists() else ""
        text = block + (f"\n---\n\n{old}" if old else "")
        args.report.write_text(text, encoding="utf-8")
    except OSError as exc:
        reasons.append(f"could not write report {args.report}: {exc}")
        block = _block(args, reasons, pin_lines, rows)
    print(block, end="")
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
