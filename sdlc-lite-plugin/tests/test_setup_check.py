"""`toolchain/setup_check.py` — the measure-only half of `/sdlc-init` (#19).

The script reads the pinned floors and the target repo and reports what is missing; the skill
renders that and does the writing. One detector decides both "missing" and "nothing to do",
so a second `/sdlc-init` run is a no-op by construction — these tests pin that detector.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parent
SCRIPT = PLUGIN / "toolchain" / "setup_check.py"
sys.path.insert(0, str(PLUGIN / "toolchain"))

import setup_check  # noqa: E402

ALL_MISSING = [
    "pyproject.toml [tool.mutmut]",
    "pyproject.toml [tool.pytest.ini_options]",
    "pyproject.toml [tool.coverage.run]",
    ".gitignore mutants/",
    ".gitignore .coverage*",
    ".gitignore *.egg-info/",
    ".gitignore .implement-feature/",
    ".gitignore if-runlog.jsonl",
]

BARE_PYPROJECT = '[project]\nname = "pkg"\nversion = "0.1.0"\n'
CONFIGURED_PYPROJECT = BARE_PYPROJECT + (
    '\n[tool.mutmut]\nsource_paths = ["src/pkg/"]\n'
    '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    '\n[tool.coverage.run]\nsource = ["src/pkg"]\nbranch = true\n'
)
FULL_GITIGNORE = "mutants/\n.coverage*\n*.egg-info/\n.implement-feature/\nif-runlog.jsonl\n"


def _repo(tmp_path: Path, pyproject: str = BARE_PYPROJECT, gitignore: str | None = None) -> Path:
    (tmp_path / "pyproject.toml").write_text(pyproject)
    if gitignore is not None:
        (tmp_path / ".gitignore").write_text(gitignore)
    return tmp_path


# --- the pinned floors -------------------------------------------------------

def test_parse_requirements_reads_names_and_floors():
    text = "# header\n\nruff>=0.6            # lint\nmypy>=1.11\nhypothesis\n"
    assert setup_check.parse_requirements(text) == [("ruff", "0.6"), ("mypy", "1.11"), ("hypothesis", None)]


def test_parse_requirements_rejects_anything_but_a_floor():
    """`/sdlc-init` never downgrades, so an exact or upper pin has no meaning for it."""
    with pytest.raises(ValueError):
        setup_check.parse_requirements("mutmut==3.8.0\n")


def test_the_shipped_requirements_pin_mutmut_3_as_a_floor():
    reqs = dict(setup_check.parse_requirements(
        (PLUGIN / "toolchain" / "requirements-dev.txt").read_text()))
    assert reqs["mutmut"] == "3"  # 2.x does not read source_paths
    assert {"ruff", "mypy", "pytest", "pytest-cov", "mutmut", "hypothesis", "pytest-asyncio"} <= set(reqs)


# --- found vs floor -> action --------------------------------------------------

@pytest.mark.parametrize("found, floor, expected", [
    (None, "0.6", "install"),
    (None, None, "install"),
    ("0.5.0", "0.6", "upgrade"),
    ("0.6", "0.6", "ok"),
    ("0.6.0", "0.6", "ok"),
    ("0.10.1", "0.6", "ok"),       # numeric, not string, comparison
    ("1.11.0", "1.11", "ok"),
    ("1.9.9", "1.11", "upgrade"),
    ("3.8.0", "3", "ok"),
    ("2.4.5", "3", "upgrade"),
    ("8.4.0", None, "ok"),
])
def test_action(found, floor, expected):
    assert setup_check.action(found, floor) == expected


# --- what is installed ----------------------------------------------------------

def test_found_version_reads_the_running_environment():
    from importlib.metadata import version
    assert setup_check.found_version("pytest") == version("pytest")


def test_an_uninstalled_package_is_found_as_none_and_needs_install():
    found = setup_check.found_version("no-such-package-sdlc-lite-xyz")
    assert found is None
    assert setup_check.action(found, "1.0") == "install"


# --- what config is missing ------------------------------------------------------

def test_a_bare_repo_misses_everything(tmp_path):
    assert setup_check.missing_config(_repo(tmp_path)) == ALL_MISSING


def test_a_configured_repo_misses_nothing(tmp_path):
    assert setup_check.missing_config(_repo(tmp_path, CONFIGURED_PYPROJECT, FULL_GITIGNORE)) == []


def test_setup_cfg_mutmut_counts(tmp_path):
    """mutmut 3 also reads `[mutmut]` from setup.cfg."""
    repo = _repo(tmp_path, gitignore=FULL_GITIGNORE)
    (repo / "setup.cfg").write_text("[mutmut]\nsource_paths = src/pkg/\n")
    assert "pyproject.toml [tool.mutmut]" not in setup_check.missing_config(repo)


@pytest.mark.parametrize("name, text, item", [
    ("pytest.ini", "[pytest]\ntestpaths = tests\n", "pyproject.toml [tool.pytest.ini_options]"),
    ("setup.cfg", "[tool:pytest]\ntestpaths = tests\n", "pyproject.toml [tool.pytest.ini_options]"),
    (".pytest.ini", "[pytest]\ntestpaths = tests\n", "pyproject.toml [tool.pytest.ini_options]"),
    ("tox.ini", "[pytest]\naddopts = -q\n", "pyproject.toml [tool.pytest.ini_options]"),
    (".coveragerc", "[run]\nbranch = True\n", "pyproject.toml [tool.coverage.run]"),
    ("setup.cfg", "[coverage:run]\nbranch = True\n", "pyproject.toml [tool.coverage.run]"),
    ("tox.ini", "[coverage:run]\nbranch = True\n", "pyproject.toml [tool.coverage.run]"),
])
def test_existing_pytest_or_coverage_config_elsewhere_counts(tmp_path, name, text, item):
    repo = _repo(tmp_path)
    (repo / name).write_text(text)
    assert item not in setup_check.missing_config(repo)


def test_pytest_9_native_tool_pytest_table_counts(tmp_path):
    """pytest 9 reads `[tool.pytest]`; adding `ini_options` beside it would be a second config."""
    repo = _repo(tmp_path, BARE_PYPROJECT + '\n[tool.pytest]\ntestpaths = ["tests"]\n')
    assert "pyproject.toml [tool.pytest.ini_options]" not in setup_check.missing_config(repo)


def test_an_unparseable_pyproject_fails_loud_not_all_missing(tmp_path):
    """A broken file must never read as "every table is missing" — /sdlc-init would append to it."""
    repo = _repo(tmp_path, BARE_PYPROJECT + "\n[tool.mutmut\n")
    with pytest.raises(ValueError):
        setup_check.missing_config(repo)
    r = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)], capture_output=True, text=True)
    assert r.returncode == 2
    assert "pyproject.toml" in r.stdout
    assert not any(item in r.stdout for item in ALL_MISSING)


@pytest.mark.parametrize("name", ["setup.cfg", "tox.ini"])
def test_an_unparseable_ini_file_fails_loud(tmp_path, name):
    """A broken setup.cfg / tox.ini must not read as "section absent" — the added pyproject
    table would then silently take precedence over the user's (broken) config."""
    repo = _repo(tmp_path)
    (repo / name).write_text("no section header\nkey = value\n")
    with pytest.raises(ValueError, match=name):
        setup_check.missing_config(repo)


