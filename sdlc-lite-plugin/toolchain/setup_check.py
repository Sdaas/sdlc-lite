"""Measure-only half of `/sdlc-init` (#19): reports what a repo lacks for `/implement-feature`.

Reads the pinned floors (`requirements-dev.txt`), compares them with what the running Python
has installed, and lists the config items the target repo is missing. It never writes a file
and never installs anything; the `/sdlc-init` skill renders this output and does the writing.

    python setup_check.py [--repo DIR] [--requirements FILE]

Exit 0 on a report; 2 when the repo has no pyproject.toml or a config file does not parse (fail loud —
a broken file must never read as "every table is missing").
"""
from __future__ import annotations

import argparse
import configparser
import importlib.util
import re
import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_REQ = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:>=\s*([0-9][0-9A-Za-z.]*))?$")

GITIGNORE_LINES = ["mutants/", ".coverage*", "*.egg-info/", ".implement-feature/", "if-runlog.jsonl"]


def parse_requirements(text: str) -> list[tuple[str, str | None]]:
    """(name, floor) per line; only `name>=floor` or a bare name is accepted."""
    out: list[tuple[str, str | None]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = _REQ.match(line)
        if not m:
            raise ValueError(f"unsupported requirement (only '>=' floors or bare names): {line!r}")
        out.append((m.group(1), m.group(2)))
    return out


def found_version(name: str) -> str | None:
    """Installed version in the running interpreter, or None."""
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _release(v: str) -> tuple[int, ...]:
    parts: list[int] = []
    for seg in v.split("."):
        m = re.match(r"\d+", seg)
        if not m:
            break
        parts.append(int(m.group()))
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def action(found: str | None, floor: str | None) -> str:
    """'install' (absent), 'upgrade' (below floor) or 'ok'."""
    if found is None:
        return "install"
    if floor is not None and _release(found) < _release(floor):
        return "upgrade"
    return "ok"


def _read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _toml_has_table(doc: dict[str, object], dotted: str) -> bool:
    node: object = doc
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            return False
        node = node[key]
    return True


def _cfg_has_section(text: str, section: str, name: str) -> bool:
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        cp.read_string(text)
    except configparser.Error as e:
        raise ValueError(f"{name} does not parse: {e}") from e
    return cp.has_section(section)


def missing_config(repo: Path) -> list[str]:
    """Config items `/implement-feature` needs that `repo` lacks (stable order).

    Raises FileNotFoundError (no pyproject.toml) or ValueError (it, setup.cfg or tox.ini does not parse). Config a
    tool already reads from another file counts as present, so nothing is added that would
    shadow it (pytest prefers pyproject.toml over tox.ini, for one)."""
    pyproject = repo / "pyproject.toml"
    if not pyproject.is_file():
        raise FileNotFoundError(pyproject)
    try:
        toml = tomllib.loads(pyproject.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"{pyproject} does not parse: {e}") from e
    cfg = _read(repo / "setup.cfg")
    tox = _read(repo / "tox.ini")
    missing: list[str] = []
    if not (_toml_has_table(toml, "tool.mutmut") or _cfg_has_section(cfg, "mutmut", "setup.cfg")):
        missing.append("pyproject.toml [tool.mutmut]")
    if not (_toml_has_table(toml, "tool.pytest") or (repo / "pytest.ini").is_file()
            or (repo / ".pytest.ini").is_file() or _cfg_has_section(cfg, "tool:pytest", "setup.cfg")
            or _cfg_has_section(tox, "pytest", "tox.ini")):
        missing.append("pyproject.toml [tool.pytest.ini_options]")
    if not (_toml_has_table(toml, "tool.coverage.run") or (repo / ".coveragerc").is_file()
            or _cfg_has_section(cfg, "coverage:run", "setup.cfg") or _cfg_has_section(tox, "coverage:run", "tox.ini")):
        missing.append("pyproject.toml [tool.coverage.run]")
    ignored = {ln.strip().strip("/") for ln in _read(repo / ".gitignore").splitlines()
               if ln.strip() and not ln.strip().startswith("#")}
    missing += [f".gitignore {ln}" for ln in GITIGNORE_LINES if ln.strip("/") not in ignored]
    return missing


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--requirements", type=Path, default=here / "requirements-dev.txt")
    args = ap.parse_args(argv)

    try:
        missing = missing_config(args.repo)
    except FileNotFoundError:
        print(f"No pyproject.toml in {args.repo.resolve()} — /sdlc-init needs an existing Python project.")
        return 2
    except ValueError as e:
        print(f"{e} — fix it first; /sdlc-init will not guess around a config file it cannot read.")
        return 2

    rows = [(n, found_version(n), f) for n, f in parse_requirements(args.requirements.read_text())]
    print(f"{'package':<16} {'found':<10} {'floor':<8} action")
    for name, found, floor in rows:
        print(f"{name:<16} {found or '-':<10} {floor or '-':<8} {action(found, floor)}")
    print(f"\npip available: {'yes' if importlib.util.find_spec('pip') else 'no'} ({sys.executable})")
    print("\nMissing config:")
    for item in missing:
        print(f"  {item}")
    if not missing:
        print("  none — config is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
