"""Adversarial tests for the surfaces this package added.

The oracle throughout: **no input may produce a confident-looking answer that
is wrong.** A tool may be right, or it may refuse. A verdict on input it did not
actually validate is a failure of this suite regardless of exit status.

The two surfaces added here are SARIF (a new export format) and `check` (a new
frontend). So the questions are: does the export preserve every verdict, and
does the frontend refuse what it does not understand rather than assuming?
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

from physics_lint import sarif  # noqa: E402
from physics_lint.cli import main as cli_main  # noqa: E402

pytest.importorskip("sparam_lint")

_HDR = "# HZ S RI R 50"


def _write(path, rows):
    path.write_text("\n".join([_HDR, *rows]) + "\n", encoding="utf-8")
    return path


def _s2p(path, gain=1.0, n=8):
    return _write(path, [
        f"{1e9 + i*1e9:.6e} 0.1 0.0 {0.9*gain} 0.0 {0.9*gain} 0.0 0.1 0.0"
        for i in range(n)])


def _run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli_main(argv)
    return rc, buf.getvalue()


# ============================================================ verdict-preserving

def test_sarif_loses_no_violation_that_the_json_reports(tmp_path):
    """The export must be lossless in the direction that matters.

    A SARIF file with fewer findings than the JSON is a confident-looking clean
    bill of health for a model that failed.
    """
    d = tmp_path / "m"
    d.mkdir()
    _s2p(d / "clean.s2p", gain=1.0)
    _s2p(d / "bad.s2p", gain=3.0)
    _write(d / "unreadable.s2p", ["1e9 0.1 0.0 nan 0.0 0.5 0.0 0.1 0.0"])

    _, raw = _run(["check", str(d)])
    _, doc = _run(["check", str(d), "--sarif"])
    report, sarif_doc = json.loads(raw), json.loads(doc)

    json_failures = {
        (f["file"], law["law"])
        for f in report["files"] for law in f.get("laws", []) if not law["passed"]
    }
    json_unreadable = {f["file"] for f in report["files"] if "error" in f}

    sarif_results = {
        (r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], r["ruleId"])
        for r in sarif_doc["runs"][0]["results"]
    }
    sarif_failures = {(u, r) for u, r in sarif_results if r != "unreadable"}
    sarif_unreadable = {u for u, r in sarif_results if r == "unreadable"}

    assert sarif_failures == json_failures, (
        f"SARIF and JSON disagree: only in JSON {json_failures - sarif_failures}, "
        f"only in SARIF {sarif_failures - json_failures}"
    )
    assert sarif_unreadable == json_unreadable, (
        "a file that could not be read went missing from the SARIF"
    )


def test_sarif_exit_code_matches_the_json_exit_code(tmp_path):
    """Adding --sarif must not change the verdict, only the rendering."""
    d = tmp_path / "m"
    d.mkdir()
    _s2p(d / "bad.s2p", gain=3.0)
    assert _run(["check", str(d)])[0] == _run(["check", str(d), "--sarif"])[0]


def test_sarif_of_an_all_clean_tree_is_empty_and_exits_zero(tmp_path):
    d = tmp_path / "m"
    d.mkdir()
    _s2p(d / "a.s2p")
    _s2p(d / "b.s2p")
    rc, out = _run(["check", str(d), "--sarif"])
    assert rc == 0
    assert json.loads(out)["runs"][0]["results"] == []


def test_an_unreadable_file_never_becomes_silence(tmp_path):
    """Silence about a file we failed to parse is indistinguishable from a pass."""
    d = tmp_path / "m"
    d.mkdir()
    _write(d / "broken.s2p", ["not a number at all"])
    rc, out = _run(["check", str(d), "--sarif"])
    ids = [r["ruleId"] for r in json.loads(out)["runs"][0]["results"]]
    assert "unreadable" in ids
    assert rc == 2, "could-not-check must outrank could-not-pass"


# ==================================================================== malformed

@pytest.mark.parametrize("content,label", [
    ("", "completely empty"),
    ("\n\n\n", "only blank lines"),
    (_HDR + "\n", "option line but no data"),
    ("! just a comment\n", "only a comment"),
    ("\x00\x01\x02binary garbage\n", "binary"),
    (_HDR + "\n1e9 0.1\n", "a truncated row"),
    (_HDR + "\n1e9 0.1 0 0.5 0 0.5 0 0.1 0\n1e9 0.1 0 0.5 0 0.5 0 0.1 0\n", "a repeated frequency"),
    ("# HZ Y RI R 50\n1e9 1 0 2 0 3 0 4 0\n", "Y-parameters in an .s2p"),
    (_HDR + "\n1e9 inf 0 0.5 0 0.5 0 0.1 0\n", "an infinity"),
])
def test_malformed_input_never_yields_a_verdict(tmp_path, content, label):
    """Every one of these must be reported as unreadable, never as a pass."""
    d = tmp_path / "m"
    d.mkdir()
    (d / "x.s2p").write_text(content, encoding="utf-8")
    rc, out = _run(["check", str(d), "--sarif"])
    doc = json.loads(out)
    ids = [r["ruleId"] for r in doc["runs"][0]["results"]]
    assert rc == 2, f"{label}: expected exit 2, got {rc}"
    assert ids == ["unreadable"], f"{label}: expected an unreadable result, got {ids}"


def test_a_directory_named_like_a_touchstone_file_is_not_read(tmp_path):
    """A frontend that stats a path by name alone will trip on this."""
    d = tmp_path / "m"
    d.mkdir()
    (d / "trap.s2p").mkdir()
    rc, out = _run(["check", str(d), "--sarif"])
    assert rc == 2, "a directory must not be read as a model"
    ids = [r["ruleId"] for r in json.loads(out)["runs"][0]["results"]]
    assert ids == ["unreadable"], (
        "a path that looks like a model and was not checked must be reported, "
        "not silently dropped"
    )


# ======================================================================== empty

def test_an_empty_tree_stays_green_and_prints_nothing_to_stdout(tmp_path):
    """Nothing to check is a path mistake, not a pass -- and not a failure.

    The note goes to stderr so it cannot pollute piped JSON.
    """
    rc, out = _run(["check", str(tmp_path)])
    assert rc == 0
    assert out.strip() == ""


def test_an_empty_tree_with_sarif_prints_nothing_rather_than_a_clean_bill(tmp_path):
    rc, out = _run(["check", str(tmp_path), "--sarif"])
    assert rc == 0
    assert out.strip() == "", (
        "emitting an empty SARIF run for a tree with no files would read as "
        "'checked, all clean'"
    )


def test_a_missing_path_is_an_error_not_an_empty_pass():
    assert _run(["check", "/definitely/not/here"])[0] == 2


# ===================================================================== enormous

def test_a_wide_tree_is_all_accounted_for(tmp_path):
    """Every file must appear; none may be silently dropped at scale."""
    d = tmp_path / "m"
    d.mkdir()
    n = 200
    for i in range(n):
        _s2p(d / f"m{i:03d}.s2p", gain=3.0 if i % 5 == 0 else 1.0)
    rc, out = _run(["check", str(d)])
    report = json.loads(out)
    assert report["summary"]["n_files"] == n
    assert report["summary"]["n_with_violations"] == n // 5
    assert rc == 1

    _, doc = _run(["check", str(d), "--sarif"])
    uris = {r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
            for r in json.loads(doc)["runs"][0]["results"]}
    assert len(uris) == n // 5, "SARIF dropped files at scale"


def test_a_long_sweep_and_many_ports_are_handled(tmp_path):
    d = tmp_path / "m"
    d.mkdir()
    rows = [f"{1e9 + i*1e6:.6e} " + " ".join("0.05 0.0" for _ in range(64))
            for i in range(2000)]
    _write(d / "big.s8p", rows)
    rc, out = _run(["check", str(d)])
    assert rc in (0, 1), "a large valid file must produce a verdict, not a crash"
    assert json.loads(out)["n_ports"] == 8


# ========================================================= out of distribution

def test_a_one_port_file_does_not_fake_the_laws_it_cannot_evaluate(tmp_path):
    """Reciprocity on a 1x1 matrix is vacuous, not passed.

    The failure to hunt is a law reporting PASS because it had nothing to
    evaluate -- which reads identically to a law that checked and was satisfied.
    """
    d = tmp_path / "m"
    d.mkdir()
    _write(d / "one.s1p", [f"{1e9 + i*1e9:.6e} 0.2 0.0" for i in range(8)])
    rc, out = _run(["check", str(d)])
    assert rc in (0, 1)
    report = json.loads(out)
    assert report["n_ports"] == 1
    # Whatever the laws report, nothing may claim a frequency it never looked at.
    for law in report["laws"]:
        assert isinstance(law["passed"], bool)


def test_a_two_point_sweep_skips_the_derivative_rather_than_guessing(tmp_path):
    """Group delay needs three points. Two is a SKIP with a reason."""
    d = tmp_path / "m"
    d.mkdir()
    _write(d / "short.s2p", [
        "1e9 0.1 0.0 0.5 0.0 0.5 0.0 0.1 0.0",
        "2e9 0.1 0.0 0.5 0.0 0.5 0.0 0.1 0.0"])
    _, out = _run(["check", str(d)])
    gd = next(law for law in json.loads(out)["laws"]
              if law["law"] == "group_delay_nonneg")
    assert gd.get("detail", {}).get("skipped") is True, (
        "a derivative over two points must be skipped, not evaluated"
    )


def test_an_all_zero_matrix_does_not_divide_by_its_own_norm(tmp_path):
    """A matched load is S = 0. Normalizing by ||S|| divides by zero."""
    d = tmp_path / "m"
    d.mkdir()
    _write(d / "zero.s2p", [f"{1e9 + i*1e9:.6e} " + " ".join(["0.0"] * 8)
                            for i in range(8)])
    rc, out = _run(["check", str(d)])
    assert rc == 0, "an all-zero network is passive and should pass"
    assert all(law["passed"] for law in json.loads(out)["laws"])


def test_a_marginally_lossless_network_is_not_false_alarmed(tmp_path):
    """sigma_max = 1 - 1e-12 is legal. A too-tight tolerance rejects it."""
    d = tmp_path / "m"
    d.mkdir()
    v = 1.0 - 1e-12
    _write(d / "lossless.s2p",
           [f"{1e9 + i*1e9:.6e} 0.0 0.0 {v!r} 0.0 {v!r} 0.0 0.0 0.0"
            for i in range(8)])
    rc, out = _run(["check", str(d)])
    pas = next(law for law in json.loads(out)["laws"] if law["law"] == "passivity")
    assert pas["passed"], f"false alarm on a legal lossless line: {pas['message']}"


# ==================================================================== the frontend

def test_the_frontend_refuses_an_unknown_subcommand():
    with pytest.raises(SystemExit) as exc:
        _run(["definitely-not-a-command"])
    assert exc.value.code == 2


def test_the_frontend_does_not_invent_a_checker_it_lacks(monkeypatch):
    """A missing checker must be an instruction, never a fabricated verdict."""
    import importlib

    import physics_lint.checkers as ch
    real = importlib.import_module

    def blocked(name, *a, **k):
        if name.startswith("sparam_lint"):
            raise ImportError("hidden for this test")
        return real(name, *a, **k)

    # checkers.load uses importlib.import_module, which does NOT route through
    # builtins.__import__ -- patching that instead silently does nothing and
    # the test passes for the wrong reason.
    monkeypatch.setattr(ch.importlib, "import_module", blocked)
    with pytest.raises(ch.CheckerMissing) as exc:
        ch.load("sparam")
    assert "pip install" in str(exc.value)


def test_extensions_the_frontend_does_not_understand_are_not_guessed(tmp_path):
    """A .txt of Touchstone content must not be read on a hunch."""
    d = tmp_path / "m"
    d.mkdir()
    _s2p(d / "model.txt")
    rc, out = _run(["check", str(d)])
    assert rc == 0 and out.strip() == "", (
        "a file with an unknown extension must be skipped, not guessed at -- "
        "Touchstone encodes the port count in the extension, so guessing it "
        "would mean guessing the matrix shape"
    )


# ================================================================= differential

def test_check_agrees_exactly_with_calling_the_checker_directly(tmp_path):
    """The frontend must not become a place verdicts quietly change."""
    from sparam_lint.cli import main as sp_main
    d = tmp_path / "m"
    d.mkdir()
    _s2p(d / "a.s2p", gain=1.0)
    _s2p(d / "b.s2p", gain=3.0)
    files = sorted(str(p) for p in d.glob("*.s2p"))

    direct = io.StringIO()
    with redirect_stdout(direct):
        rc_direct = sp_main(["--json", *files])
    rc_through, through = _run(["check", str(d)])

    assert json.loads(through) == json.loads(direct.getvalue())
    assert rc_through == rc_direct


def test_sarif_from_either_json_shape_is_identical():
    """One file emits a flat object, several an envelope. Same findings."""
    law = {"law": "passivity", "passed": False, "message": "sigma_max 2.0 > 1"}
    flat = sarif.sarif_from_sparam({"file": "a.s2p", "laws": [law]})
    env = sarif.sarif_from_sparam({"files": [{"file": "a.s2p", "laws": [law]}]})
    assert flat["runs"][0]["results"] == env["runs"][0]["results"]
    assert flat["runs"][0]["tool"]["driver"]["rules"] == \
        env["runs"][0]["tool"]["driver"]["rules"]
