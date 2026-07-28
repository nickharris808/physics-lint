"""Lazy access to the three checkers, with an install message when one is absent.

The checkers are separate packages on purpose: someone who only cares about
S-parameters should not be made to install a coupling-ceiling checker. That
means this package cannot assume any of them are present, and the failure when
one is missing has to be a usable instruction rather than an ImportError
traceback.
"""

from __future__ import annotations

import importlib
from types import ModuleType

__all__ = ["CHECKERS", "CheckerMissing", "load", "available"]

#: subcommand -> (import name, distribution name, one-line description)
CHECKERS: dict[str, tuple[str, str, str]] = {
    "sparam": (
        "sparam_lint",
        "sparam-lint",
        "Is an S-parameter model physically possible? Five laws.",
    ),
    "coupling": (
        "maxwell_lint",
        "maxwell-lint",
        "Does a coupling extractor predict impossible physics? k <= 1.",
    ),
    "abstain": (
        "abstain_bench",
        "abstain-bench",
        "Does a model know when to shut up? Abstention recall.",
    ),
}

_REPO = "https://github.com/nickharris808"


class CheckerMissing(RuntimeError):
    """A subcommand was invoked but the package behind it is not installed."""


def install_hint(dist: str) -> str:
    """The exact command that fixes a missing checker.

    Names the git source rather than the bare distribution because none of the
    three is on a package index yet; saying `pip install sparam-lint` here
    would be advice that does not work.
    """
    return f"pip install git+{_REPO}/{dist}.git@main"


def load(subcommand: str) -> ModuleType:
    """Import the checker behind ``subcommand`` or raise with instructions."""
    if subcommand not in CHECKERS:
        raise CheckerMissing(
            f"unknown checker {subcommand!r}; expected one of "
            f"{', '.join(sorted(CHECKERS))}"
        )
    module, dist, _ = CHECKERS[subcommand]
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise CheckerMissing(
            f"`physics-lint {subcommand}` needs the {dist} package, which is "
            f"not installed.\n\n    {install_hint(dist)}\n\n"
            f"(underlying error: {exc})"
        ) from exc


def available() -> dict[str, bool]:
    """Which checkers can be imported right now. Used by `physics-lint doctor`."""
    out = {}
    for sub, (module, _, _) in CHECKERS.items():
        try:
            importlib.import_module(module)
        except ImportError:
            out[sub] = False
        else:
            out[sub] = True
    return out
