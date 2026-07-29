"""One entry point for the physical-admissibility checkers.

    physics-lint sparam   models/*.s2p     # five laws
    physics-lint coupling matrix --full …  # screening ceiling
    physics-lint abstain  demo             # abstention recall
    physics-lint check    .                # walk a tree, pick per file type
    physics-lint doctor                    # what is installed

Each subcommand hands off to the real checker's CLI, so behaviour, flags and
exit codes are whatever that tool does -- this package adds a front door, not a
second opinion. The two things it adds of its own are `check`, which routes by
file type, and `--sarif`, which is a pure function of the JSON the checkers
already emit.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

from . import __version__
from .checkers import CHECKERS, CheckerMissing, available, install_hint, load
from .sarif import sarif_from_sparam

_TOUCHSTONE = (".s1p", ".s2p", ".s3p", ".s4p", ".s5p", ".s6p", ".s8p", ".s12p", ".s16p")


def _delegate(sub: str, argv: list[str]) -> int:
    """Run a checker's own CLI with the remaining arguments."""
    try:
        mod = load(sub)
    except CheckerMissing as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    from importlib import import_module
    return int(import_module(f"{mod.__name__}.cli").main(argv))


def _capture_sparam_json(paths: list[str]) -> tuple[dict, int]:
    """Run sparam-lint's CLI in-process and take its JSON."""
    mod = load("sparam")
    from importlib import import_module
    cli = import_module(f"{mod.__name__}.cli")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(["--json", *paths])
    return json.loads(buf.getvalue()), int(rc)


def _cmd_check(args: argparse.Namespace) -> int:
    """Walk a path and run the right checker for each file found."""
    root = Path(args.path)
    if not root.exists():
        print(f"error: no such path: {root}", file=sys.stderr)
        return 2

    # Match on the extension, not on is_file(). A *directory* named model.s2p
    # looks exactly like a model to anyone reading the tree, and quietly
    # dropping it would be silence about something that was never checked. The
    # reader refuses it by name, so it surfaces as `unreadable` and the run
    # exits 2 -- could-not-check outranks checked-and-passed.
    files = ([root] if root.is_file()
             else sorted(p for p in root.rglob("*")
                         if p.suffix.lower() in _TOUCHSTONE))
    if not files:
        # Nothing to check is not the same as everything passing, and it is
        # nearly always a path mistake. Say so on stderr and stay green, the
        # same way the Action treats an empty glob.
        print(f"no Touchstone files found under {root}", file=sys.stderr)
        return 0

    report, rc = _capture_sparam_json([str(f) for f in files])
    if args.sarif:
        print(json.dumps(sarif_from_sparam(report, _checker_version("sparam")), indent=2))
    else:
        print(json.dumps(report, indent=2))
    return rc


def _checker_version(sub: str) -> str:
    try:
        return getattr(load(sub), "__version__", "0")
    except CheckerMissing:
        return "0"


def _installed_summary(dist: str) -> str | None:
    """The summary the *installed* distribution declares about itself.

    Without this, `doctor` printed a description baked into CHECKERS and
    asserted it about whatever happens to answer to that name. A distribution
    name is not a guarantee of identity -- `abstain-bench` on this machine can
    be a different project than the one this table was written against -- so
    reporting our description of it would be a claim we had not checked.
    """
    try:
        from importlib.metadata import metadata

        return (metadata(dist) or {}).get("Summary") or None
    except Exception:
        return None


def _cmd_doctor(_: argparse.Namespace) -> int:
    """Report what is installed, and how to get what is not."""
    have = available()
    print("physics-lint", __version__)
    for sub, ok in sorted(have.items()):
        module, dist, desc = CHECKERS[sub]
        mark = "ok     " if ok else "MISSING"
        ver = f" {_checker_version(sub)}" if ok else ""
        print(f"  [{mark}] {sub:9s} {dist}{ver}")
        # What the installed distribution says about itself, not what this
        # package expects it to be. When it declares nothing, fall back to the
        # expected description and label the fallback rather than passing it
        # off as a fact about what is installed.
        summary = _installed_summary(dist) if ok else None
        if summary:
            print(f"             {summary}")
        elif ok:
            print(f"             (declares no summary; expected: {desc})")
        else:
            print(f"             {desc}")
        if not ok:
            print(f"             {install_hint(dist)}")
    missing = [s for s, ok in have.items() if not ok]
    if missing:
        print(f"\n{len(missing)} of {len(have)} checkers unavailable.")
    return 0 if not missing else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="physics-lint",
        description="Physical-admissibility checkers, behind one command.",
        epilog="Each subcommand's own --help lists its full flag set.",
    )
    p.add_argument("--version", action="version", version=f"physics-lint {__version__}")
    subs = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    for sub, (_, dist, desc) in CHECKERS.items():
        sp = subs.add_parser(sub, help=desc, add_help=False,
                             description=f"{desc} Delegates to {dist}.")
        sp.add_argument("rest", nargs=argparse.REMAINDER)

    c = subs.add_parser("check", help="Walk a path and check every Touchstone file.")
    c.add_argument("path", nargs="?", default=".")
    c.add_argument("--sarif", action="store_true",
                   help="emit SARIF 2.1.0 instead of the checker's JSON")
    c.set_defaults(func=_cmd_check)

    d = subs.add_parser("doctor", help="Show which checkers are installed.")
    d.set_defaults(func=_cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Hand a checker's arguments straight through without letting our parser
    # look at them. Anything else swallows the checker's own flags -- argparse
    # would claim `physics-lint sparam --json` as an unrecognized argument of
    # ours -- and would shadow `physics-lint sparam --help`, which must show
    # the real tool's help, not this one's.
    if argv and argv[0] in CHECKERS:
        return _delegate(argv[0], argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
