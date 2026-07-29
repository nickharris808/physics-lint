# Contributing to physics-lint

The one non-negotiable rule for this package:

> **This package performs no physics of its own, and never will.**

Every verdict comes from the checker behind it, unchanged. `physics-lint sparam
…` runs `sparam-lint` with your arguments untouched — same flags, same output,
same exit codes — and a test asserts the JSON coming through here is
byte-identical to the JSON the checker emits directly. If that stopped being
true, this package would become a place for verdicts to quietly change, which
is the one thing a front door must never be.

So a change that adds a check, adjusts a threshold, or reinterprets a result
belongs in the checker, not here. What belongs here is the three things this
package owns: the `check` frontend, SARIF conversion, and `doctor`.

## What a good contribution looks like

- **A refusal we are missing.** An input `check` currently walks past, or
  accepts and reports on without having really validated. Refusing is always
  preferable to a confident answer we have not earned.
- **A SARIF fidelity fix.** Results must not carry a `region`: a physics
  failure happens at a *frequency*, not a line, and inventing one would make
  the annotation render at the cost of being a false claim about location. A
  test enforces this.
- **A `doctor` improvement** that reports something it has verified. It prints
  the summary the installed distribution declares about itself, precisely
  because a distribution name is not a guarantee of identity.

## Before you open a PR

```bash
pip install -e . pytest ruff
python -m pytest tests/ -q
ruff check .
mkdocs build --strict          # if you touched docs/
```

Any number you add to a README or a docs page must be reproducible by running
the published code. Several tests exist solely to enforce that — they re-run
the transcripts on this site and diff them, and they will fail you rather than
let a figure rot. If a number genuinely cannot be re-derived from what is
published, say so at the figure, as `scope.md` does for the one such number in
the portfolio.

New guards should be demonstrated **red** — break the thing they guard, watch
the test fail, then fix it — before being submitted. A guard that has never
failed is a guard nobody has checked.
