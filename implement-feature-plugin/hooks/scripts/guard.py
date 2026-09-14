#!/usr/bin/env python3
"""PreToolUse guard hook for /implement-feature.

Does two jobs on every Read/Bash/Grep/Glob/Edit/Write/NotebookEdit (conductor AND every
subagent): AUDIT (append one JSONL line per tool call) and ENFORCE (deny unauthorized
access). The deny decision is computed FIRST so the audit line can record it truthfully;
the audit still logs every call regardless of the decision.

  1. AUDIT  — append one JSONL line per tool call (agent_id/agent_type/tool/target +
     `guard_decision: allow|deny`, the guard's own pre-execution decision — #31 R4).
  2. ENFORCE — the allow/deny rules now live in ONE place: `policy.py` (the #30 SSOT that
     the analyzer's detective leg also imports). This hook is the tool-aware, real-time,
     best-effort-for-Bash CALLER of that policy:
       - single-target tools (Read/Grep/Glob/Edit/Write/NotebookEdit) name one inspectable
         path -> `policy.decide()` on it is precise;
       - Bash is best-effort: the guard extracts the write-redirect targets and scans
         path-like tokens, then applies the same policy. It cannot see the full set of files
         an arbitrary `python -c …` or pipeline touches (documented limitation — the
         transcript-based auditor in analyzer/ is the authoritative backstop).
     Two enforcement mechanics stay here because they need I/O the pure policy must not do:
     the secret DIRECTORY scan (a recursive search over a dir that merely CONTAINS a secret
     file) and the R6 wildcard-ban.
  3. MODEL ENFORCE (#22 (a)) — on a Task/Agent dispatch the hook reads the target subagent's
     agent-def `model:` pin (via agentdefs.py) and DENIES a dispatch that names no model.
     !!! BEING REVERTED (#36): its premise ("frontmatter pin silently droppable") is false and
     it breaks the dated reviewer pins — see the block comment on _dispatch_deny_reason below.
     Effort has no inline dispatch lever on this platform, so it is audited (analyzer), never
     enforced here (this half stands).

Reads the hook JSON on stdin. To DENY: print a hookSpecificOutput deny decision and
exit 2. To ALLOW: exit 0.

Run-log resolution (hooks are separate processes and do NOT inherit the conductor's
exported env, hence the pointer file rather than an env var):
  1. $IF_RUNLOG (explicit override), else
  2. the pointer file $CLAUDE_PROJECT_DIR/.implement-feature/.active-run — its contents
     are the active <artifact_dir>; the run-log is <artifact_dir>/handoff/run-log.jsonl, else
  3. today's fallback $CLAUDE_PROJECT_DIR/if-runlog.jsonl, else
  4. /tmp/if-runlog.jsonl.
"""
import json, os, sys, datetime

# The guard runs as a standalone script (`python guard.py`), so sys.path[0] is this
# script's dir, not the plugin root where policy.py lives. Add the plugin root
# (hooks/scripts -> hooks -> <plugin root>) so `import policy` resolves — the ONE home
# for the isolation rules, shared with the analyzer (#30 R1).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import agentdefs  # noqa: E402
import policy  # noqa: E402

_DENY_PREFIX = "Blocked by implement-feature guard: "


def _active_run_runlog():
    """Resolve the run-log from the .active-run pointer file, if present/usable."""
    proj = os.environ.get("CLAUDE_PROJECT_DIR")
    if not proj:
        return None
    pointer = os.path.join(proj, ".implement-feature", ".active-run")
    try:
        workdir = open(pointer, encoding="utf-8").read().strip()
    except OSError:
        return None
    if not workdir:
        return None
    return os.path.join(workdir, "handoff", "run-log.jsonl")


def runlog_path():
    return (os.environ.get("IF_RUNLOG")
            or _active_run_runlog()
            or (os.path.join(os.environ["CLAUDE_PROJECT_DIR"], "if-runlog.jsonl")
                if os.environ.get("CLAUDE_PROJECT_DIR") else None)
            or "/tmp/if-runlog.jsonl")


def _handoff_dir() -> str:
    """The run's real handoff dir: the directory containing run-log.jsonl (by convention
    <artifact_dir>/handoff/run-log.jsonl — see runlog_path()). Anchors write-confinement."""
    return os.path.normpath(os.path.dirname(runlog_path()))


