"""Run-log reader — the LOAD-BEARING half of the analyzer.

The run-log (`run-log.jsonl`) is HETEROGENEOUS — two record shapes interleaved in one file:

  1. GUARD AUDIT records (one per tool call, written by hooks/scripts/guard.py):

    {"ts": "<UTC ISO>", "agent_type": "<str>", "agent_id": "<str>",
     "tool": "Read|Bash|Grep|Glob|Edit|Write|...", "target": "<path/cmd>",
     "guard_decision": "allow|deny"}   # the guard's OWN pre-execution decision (#31 R4);
                                       # absent on legacy lines -> counted as unknown

  2. CONDUCTOR ORCHESTRATION records (one per gate, written by the SKILL conductor):

    {"gate": "<name>", "mode": "[C]|[I]", "agent": "<role>", "inbox":[...],
     "outbox":[...], "result": "<str>", "ts": "<UTC ISO>"}   # the orchestration story

Discriminated on read by shape (a `gate` key with no `tool` = orchestration). Orchestration
records are counted separately (`orchestration_entries`) and EXCLUDED from tool-call
aggregation and the isolation buckets — before #22 leg B they were mis-parsed as conductor
"tool calls" with an empty tool name (M-06), inflating counts and printing a garbage `×N`
cell. Their timestamps still bound the run window (they are part of the run). The conductor
no longer writes a guessed `model`/`effort` into these records for `[I]` gates (m-09): the
receipt's requested model/effort come from the agent-def pins (agentdefs.py), not a guess.

From this it derives, WITHOUT ever touching the transcript:
  - per-agent activity (tool-call counts, files read / written)
  - the run's time window (min/max ts) — the single value handed to the
    transcript layer for correlation (a value, never code or shared state)
  - isolation-compliance verdicts — the proof that the guard's invariants held

IMPORTANT — the audit records ATTEMPTS, not outcomes. guard.py logs EVERY call
(allowed or denied), stamping its own pre-execution decision as `guard_decision`.
So a forbidden entry appearing here means an agent *tried* — the guard blocks it
at runtime (guard_decision="deny"), and this layer *detects* the attempt after the
fact. A denied call has no transcript effect, so `guard_decision` is the only place
a denial is visible. Preventive (guard) + detective (analyzer) together.

The isolation verdicts are adjudicated by the SAME authority the guard uses —
`policy.decide()` and the shared predicates in `policy.py` (the #30 SSOT). This
module no longer keeps its own copy of `looks_secret` / `is_test_path` / the
reviewer write-confinement test / the Bash parsing: those lived here under a
"KEEP IN SYNC" comment and drifted from the guard. Importing the one definition
is the whole point of the seam — the preventive and detective legs can no longer
disagree. The detective inherits the guard's Bash best-effort blind spot by design;
the transcript-based auditor (#30 R3) is the authoritative backstop.

This module has ZERO knowledge of transcript.py.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field

import policy

from ._util import parse_ts

# Mirror guard.py's tool classification (keep in sync with hooks/scripts/guard.py).
READISH = {"Read", "Bash", "Grep", "Glob"}
WRITEISH = {"Write", "Edit", "NotebookEdit"}

# The conductor logs with an empty agent_type; give it a readable name.
CONDUCTOR = "conductor"

# The subagent gates we expect a full run to exercise (namespaced, per SKILL.md).
EXPECTED_AGENTS = (
    "sdlc-lite:test-writer",
    "sdlc-lite:test-reviewer",
    "sdlc-lite:implementer",
    "sdlc-lite:verifier",
    "sdlc-lite:code-reviewer",
)


# --- data model ------------------------------------------------------------
@dataclass
class AgentActivity:
    agent_type: str
    total_calls: int = 0
    tool_counts: dict[str, int] = field(default_factory=dict)
    reads: list[str] = field(default_factory=list)   # targets of read-ish calls
    writes: list[str] = field(default_factory=list)   # targets of write-ish calls
    # guard's own pre-execution decision per call (#31 R4). `decision_unknown` counts
    # legacy lines written before guard_decision existed — reported, never guessed.
    grants: int = 0
    denies: int = 0
    decision_unknown: int = 0
    # (tool, target) for each read-ish call — the tool is needed to mirror guard.py's
    # tool-split secret detection faithfully (a Bash target is a command, not a path).
    read_calls: list[tuple[str, str]] = field(default_factory=list)
    # (tool, target) for each write-ish call — the tool distinguishes a single-target
    # Write/Edit (target IS a path) from a Bash write (target is a command whose write
    # redirect/copy destinations must be extracted before the policy can adjudicate them).
    write_calls: list[tuple[str, str]] = field(default_factory=list)

    @property
    def label(self) -> str:
        """Human-friendly name (strip the plugin namespace; name the conductor)."""
        if not self.agent_type:
            return CONDUCTOR
        return self.agent_type.split(":", 1)[-1]


@dataclass
class IsolationCheck:
    name: str
    passed: bool
    detail: str
    evidence: list[str] = field(default_factory=list)  # offending log lines


@dataclass
class RunLogAnalysis:
    path: str
    total_entries: int          # GUARD AUDIT records only (one per tool call)
    malformed_lines: int
    window_start: _dt.datetime | None
    window_end: _dt.datetime | None
    agents: dict[str, AgentActivity]
    checks: list[IsolationCheck]
    orchestration_entries: int = 0   # CONDUCTOR gate records (excluded from tool counts, M-06)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)


# --- parsing ---------------------------------------------------------------
def _handoff_dir(runlog_path: str) -> str:
    """The run's real handoff dir: the directory holding the run-log (by convention
    <artifact_dir>/handoff/run-log.jsonl). Anchors the reviewer write-confinement check,
    exactly as guard.py's _handoff_dir() anchors the preventive side — same value, same
    seam, so the two legs agree on what counts as 'inside the outbox'.

    **Must be absolute.** The guard logs write-targets as absolute paths (Write/Edit tool
    targets and resolved Bash redirects are always absolute in practice), and
    `policy.is_within()` does a plain string-prefix comparison — no implicit normalization
    against cwd. A relative `runlog_path` (e.g. `--workdir` passed as a relative path, which
    `analyze_run.py` does not itself require to be absolute) would silently produce a
    relative handoff_dir that can never match those absolute targets, misclassifying every
    legitimate handoff-outbox write as a policy violation. `abspath()` makes this correct
    regardless of what the caller passes."""
    return os.path.abspath(os.path.normpath(os.path.dirname(runlog_path)))


def parse_runlog(path: str) -> RunLogAnalysis:
    """Read if-runlog.jsonl and compute per-agent activity + isolation verdicts.

    Robust to malformed lines (skipped and counted), mirroring guard.py's own
    "never fail on bad input" stance.
    """
    agents: dict[str, AgentActivity] = {}
    times: list[_dt.datetime] = []
    total = 0
    orchestration = 0
    malformed = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(rec, dict):
                malformed += 1
                continue

            # M-06: the run-log is heterogeneous. A conductor ORCHESTRATION record (a `gate`
            # key, no `tool`) is the run's story, NOT a tool call — count it apart and skip the
            # tool aggregation, so it never becomes a phantom empty-tool "call" in the
            # conductor bucket. Its timestamp still bounds the run window (below).
            if "gate" in rec and "tool" not in rec:
                orchestration += 1
                ts = parse_ts(str(rec.get("ts") or ""))
                if ts is not None:
                    times.append(ts)
                continue

            total += 1
            atype = str(rec.get("agent_type") or "")
            tool = str(rec.get("tool") or "")
            target = str(rec.get("target") or "")

            act = agents.get(atype)
            if act is None:
                act = agents[atype] = AgentActivity(agent_type=atype)
            act.total_calls += 1
            act.tool_counts[tool] = act.tool_counts.get(tool, 0) + 1
            if tool in READISH:
                act.reads.append(target)
                act.read_calls.append((tool, target))
            elif tool in WRITEISH:
                act.writes.append(target)
                act.write_calls.append((tool, target))

            # #31 R4: the guard's own decision. Absent (legacy line) => unknown, not a guess.
            decision = rec.get("guard_decision")
            if decision == "allow":
                act.grants += 1
            elif decision == "deny":
                act.denies += 1
            else:
                act.decision_unknown += 1

            ts = parse_ts(str(rec.get("ts") or ""))
            if ts is not None:
                times.append(ts)

    checks = _run_isolation_checks(agents, _handoff_dir(path))
    return RunLogAnalysis(
        path=path,
        total_entries=total,
        malformed_lines=malformed,
        window_start=min(times) if times else None,
        window_end=max(times) if times else None,
        agents=agents,
        checks=checks,
        orchestration_entries=orchestration,
    )


def _denied_reads(act: AgentActivity, handoff_dir: str, rule: str) -> list[str]:
    """Read targets of `act` that policy.decide() denies with the given rule slug. Bash
    read targets are command strings; the design-internal / draft READ invariants are
    substring-visible in the command, so decide() on the raw command is faithful for those
    rules (secrets are handled separately via the tool-split looks_secret, below)."""
    hits: list[str] = []
    for _tool, t in act.read_calls:
        if policy.decide(act.agent_type, policy.READ, t, handoff_dir).rule == rule:
            hits.append(t)
    return hits


def _denied_writes(act: AgentActivity, handoff_dir: str, rule: str) -> list[str]:
    """Write targets of `act` that policy.decide() denies with the given rule slug. A
    single-target Write/Edit names one path; a Bash write hides its destinations inside a
    command, so those are extracted (policy.bash_write_targets — best-effort, the guard's
    same blind spot) before each is adjudicated."""
    hits: list[str] = []
    for tool, t in act.write_calls:
        targets = policy.bash_write_targets(t) if tool == "Bash" else [t]
        for w in targets:
            if policy.decide(act.agent_type, policy.WRITE, w, handoff_dir).rule == rule:
                hits.append(w)
    # A confined reviewer can also smuggle a write through a Bash *read-ish* call (its Bash
    # calls are logged as reads); the guard extracts redirect targets from those too.
    for tool, t in act.read_calls:
        if tool != "Bash":
            continue
        for w in policy.bash_write_targets(t):
            if policy.decide(act.agent_type, policy.WRITE, w, handoff_dir).rule == rule:
                hits.append(w)
    return hits


def _run_isolation_checks(agents: dict[str, AgentActivity],
                          handoff_dir: str) -> list[IsolationCheck]:
    """The four detective verdicts, derived purely from per-agent activity + the policy
    SSOT. Each verdict asks policy.decide() (or, for secrets, the tool-split predicate) the
    SAME question the guard asked at runtime — so the report can never pass a run the guard
    would have blocked, nor fail one it correctly allowed."""
    checks: list[IsolationCheck] = []

    # 1. test-writer must not have attempted to read the internal design (algorithm-blind).
    tw_hits = [
        t for a in agents.values() if "test-writer" in a.agent_type
        for t in _denied_reads(a, handoff_dir, "algorithm-blind")
    ]
    checks.append(IsolationCheck(
        name="test-writer stayed algorithm-blind",
        passed=not tw_hits,
        detail=("no attempt to read design-internal.md"
                if not tw_hits else
                f"{len(tw_hits)} attempt(s) to read design-internal.md (guard blocks at runtime)"),
        evidence=tw_hits,
    ))

    # 2. implementer must not have attempted to write/edit a test file (test-integrity).
    impl_hits = [
        t for a in agents.values() if "implementer" in a.agent_type
        for t in _denied_writes(a, handoff_dir, "test-integrity")
    ]
    checks.append(IsolationCheck(
        name="implementer did not touch tests",
        passed=not impl_hits,
        detail=("no attempt to write/edit test files"
                if not impl_hits else
                f"{len(impl_hits)} attempt(s) to write a test file (guard blocks at runtime)"),
        evidence=impl_hits,
    ))

    # 3. no agent must have attempted to read secrets/.env. Uses the tool-split predicate
    #    directly (a Bash target is a command, so scan path-like tokens — never the raw
    #    command body, #16; decide()'s path-form secret rule is for resolved paths only).
    secret_hits = [
        f"{a.label}: {t}" for a in agents.values()
        for (tool, t) in a.read_calls if policy.looks_secret(tool, t)
    ]
    checks.append(IsolationCheck(
        name="no secret/.env access by any agent",
        passed=not secret_hits,
        detail=("no attempt to read secrets/.env"
                if not secret_hits else
                f"{len(secret_hits)} attempt(s) to read secrets/.env (guard blocks at runtime)"),
        evidence=secret_hits,
    ))

    # 3c. the read-only critics (test-reviewer + verifier + code-reviewer, #29) must not have
    #     written into the product tree. Their Write/Edit targets and any Bash write-redirect
    #     are checked against their sanctioned outputs (the run's ACTUAL handoff outbox +
    #     scratch) — the ANCHORED policy rule, not a loose "/handoff/" substring.
    reviewer_hits = [
        f"{a.label}: {t}" for a in agents.values()
        if policy.role_of(a.agent_type) in ("test-reviewer", "verifier", "code-reviewer")
        for t in _denied_writes(a, handoff_dir, "write-confinement")
    ]
    checks.append(IsolationCheck(
        name="read-only critics stayed out of the product tree",
        passed=not reviewer_hits,
        detail=("no product-tree writes by the read-only critics"
                if not reviewer_hits else
                f"{len(reviewer_hits)} product-tree write(s) by a read-only critic "
                "(guard blocks at runtime)"),
        evidence=reviewer_hits,
    ))

    # 4. distinct expected agents actually ran (proves isolation, not just intent)
    seen = {a.agent_type for a in agents.values() if a.agent_type}
    missing = [e for e in EXPECTED_AGENTS if e not in seen]
    # Informational, not a hard failure: a partial/aborted run legitimately lacks
    # later gates. We report presence but only fail if NO subagent ran at all.
    checks.append(IsolationCheck(
        name="distinct subagents observed",
        passed=bool(seen),
        detail=(f"{len(seen)} subagent type(s) ran"
                + (f"; not yet seen: {', '.join(m.split(':', 1)[-1] for m in missing)}"
                   if missing else " (all expected gates present)")),
        evidence=sorted(seen),
    ))

    return checks