def test_a_commented_out_table_does_not_count(tmp_path):
    repo = _repo(tmp_path, BARE_PYPROJECT + '# [tool.mutmut]\n# source_paths = ["src/pkg/"]\n')
    assert "pyproject.toml [tool.mutmut]" in setup_check.missing_config(repo)


@pytest.mark.parametrize("line", ["mutants/", "mutants", "/mutants/", "/mutants", "  mutants/  "])
def test_gitignore_spellings_of_mutants_count(tmp_path, line):
    repo = _repo(tmp_path, gitignore=line + "\n")
    assert ".gitignore mutants/" not in setup_check.missing_config(repo)


def test_a_commented_gitignore_line_does_not_count(tmp_path):
    repo = _repo(tmp_path, gitignore="# mutants/\n")
    assert ".gitignore mutants/" in setup_check.missing_config(repo)


def test_the_t3_fixture_matches_what_sdlc_init_writes():
    """AC: the python-starter fixture's committed config is exactly what `/sdlc-init` leaves."""
    assert setup_check.missing_config(REPO / "test-fixtures/python-starter/roman-numeral") == []


# --- the CLI the skill runs ---------------------------------------------------------

def test_cli_prints_the_table_and_the_missing_items(tmp_path):
    repo = _repo(tmp_path)
    out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)],
                         capture_output=True, text=True, check=True).stdout
    assert "floor" in out.lower()
    for pkg in ("ruff", "mypy", "pytest", "pytest-cov", "mutmut", "hypothesis", "pytest-asyncio"):
        assert pkg in out
    for item in ALL_MISSING:
        assert item in out