# --- secret DIRECTORY scan (guard-only I/O; the policy stays pure) ----------
# #m-05: a direct open of .env is caught by policy.is_secret_path. But a recursive/broad
# read over a DIRECTORY that merely CONTAINS a secret file (`grep -r … /repo`, a `Grep`
# call scoped to a directory) returns matching secret lines without the target itself ever
# being a secret path. Walk the directory (bounded) and look for a secret-named file.
def _dir_contains_secret(path: str, max_files: int = 5000) -> bool:
    if not path or not os.path.isdir(path):
        return False
    seen = 0
    for _root, _dirs, files in os.walk(path):
        for f in files:
            seen += 1
            if seen > max_files:
                return False  # bail out on huge trees rather than hang the hook
            if policy.is_secret_component(f.lower()):
                return True
    return False


_RECURSIVE_SEARCH_TOOLS = {"grep": "flag", "rg": "always", "ag": "always",
                            "ack": "always", "find": "always"}


def _bash_secret_dir_targets(command: str) -> list[str]:
    """Best-effort (#m-05): directory arguments to a recursive-search-style Bash command,
    e.g. `grep -r … /repo`. Only fires for known recursive tools/flags."""
    toks = policy.bash_tokens(command)
    if not toks:
        return []
    prog = os.path.basename(toks[0])
    mode = _RECURSIVE_SEARCH_TOOLS.get(prog)
    if mode is None:
        return []
    if mode == "flag":
        recursive = any(t.startswith("-") and not t.startswith("--") and "r" in t[1:]
                         for t in toks[1:]) or "--recursive" in toks[1:]
        if not recursive:
            return []
    return [t for t in toks[1:] if not t.startswith("-") and os.path.isdir(t)]


def _deny_reason(tool: str, ti: dict, agent_type: str, target: str) -> str | None:
    """The guard's pre-execution decision, as a deny reason (or None to allow).

    Pure w.r.t. process state (no exit) so main() can learn the decision BEFORE writing the
    audit line — the run-log then records `guard_decision` truthfully (#31 R4). The
    allow/deny logic is delegated to policy.decide(); this function is the tool-aware
    extraction that turns a tool call into the (access, path) probes decide() adjudicates,
    plus the two I/O-bearing mechanics (secret dir-scan) that can't live in the pure policy."""
    # #22 (a): a Task/Agent dispatch is model-enforced, not file-access-checked.
    if tool in ("Task", "Agent"):
        return _dispatch_deny_reason(ti)

    handoff = _handoff_dir()

    if tool == "Bash":
        return _bash_deny_reason(agent_type, target, handoff)

    # Single-target tools: one inspectable path -> precise policy decision.
    #   read side:  Read/Grep/Glob, plus Edit (which reads the file to diff).
    #   write side: Write/NotebookEdit, plus Edit.
    if tool in ("Read", "Grep", "Glob") or tool == "Edit":
        d = policy.decide(agent_type, policy.READ, target, handoff)
        if not d.allowed:
            return _DENY_PREFIX + d.reason
        # secret DIRECTORY scan for a Grep scoped to a directory (I/O — see above).
        if tool == "Grep" and _dir_contains_secret(str(ti.get("path") or "")):
            return (_DENY_PREFIX + "this directory contains a secrets/.env file — a "
                    "directory-scoped search would surface its contents.")
    if tool in ("Write", "NotebookEdit") or tool == "Edit":
        d = policy.decide(agent_type, policy.WRITE, target, handoff)
        if not d.allowed:
            return _DENY_PREFIX + d.reason
    return None


# --- #22 (a): model enforcement on a Task/Agent dispatch --------------------
# !!! BEING REVERTED — see #36 and design/model-pinning-findings.md §7. !!!
# This implements the Thomas-Witt "deny-if-unnamed" technique on the PREMISE that an agent-def
# `model:` pin is rank-2 (frontmatter, "silently droppable if the dispatch omits a model") and so
# must be promoted to rank-1 by naming it per-invocation. THAT PREMISE IS FALSE on this platform:
# a bare-dispatch frontmatter pin IS honored (proven across four real sessions + a 2026-09-14
# re-probe). Worse, this rule BREAKS the dated reviewer pins: the inline `model` slot is enum-only
# {sonnet,opus,haiku,fable}, so a forced inline name of a `claude-opus-4-8` reviewer can only be the
# `opus` alias, which (rank-1) OVERRIDES the dated frontmatter pin -> the reviewer runs
# `claude-opus-5`. The #36 fix is the inverse (dispatch pinned gates bare); this function will be
# removed/inverted then. Left in place for now (behavior unchanged this commit).
# Contract (M-08, current): pinned + no model -> deny; ANY explicit model -> allow (a *wrong* named
# model is caught by the transcript-based receipt as a pin/actual FAIL); unpinned -> allow;
# unparseable -> fail open.
# Effort has NO inline dispatch lever on this platform (verified 2026-09), so it cannot be
# enforced here — only audited by the analyzer. See agentdefs.py / the developer-guide ADR-12.
def _dispatch_deny_reason(ti: dict) -> str | None:
    """Deny a pinned-model dispatch that names no model; else allow. Fail open on anything
    unexpected (never break a dispatch we can't confidently adjudicate)."""
    try:
        subagent_type = str(ti.get("subagent_type") or "")
        if not subagent_type:
            return None  # not a named-agent dispatch we model -> allow
        pin = agentdefs.pin_for(subagent_type)
        if not (pin and pin.model):
            return None  # no model pin for this agent -> nothing to enforce
        explicit = str(ti.get("model") or "").strip()
        if explicit:
            return None  # a model was named (rank-1) -> allow; mismatch is the receipt's job
        return (_DENY_PREFIX + f"'{subagent_type}' pins model '{pin.model}' but this dispatch "
                f"named no model — the frontmatter pin is silently droppable. Re-dispatch with "
                f"the model named explicitly (model: \"{pin.model}\") so the pin is honored.")
    except Exception:
        return None  # fail open: an unparseable dispatch payload is never blocked


