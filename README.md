# physics-lint

![CI](https://github.com/nickharris808/physics-lint/actions/workflows/ci.yml/badge.svg) ![Python](https://img.shields.io/badge/python-3.10%20%E2%80%93%203.13-blue) ![Licence](https://img.shields.io/badge/licence-Apache--2.0-green) ![Tests](https://img.shields.io/badge/tests-57%20passing-brightgreen)

📖 **[Documentation site](https://nickharris808.github.io/physics-lint/)** — the portfolio narrative, the concepts, a full walkthrough, and what all of this proves (and does not). Built from [`docs/`](docs/) in this repository.

**One command for the physical-admissibility checkers.**

Three tools answer the same question in three places — is this model physically
possible? — and until now you had to know three package names and three CLIs to
use them. This is the front door.

```bash
pip install git+https://github.com/nickharris808/physics-lint.git

physics-lint doctor              # what is installed
physics-lint check .             # walk a tree, check every Touchstone file
physics-lint sparam my.s2p       # five laws
physics-lint coupling demo       # screening ceiling
physics-lint abstain demo        # abstention recall
```

> **Not yet on PyPI.** `pip install physics-lint` is the intended install once
> published; until then use the source install above.

## It is a front door, not a fourth checker

`physics-lint sparam …` runs `sparam-lint` with your arguments untouched — same
flags, same output, same exit codes. There is no second opinion layered on top,
and a test asserts the JSON that comes through this package is byte-identical to
the JSON the checker emits directly. If that were not true, this package would
be a place for verdicts to quietly change.

It adds exactly three things of its own: the `check` subcommand, SARIF output,
and `doctor`.

## Installing the checkers

The three checkers are **not** hard dependencies. Someone who only cares about
S-parameters should not be made to install a coupling-ceiling checker, and none
of the three is on a package index yet — a direct git URL cannot be published to
PyPI, so declaring them would make this package *uninstallable* rather than
convenient.

So each subcommand imports its checker lazily and, if it is missing, tells you
the command that fixes it:

```bash
$ physics-lint doctor
physics-lint 0.1.0
  [ok     ] abstain   abstain-bench 0.1.0
             Does a model know when to shut up? Abstention recall.
  [MISSING] coupling  maxwell-lint
             Does a coupling extractor predict impossible physics? k <= 1.
             pip install git+https://github.com/nickharris808/maxwell-lint.git@main
  [ok     ] sparam    sparam-lint 0.1.0
             Is an S-parameter model physically possible? Five laws.

1 of 3 checkers unavailable.
```

`doctor` exits `1` when anything is missing, so it works as a CI preflight.

## `check` — walk a tree

```bash
$ physics-lint check models/
```

Finds every `.s1p`…`.s16p` under the path and runs the S-parameter battery over
all of them in one pass, emitting the checker's JSON. Exit codes are
`sparam-lint`'s: `0` clean, `1` a law failed, `2` a file could not be read.

An empty match prints a note to stderr and stays green — that is nearly always a
path mistake rather than a physics problem, and it is the same call the GitHub
Action makes. A path that does not exist is an error.

## SARIF — findings inline on the pull request

```bash
physics-lint check models/ --sarif > physics.sarif
```

Then upload it with `github/codeql-action/upload-sarif`, and each failing law
appears as an annotation on the PR instead of buried in a job log.

**One deliberate omission.** SARIF results usually carry a line and column, and
GitHub renders the annotation in the diff when they do. There is a strong pull
to emit one so the output looks better. A physics failure does not happen at a
line — it happens at a **frequency** — and a Touchstone file's rows are not the
unit anyone reasons about. So results point at the file with no `region`, and
the frequency goes in the message where it is true. A test asserts no `region`
is ever emitted. The annotation is less pretty and it is not a lie about where
the problem is.

Two more things the SARIF gets right rather than conveniently:

- a file that could **not be read** becomes an `unreadable` result, not silence.
  Saying nothing about a file you failed to parse is indistinguishable from
  passing it;
- rules are declared only when they fire, so the rule list is never padded with
  laws that had nothing to say.

## CLI reference

```
physics-lint {sparam,coupling,abstain,check,doctor} [...]
```

| Command | What it does |
|---|---|
| `sparam …` | Delegates to `sparam-lint`. All its flags work. |
| `coupling …` | Delegates to `maxwell-lint`. |
| `abstain …` | Delegates to `abstain-bench`. |
| `check [PATH] [--sarif]` | Walk a tree and check every Touchstone file found. Default path `.`. |
| `doctor` | Report which checkers are installed. Exit `1` if any is missing. |
| `--version` | Print the version. |

`physics-lint sparam --help` shows **sparam-lint's** help, not this package's —
the arguments after a checker name are handed straight through without being
parsed here.

## Library use

```python
from physics_lint import sarif_from_sparam, available, load

print(available())                  # {'sparam': True, 'coupling': True, ...}
sparam = load("sparam")             # raises CheckerMissing with an install hint
doc = sarif_from_sparam(report)     # the JSON you already have -> SARIF 2.1.0
```

| Object | What it is |
|---|---|
| `available() -> dict[str, bool]` | Which checkers import right now. |
| `load(subcommand) -> module` | Import a checker, or raise `CheckerMissing` carrying the install command. |
| `CheckerMissing` | `RuntimeError` subclass; its message is meant to be shown to a user verbatim. |
| `sarif_from_sparam(report, version="0")` | `sparam-lint --json` output (either shape) → SARIF 2.1.0. |
| `sarif_from_coupling(report, uri, version="0")` | `maxwell-lint --json` ceiling report → SARIF 2.1.0. |
| `CHECKERS` | subcommand → (import name, distribution name, description). |

## Troubleshooting

**`physics-lint sparam` says the package is missing but I installed it** — you
installed it into a different environment. `physics-lint doctor` reports the
version it can actually import; compare that with `pip show sparam-lint`.

**`--json` is rejected as an unrecognized argument** — that was a real bug,
fixed: arguments after a checker name are now handed through without this
package's parser looking at them. Upgrade.

**`check` found nothing and exited 0** — no `.sNp` files under that path. The
note goes to stderr so it does not pollute piped JSON.

**SARIF uploads but no annotations appear in the diff** — expected, and see
above: results have no line region because a physics failure has a frequency,
not a line. They appear in the Security tab and in the check summary.

**`doctor` exits 1 in CI and I want it not to** — do not paper over it; a
missing checker means the corresponding files went unchecked. Install it, or
drop that subcommand from the job.

## Scope, honestly

This package performs **no physics of its own**. Every verdict comes from the
checker behind it, and each of those tells you whether a model is *physically
admissible*, never whether it is *accurate* — a perfectly passive model of
entirely the wrong structure passes every law. Necessary, not sufficient.

## The rest of the toolkit

| | |
|---|---|
| [`sparam-lint`](https://github.com/nickharris808/sparam-lint) | Is an S-parameter model physically possible? Five laws + a negative control. |
| [`maxwell-lint`](https://github.com/nickharris808/maxwell-lint) | Does a coupling extractor predict impossible physics? Screening ceiling k ≤ 1. |
| [`abstain-bench`](https://github.com/nickharris808/abstain-bench) | Does a model know when to shut up? Abstention recall, never pooled with accuracy. |
| [`sparam-conformance`](https://huggingface.co/datasets/nickh007/sparam-conformance) | 11 labelled networks with verified ground truth. Grades the graders. |
| [`screening-ceiling`](https://huggingface.co/datasets/nickh007/screening-ceiling) | A certified impossibility result + 27 counterexamples. Zero-dependency verifier. |
| [`physics-lint-action`](https://github.com/nickharris808/physics-lint-action) | The same checks, in your CI. |
| [`physics-lint-mcp`](https://github.com/nickharris808/physics-lint-mcp) | A physics oracle your AI agent can call. |
| [**Try it in your browser**](https://huggingface.co/spaces/nickh007/physics-lint) | All three checks, no install, runs client-side. |

These tools **grade** a model. Producing one that is passive *by construction* —
so it cannot fail these laws whatever its parameters — and accurate at speed in
the many-body regime, with calibrated abstention and a fail-closed signoff
certificate, is the commercial core: **[ChipletOS](https://chipletos.com)**.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
