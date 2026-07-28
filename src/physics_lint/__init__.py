"""physics-lint — the physical-admissibility checkers behind one command.

This package is a front door, not a fourth checker. It adds three things:

* one CLI (`physics-lint sparam|coupling|abstain`) so there is one name to
  remember instead of three;
* `physics-lint check`, which walks a tree and routes by file type;
* SARIF 2.1.0 output, so findings land inline on a pull request.

Everything else is the underlying tool's behaviour, unchanged. The checkers
are imported lazily, so this package installs and runs with none of them
present and tells you exactly what to install when you reach for one.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .checkers import CHECKERS, CheckerMissing, available, load
from .sarif import sarif_from_coupling, sarif_from_sparam

__all__ = [
    "CHECKERS", "CheckerMissing", "available", "load",
    "sarif_from_sparam", "sarif_from_coupling", "__version__",
]
