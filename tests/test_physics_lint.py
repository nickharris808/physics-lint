"""Tests for the physics-lint front door.

The rule this package lives under: it must add a door, not a second opinion.
So most of what is tested here is that it *delegates* faithfully, that it
degrades to a usable instruction when a checker is absent, and that the one
thing it computes itself -- SARIF -- invents nothing.
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

import physics_lint  # noqa: E402
from physics_lint import checkers, sarif  # noqa: E402
from physics_lint.cli import build_parser  # noqa: E402
from physics_lint.cli import main as cli_main  # noqa: E402

# Fixtures are written here rather than read from a sibling checkout. A
# standalone clone of this repository has no ../sparam-lint next to it, and a
# test that silently depends on the developer's directory layout fails only for
# other people.
_HDR = "# HZ S RI R 50"


def _write_s2p(path, gain=1.0, n=16):
    """A simple reciprocal 2-port. gain > 1 makes it non-passive on purpose."""
    lines = [_HDR]
    for i in range(n):
        f = 1e9 + i * 1e9
        s11 = 0.10
        s21 = 0.90 * gain
        lines.append(f"{f:.6e} {s11} 0.0 {s21} 0.0 {s21} 0.0 {s11} 0.0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def models(tmp_path):
    """A directory with one admissible model and one that cannot exist."""
    d = tmp_path / "models"
    d.mkdir()
    _write_s2p(d / "passive_line.s2p", gain=1.0)
    _write_s2p(d / "active_gain.s2p", gain=3.0)
    return d


def _run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli_main(argv)
    return rc, buf.getvalue()


# ------------------------------------------------------------------ wiring

def test_every_checker_has_a_subcommand_and_an_install_hint():
    parser = build_parser()
    actions = [a for a in parser._actions if a.dest == "cmd"]
    names = set(actions[0].choices)
    assert set(checkers.CHECKERS) <= names
    for _, dist, desc in checkers.CHECKERS.values():
        assert desc.strip(), "a subcommand with no description is undiscoverable"
        assert checkers.install_hint(dist).startswith("pip install git+")


def test_install_hint_names_git_not_a_package_index():
    """None of the three is on PyPI, so `pip install sparam-lint` is bad advice."""
    for _, dist, _ in checkers.CHECKERS.values():
        hint = checkers.install_hint(dist)
        assert "github.com/nickharris808" in hint
        assert hint != f"pip install {dist}"


def test_missing_checker_gives_an_instruction_not_a_traceback():
    """The failure mode a user hits first has to be actionable."""
    with pytest.raises(checkers.CheckerMissing) as exc:
        checkers.load("nope")
    assert "expected one of" in str(exc.value)


def test_doctor_reports_every_checker():
    rc, out = _run(["doctor"])
    for sub in checkers.CHECKERS:
        assert sub in out
    assert rc in (0, 1)


# -------------------------------------------------------------- delegation

def test_sparam_subcommand_delegates_exit_code(models):
    """A clean model exits 0 and a non-physical one exits 1, unchanged."""
    pytest.importorskip("sparam_lint")
    assert _run(["sparam", str(models / "passive_line.s2p"), "--no-colour"])[0] == 0
    assert _run(["sparam", str(models / "active_gain.s2p"), "--no-colour"])[0] == 1


def test_delegation_does_not_reinterpret_the_verdict(models):
    """Front door, not second opinion: the JSON must be the checker's own."""
    pytest.importorskip("sparam_lint")
    from sparam_lint.cli import main as sp_main
    direct = io.StringIO()
    with redirect_stdout(direct):
        sp_main(["--json", str(models / "active_gain.s2p")])
    _, through = _run(["sparam", "--json", str(models / "active_gain.s2p")])
    assert json.loads(through) == json.loads(direct.getvalue())


# ------------------------------------------------------------------- check

def test_check_walks_a_directory(models):
    pytest.importorskip("sparam_lint")
    rc, out = _run(["check", str(models)])
    payload = json.loads(out)
    assert payload["summary"]["n_files"] >= 2
    assert rc == 1, "the directory contains a known-bad model"


def test_check_on_an_empty_tree_says_so_and_stays_green(tmp_path):
    """Nothing to check is a path mistake, not a pass -- but not a failure either."""
    rc, out = _run(["check", str(tmp_path)])
    assert rc == 0
    assert out.strip() == "", "no findings should be printed for an empty tree"


def test_check_on_a_missing_path_is_an_error():
    rc, _ = _run(["check", "/definitely/not/here"])
    assert rc == 2


# ------------------------------------------------------------------- SARIF

def test_sarif_is_wellformed_and_names_only_rules_it_reports(models):
    pytest.importorskip("sparam_lint")
    _, out = _run(["check", str(models), "--sarif"])
    doc = json.loads(out)
    assert doc["version"] == "2.1.0"
    assert doc["$schema"] == sarif.SCHEMA
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "sparam-lint"
    declared = {r["id"] for r in run["tool"]["driver"]["rules"]}
    used = {r["ruleId"] for r in run["results"]}
    assert used <= declared, f"results cite undeclared rules: {used - declared}"
    assert declared == used, f"rules declared but never used: {declared - used}"
    for res in run["results"]:
        assert res["message"]["text"].strip()
        assert res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]