def _bash_deny_reason(agent_type: str, command: str, handoff: str) -> str | None:
    """Best-effort Bash enforcement. The Bash target is the whole command string, so this
    can't just hand a path to decide(): it (a) scans path-like tokens for secrets, (b)
    substring-tests the command for the design-internal / draft READ invariants, and (c)
    resolves write-redirect targets and adjudicates each via decide(WRITE)."""
    # (a) secret reads — token scan (never the raw command body, #16) + directory scan.
    if policy.looks_secret("Bash", command):
        return _DENY_PREFIX + "reading secrets/.env is not allowed."
    for d in _bash_secret_dir_targets(command):
        if _dir_contains_secret(d):
            return (_DENY_PREFIX + f"recursive search of {d} would surface a "
                    "secrets/.env file's contents.")

    # (b) READ invariants that the command string exposes literally. A wildcard read that
    #     could resolve to design-internal is handled by the R6 ban (added next commit).
    if "test-writer" in agent_type and policy.is_design_internal(command):
        return (_DENY_PREFIX + "the test-writer is algorithm-blind and must not read "
                "design-internal.md.")
    # R6 wildcard-ban: an algorithm-blind agent may not run an UNRESOLVABLE wildcard read
    # over handoff/ — the glob (`cat handoff/*.md`) could expand to design-internal.md, and
    # the literal-substring rule above can't see it. Ban the glob; read files by exact name.
    if policy.is_algorithm_blind(agent_type):
        globs = policy.bash_wildcard_handoff_reads(command)
        if globs:
            return (_DENY_PREFIX + "the test-writer is algorithm-blind; a wildcard read over "
                    "handoff/ could resolve to design-internal.md. Read the files you need by "
                    f"exact name instead (offending: {', '.join(globs)[:120]}).")
    if agent_type and policy.is_draft(command):
        return (_DENY_PREFIX + "handoff/draft/ holds unapproved drafts. Subagents read "
                "only promoted files under handoff/. (Conductor promotes on approval.)")

    # (c) writes — resolve redirect/tee targets and adjudicate each against the policy
    #     (implementer test-integrity + the confined roles' product-tree ban).
    for t in policy.bash_write_targets(command):
        d = policy.decide(agent_type, policy.WRITE, t, handoff)
        if not d.allowed:
            return _DENY_PREFIX + d.reason
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # never break the tool on a parse error

    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    agent_type = str(data.get("agent_type") or "")
    agent_id = str(data.get("agent_id") or "")
    target = str(ti.get("file_path") or ti.get("path") or ti.get("command")
                 or ti.get("pattern") or ti.get("subagent_type") or "")

    # Decide FIRST (job #2), so the audit line can record the guard's own decision.
    reason = _deny_reason(tool, ti, agent_type, target)

    # 1. AUDIT (best-effort; never fail the tool because of logging). A denied call has no
    #    transcript effect, so `guard_decision` here is the ONLY record that a denial happened.
    #    The target is logged AT FULL LENGTH (the intent record — #30 R3): the transcript-based
    #    auditor needs the whole command string, not a 300-char prefix.
    try:
        with open(runlog_path(), "a") as f:
            f.write(json.dumps({
                # UTC + tz-aware ("…+00:00") on purpose: the observability analyzer
                # correlates this run-log against the Claude Code session transcript
                # (which stamps UTC/"Z"). A naive local time would be off by the tz
                # offset and break the time-window match. See analyzer/transcript.py.
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "agent_type": agent_type, "agent_id": agent_id,
                "tool": tool, "target": target,
                # #31 R4: the guard's OWN pre-execution decision — not the platform's final
                # verdict or the command's exit status.
                "guard_decision": "deny" if reason else "allow",
            }) + "\n")
    except Exception:
        pass

    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}))
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
