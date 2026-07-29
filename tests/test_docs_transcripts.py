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


def test_no_readme_example_promises_a_subcommand_of_a_checker_we_do_not_own() -> None:
    """`physics-lint abstain demo` was documented and is now broken.

    The `abstain-bench` distribution name resolves to a *different* project
    than the one this table was written against, and that project has no
    `demo` subcommand -- so a documented command failed with argparse's
    "invalid choice". Delegation is verbatim by design, which means this
    package must not promise any particular subcommand of a checker it does
    not own. `--help` is the only one every argparse CLI answers.

    Scope: `sparam` and `coupling` delegate to `sparam-lint` and `maxwell-lint`,
    which are published from this portfolio, so documenting their subcommands is
    a promise we can keep. `abstain` is not, and that is the difference the
    guard encodes -- not a style rule.
    """
    readme = (HERE / "README.md").read_text(encoding="utf-8")
    promised = set(re.findall(r"^physics-lint abstain ([a-z][a-z0-9-]*)",
                              readme, re.M))
    assert not promised, (
        "README promises abstain-bench subcommand(s) this package cannot "
        f"guarantee: {sorted(promised)}"
    )


def test_the_delegation_examples_that_are_documented_actually_run() -> None:
    """Whatever the README does show under a checker name must work."""
    from shutil import which

    if which("physics-lint") is None:
        pytest.skip("physics-lint not on PATH")
    readme = (HERE / "README.md").read_text(encoding="utf-8")
    for sub in re.findall(r"^physics-lint ((?:sparam|coupling|abstain) --help)",
                          readme, re.M):
        r = subprocess.run(["physics-lint", *sub.split()],
                           capture_output=True, text=True)
        assert r.returncode == 0, (
            f"documented `physics-lint {sub}` exits {r.returncode}:\n{r.stderr}"
        )


# --------------------------------------------------------------------------
# Numbers on the site, bound to their sources.
# --------------------------------------------------------------------------

DOCS = HERE / "docs"


def _all_docs() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(DOCS.glob("*.md")))


def test_the_certified_bound_and_its_consequence_come_from_the_dataset() -> None:
    """`k <= 0.909090909091` and `at least 10.000002%` must re-derive.

    The bound has to hold over every published region, and the over-prediction
    figure is `1/sup(k) - 1` computed from those same regions. If the dataset is
    ever regenerated and the site is not, this fails.
    """
    import json

    data = HERE.parent / "datasets" / "screening-ceiling" / "data" / "certified_regions.jsonl"
    if not data.exists():
        pytest.skip("screening-ceiling data not beside this checkout")

    regions = [json.loads(ln) for ln in data.read_text(encoding="utf-8").splitlines() if ln.strip()]
    sup = max(r["sup_certified_k_hi"] for r in regions)
    text = _all_docs()

    quoted = re.findall(r"k ≤ (0\.\d+)", text)
    assert quoted, "the site no longer quotes the certified bound"
    for q in set(quoted):
        assert sup <= float(q), (
            f"site claims k <= {q} but a published region reaches {sup!r}"
        )

    pct = re.findall(r"at least (\d+\.\d+)%", text)
    assert pct, "the site no longer quotes the over-prediction consequence"
    live = (1.0 / sup - 1.0) * 100.0
    for q in set(pct):
        assert abs(live - float(q)) < 1e-5, (
            f"site says at least {q}%, dataset gives {live:.6f}%"
        )


def test_the_one_unreproducible_figure_is_labelled_as_such_everywhere() -> None:
    """0.081% comes from a solver that is in no release. Every page that quotes
    it must say so on the same page, not in a footnote somewhere else."""
    for p in sorted(DOCS.glob("*.md")):
        t = p.read_text(encoding="utf-8")
        if "0.081%" not in t:
            continue
        assert re.search(r"cannot .{0,40}re-derive|not part of any release|"
                         r"not in any release|taken on our word", t), (
            f"{p.name} quotes 0.081% without saying it is not reproducible here"
        )


def test_the_commercial_section_quotes_no_measurement_at_all() -> None:
    """The iso-compute and calibration experiments ran against the private
    corpus, so their figures cannot be checked by a reader.

    A first draft of the FAQ quoted both. The conclusion is fine to state in
    words; the numbers are not, because nothing published here can produce
    them. The check is for *any* figure rather than for specific ones -- a
    guard that spells out the forbidden numbers publishes them itself.
    """
    faq = (DOCS / "faq.md").read_text(encoding="utf-8")
    # `.` matches newlines under re.S, so the header pattern must be
    # newline-free or it swallows the whole document and captures nothing --
    # which is how this guard first passed against text it should have caught.
    m = re.search(r"^##[^\n]*commercial angle[^\n]*\n(.*?)(?=^## |\Z)",
                  faq, re.M | re.S)
    assert m, "the commercial-angle section is no longer in the shape this guards"
    section = m.group(1)
    figures = re.findall(r"\d+(?:\.\d+)?\s*%|\d+\.\d+", section)
    assert not figures, (
        f"the commercial-angle section quotes {figures}; every measurement "
        "behind it was made against the closed corpus and cannot be checked "
        "by a reader"
    )


def test_doctor_prints_the_summary_the_installed_distribution_declares() -> None:
    """The contract, checked in whatever environment this runs in.

    `doctor` used to print a description baked into CHECKERS and assert it about
    whatever answered to that name. It now prints what the installed
    distribution declares about itself. That is the property worth testing, and
    unlike a transcript diff it holds everywhere -- which matters here, because
    the same distribution name genuinely resolves to different projects on
    different machines, and that is the whole reason the change was made.
    """
    import os
    import sys
    from importlib.metadata import PackageNotFoundError, metadata

    from physics_lint.checkers import CHECKERS, available

    r = subprocess.run([sys.executable, "-m", "physics_lint.cli", "doctor"],
                       cwd=HERE, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=str(HERE / "src")))
    assert r.returncode in (0, 1), r.stderr

    checked = 0
    for sub, ok in available().items():
        if not ok:
            continue
        _mod, dist, _desc = CHECKERS[sub]
        try:
            declared = (metadata(dist) or {}).get("Summary")
        except PackageNotFoundError:
            continue
        if not declared:
            continue
        assert declared in r.stdout, (
            f"doctor does not print the summary {dist} declares:\n  {declared!r}"
        )
        checked += 1

    if checked == 0:
        pytest.skip("no installed checker declares a summary to compare against")


def test_the_readme_missing_block_quotes_what_the_code_would_print() -> None:
    """Environment-free half of the card's `doctor` transcripts.

    A checker that is not installed has nothing to declare, so `doctor` falls
    back to CHECKERS. Wherever the card shows a `[MISSING]` line, the
    description beside it must be that fallback verbatim.
    """
    from physics_lint.checkers import CHECKERS

    readme = (HERE / "README.md").read_text(encoding="utf-8")
    shown_missing = set(re.findall(r"\[MISSING\]\s+\S+\s+(\S+)", readme))
    assert shown_missing, "the card no longer shows a MISSING example"
    for _sub, (_mod, dist, desc) in CHECKERS.items():
        if dist in shown_missing:
            assert desc in readme, (
                f"the card shows {dist} as MISSING but not the description "
                f"CHECKERS declares for it: {desc!r}"
            )