def test_cli_shows_the_installed_version_of_a_satisfied_pin(tmp_path):
    from importlib.metadata import version
    out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(_repo(tmp_path))],
                         capture_output=True, text=True, check=True).stdout
    row = next(ln for ln in out.splitlines() if ln.split()[:1] == ["pytest"])
    assert version("pytest") in row and "ok" in row.split()


def test_cli_on_a_set_up_repo_reports_no_missing_config(tmp_path):
    repo = _repo(tmp_path, CONFIGURED_PYPROJECT, FULL_GITIGNORE)
    out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)],
                         capture_output=True, text=True, check=True).stdout
    assert "floor" in out.lower()
    assert not any(item in out for item in ALL_MISSING)


def _src_layout(tmp_path: Path) -> Path:
    repo = _repo(tmp_path, CONFIGURED_PYPROJECT, FULL_GITIGNORE)
    (repo / "src" / "sdlclitexyzpkg").mkdir(parents=True)
    (repo / "src" / "sdlclitexyzpkg" / "__init__.py").write_text("")
    return repo


def test_cli_reports_an_uninstalled_src_layout_package_as_not_importable(tmp_path):
    """#101: an uninstalled src-layout package must reach the plan as `pip install -e .`,
    not surface later as a red smoke test or a Gate 0 stop."""
    out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(_src_layout(tmp_path))],
                         capture_output=True, text=True, check=True).stdout
    assert "package importable: no (sdlclitexyzpkg)" in out


def test_cli_reports_an_installed_src_layout_package_as_importable(tmp_path):
    """The answer comes from a real import in the active Python, not from the layout — after
    `pip install -e .` the next run must say yes and not offer the install again."""
    import os
    repo = _src_layout(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(repo / "src")}
    out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)],
                         capture_output=True, text=True, check=True, env=env).stdout
    assert "package importable: yes (sdlclitexyzpkg)" in out


def test_cli_reports_a_flat_layout_package_as_importable(tmp_path):
    """A package at the repo root imports from the repo dir; it needs no install."""
    repo = _repo(tmp_path, CONFIGURED_PYPROJECT, FULL_GITIGNORE)
    (repo / "sdlclitexyzpkg").mkdir()
    (repo / "sdlclitexyzpkg" / "__init__.py").write_text("")
    out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)],
                         capture_output=True, text=True, check=True).stdout
    assert "package importable: yes (sdlclitexyzpkg)" in out


def test_package_dir_skips_the_tests_dir(tmp_path):
    repo = _repo(tmp_path)
    for d in ("pkg", "tests"):
        (repo / d).mkdir()
        (repo / d / "__init__.py").write_text("")
    assert setup_check.package_dir(repo) == repo / "pkg"


def test_more_than_one_package_dir_is_unknown_not_a_guess(tmp_path):
    """The skill asks about an ambiguous layout; the script must not pick one for it."""
    repo = _repo(tmp_path, CONFIGURED_PYPROJECT, FULL_GITIGNORE)
    for d in ("pkg_a", "pkg_b"):
        (repo / "src" / d).mkdir(parents=True)
        (repo / "src" / d / "__init__.py").write_text("")
    assert setup_check.package_dir(repo) is None
    out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)],
                         capture_output=True, text=True, check=True).stdout
    assert "package importable: unknown" in out


def test_no_pyproject_is_a_stop_not_a_list_of_missing_tables(tmp_path):
    """Scope: no pyproject.toml -> stop with a message (creating a project layout is out of scope)."""
    with pytest.raises(FileNotFoundError):
        setup_check.missing_config(tmp_path)
    r = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 2
    assert "pyproject.toml" in r.stdout + r.stderr
    assert not any(item in r.stdout for item in ALL_MISSING)
