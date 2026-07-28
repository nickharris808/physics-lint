"""The documentation site's transcripts, re-run and diffed against the code.

`docs/tutorial.md` shows captured output. Captured output rots: a message gets
reworded, a number changes, and the page keeps claiming the old one. That is
exactly the failure this portfolio exists to make impossible elsewhere, so the
transcripts are bound to the tools rather than trusted.

This caught a real drift on its first run -- `touchstone-tools info` was
documented as reporting `max |entry| 0.95` and `max |S - S^T| 1.900e+00` when it
actually reports `0.944061` and `9.252e-01`.

Every check skips when the tool it exercises is not installed, because
`physics-lint` deliberately does not depend on the checkers.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
TUTORIAL = HERE / "docs" / "tutorial.md"

# The three files the tutorial's `models/` directory holds. Taken from the
# sparam-conformance corpus, which is where a reader gets them.
CASES = ("active_gain", "ferrite_isolator", "passive_line")


def _corpus() -> Path:
    """The sibling corpus checkout, if this is a dev tree."""
    d = HERE.parent / "sparam-conformance" / "data"
    if not all((d / f"{c}.s2p").exists() for c in CASES):
        pytest.skip("sparam-conformance corpus not beside this checkout")
    return d


@pytest.fixture(scope="module")
def models(tmp_path_factory) -> Path:
    src = _corpus()
    d = tmp_path_factory.mktemp("tut") / "models"
    d.mkdir()
    for c in CASES:
        (d / f"{c}.s2p").write_bytes((src / f"{c}.s2p").read_bytes())
    return d


def _doc() -> str:
    return TUTORIAL.read_text(encoding="utf-8")


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    exe = argv[0]
    from shutil import which

    if which(exe) is None:
        pytest.skip(f"{exe} not on PATH")
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True)


def test_tutorial_exists_and_is_on_the_nav() -> None:
    assert TUTORIAL.exists()
    nav = (HERE / "mkdocs.yml").read_text(encoding="utf-8")
    assert "tutorial.md" in nav, "the tutorial is not reachable from the site nav"


def test_self_test_transcript_still_matches(models: Path) -> None:
    """Step 1: the negative control, and the line the page quotes from it."""
    r = _run(["sparam-lint", "--self-test"], models.parent)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "battery discriminates: True" in r.stdout
    for law in ("passivity", "reciprocity", "energy_conservation",
                "positive_real_z0", "group_delay_nonneg"):
        assert f"[REJECTED] {law}" in r.stdout
        assert f"[REJECTED] {law}" in _doc(), f"page no longer shows {law}"


def test_step2_file_count_line_matches(models: Path) -> None:
    """The summary line is a claim about how many files fail. Check it."""
    r = _run(["sparam-lint", "--quiet"] + sorted(str(p) for p in models.glob("*.s2p")),
             models.parent)
    tail = r.stdout.strip().splitlines()[-1].strip()
    assert tail == "3 file(s), 2 with violations", tail
    assert tail in _doc(), f"page's summary line is stale; live is {tail!r}"


def test_the_isolator_conclusion_on_the_page_is_the_one_the_code_prints(
    models: Path,
) -> None:
    """The honesty fix, pinned.

    A network whose only failing law is reciprocity must not be called
    unrealizable -- an isolator is real hardware. If someone reverts that, the
    page and the code disagree and this fails.
    """
    r = _run(["sparam-lint", str(models / "ferrite_isolator.s2p")], models.parent)
    concl = [ln.strip() for ln in r.stdout.splitlines()
             if ln.strip().startswith("S is not symmetric.")]
    assert concl, r.stdout
    assert concl[0] in _doc(), f"page's conclusion is stale; live is {concl[0]!r}"
    assert "not physically realizable" not in r.stdout, (
        "reciprocity alone must not license the unrealizable conclusion"
    )


def test_step3_json_mapping_reproduces(models: Path) -> None:
    """The little JSON consumer on the page, run for real."""
    import json

    r = _run(["sparam-lint", "--json"] + sorted(str(p) for p in models.glob("*.s2p")),
             models.parent)
    doc = json.loads(r.stdout)
    got = {
        Path(f["file"]).name: sorted(
            law["law"] for law in f.get("laws", []) if not law["passed"]
        )
        for f in doc["files"]
    }
    assert got == {
        "active_gain.s2p": ["energy_conservation", "passivity"],
        "ferrite_isolator.s2p": ["reciprocity"],
        "passive_line.s2p": [],
    }, got


def test_step4_touchstone_info_numbers_are_the_live_ones(models: Path) -> None:
    """The drift this file was written to catch."""
    r = _run(["touchstone-tools", "info", str(models / "ferrite_isolator.s2p")],
             models.parent)
    assert r.returncode == 0, r.stdout + r.stderr
    page = _doc()
    for key in ("max |entry|", "max |S - S^T|"):
        live = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith(key)]
        assert live, r.stdout
        assert live[0] in page, f"page is stale for {key!r}; live is {live[0]!r}"


def test_no_transcript_on_the_page_quotes_a_number_we_cannot_produce() -> None:
    """A blunt backstop: every `$ ` command block on the page is one we ship.

    It does not check the output -- the tests above do that for the ones that
    have output worth pinning. It checks that nobody documented a command that
    does not exist, which is the cheapest way for a tutorial to become fiction.
    """
    known = {"sparam-lint", "maxwell-lint", "abstain-bench", "touchstone-tools",
             "physics-lint", "python3", "python", "cd", "pip", "git"}
    cmds = {m.split()[0] for m in re.findall(r"^\$ (.+)$", _doc(), re.M)}
    unknown = cmds - known
    assert not unknown, f"tutorial documents unknown command(s): {sorted(unknown)}"