def test_sarif_invents_no_line_numbers(models):
    """A physics failure happens at a frequency, not at a line.

    Emitting a `region` would make the annotation render in the PR diff, which
    is precisely why it is tempting -- and it would be a claim about where the
    problem is that we cannot support.
    """
    pytest.importorskip("sparam_lint")
    _, out = _run(["check", str(models), "--sarif"])
    for res in json.loads(out)["runs"][0]["results"]:
        for loc in res["locations"]:
            assert "region" not in loc["physicalLocation"], (
                "a region here would be a fabricated location"
            )


def test_sarif_reports_an_unreadable_file_rather_than_dropping_it(tmp_path):
    """Silence about a file we could not read is indistinguishable from a pass."""
    report = {"files": [{"file": "broken.s2p", "error": "no data rows", "passed": False}],
              "summary": {"n_files": 1}}
    doc = sarif.sarif_from_sparam(report)
    ids = [r["ruleId"] for r in doc["runs"][0]["results"]]
    assert ids == ["unreadable"]
    assert "no data rows" in doc["runs"][0]["results"][0]["message"]["text"]


def test_sarif_of_a_clean_run_has_no_results_and_no_rules():
    doc = sarif.sarif_from_sparam(
        {"file": "ok.s2p", "passed": True,
         "laws": [{"law": "passivity", "passed": True, "message": "fine"}]})
    assert doc["runs"][0]["results"] == []
    assert doc["runs"][0]["tool"]["driver"]["rules"] == []


def test_sarif_accepts_both_json_shapes():
    """sparam-lint emits a flat object for one file and an envelope for many."""
    law = {"law": "passivity", "passed": False, "message": "sigma_max 2.0 > 1"}
    flat = sarif.sarif_from_sparam({"file": "a.s2p", "laws": [law]})
    env = sarif.sarif_from_sparam({"files": [{"file": "a.s2p", "laws": [law]}]})
    assert flat["runs"][0]["results"] == env["runs"][0]["results"]


def test_every_rule_carries_a_real_explanation():
    """A SARIF rule with a restated title for a description helps nobody."""
    for rule_id, text in sarif._HELP.items():
        assert len(text) > 60, f"{rule_id} has a placeholder description"
        assert text != rule_id


def test_coupling_sarif_reports_the_ceiling():
    doc = sarif.sarif_from_coupling(
        {"n_violations": 28, "n_pairs": 56, "max_k": 1.5946, "worst_pair": [2, 6]},
        "coupling.csv")
    res = doc["runs"][0]["results"]
    assert len(res) == 1 and res[0]["ruleId"] == "screening_ceiling"
    assert "1.5946" in res[0]["message"]["text"]
    assert "(2, 6)" in res[0]["message"]["text"]


def test_coupling_sarif_of_a_clean_report_is_empty():
    doc = sarif.sarif_from_coupling({"n_violations": 0, "n_pairs": 56, "max_k": 0.8}, "c.csv")
    assert doc["runs"][0]["results"] == []


# ---------------------------------------------------------------- metadata

def test_version_is_exported_and_matches_pyproject():
    text = (HERE / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{physics_lint.__version__}"' in text


def test_package_declares_no_hard_dependency_on_the_checkers():
    """Declaring them would make this package uninstallable, not convenient.

    None of the three is on a package index, and a direct git URL cannot be
    published to PyPI. The lazy import plus an install hint is the honest
    arrangement; this guard stops someone 'fixing' it into a broken install.
    """
    text = (HERE / "pyproject.toml").read_text(encoding="utf-8")
    deps = text.split("dependencies = [", 1)[1].split("]", 1)[0]
    for _, dist, _ in checkers.CHECKERS.values():
        assert dist not in deps, f"{dist} must stay an optional, lazily-imported checker"


def test_checker_flags_are_not_swallowed_by_our_parser(models):
    """`physics-lint sparam --json f.s2p` must reach sparam-lint intact.

    argparse claimed --json as an unrecognized argument of ours until
    delegation was moved ahead of parsing. Anything that re-introduces a parse
    step before the hand-off breaks every checker flag at once.
    """
    pytest.importorskip("sparam_lint")
    rc, out = _run(["sparam", "--json", str(models / "passive_line.s2p")])
    assert rc == 0
    assert json.loads(out)["passed"] is True


def test_checker_help_is_the_checkers_own():
    """`physics-lint sparam --help` must not show this package's help."""
    pytest.importorskip("sparam_lint")
    with pytest.raises(SystemExit):
        _run(["sparam", "--help"])


def test_tests_depend_on_no_sibling_checkout():
    """A standalone clone has no ../sparam-lint beside it.

    Depending on the developer's directory layout produces a suite that passes
    locally and fails for everyone else -- which is exactly what happened on
    the first CI run of this repository.
    """
    src = Path(__file__).read_text(encoding="utf-8")
    # Drop this function's own body before scanning, or the guard matches the
    # very strings it exists to forbid.
    body = src.split("def test_tests_depend_on_no_sibling_checkout", 1)[0]
    parent = "HERE.parent /"          # assembled so it is not a literal here
    for sibling in ("sparam-lint", "maxwell-lint", "abstain-bench"):
        needle = f'{parent} "{sibling}"'
        assert needle not in body, f"tests reach outside the repository: {needle}"
        assert f'"..{"/"}{sibling}"' not in body
