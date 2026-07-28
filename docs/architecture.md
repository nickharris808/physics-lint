# Architecture notes

Why the portfolio is shaped the way it is. These are the decisions a
contributor would otherwise reverse.

## Why separate packages rather than one

Someone who only has `.s2p` files should not be made to install a coupling
checker, a benchmark harness and an interval-arithmetic library. Each package
has its own audience, its own release cadence, and its own non-negotiable rule
in `CONTRIBUTING.md` — and those rules genuinely differ.

`physics-lint` exists as the front door for people who want all of it. It is a
*front door, not a fourth checker*: arguments after a checker name are handed
through without its parser looking at them, and a test asserts the JSON coming
through it is byte-identical to the checker's own. If that were not true, it
would be a place for verdicts to quietly change.

## Why the checkers are not dependencies of the front door

None of them is on a package index, and a direct git URL cannot be published to
PyPI. Declaring them would make `physics-lint` *uninstallable* rather than
convenient. So each subcommand imports lazily and prints the exact install
command when its checker is absent, and `doctor` reports the whole picture.

A guard test stops someone "fixing" this into a broken install.

## Why SARIF lives in one place

It is a pure function of the JSON the checkers already emit. Three
implementations of a serialization format is three chances to drift, so the
conversion lives in `physics-lint` and the Action installs that package only
when `sarif-file` is set.

## Why the dataset verifier imports nothing

`screening-ceiling`'s `verify.py` runs under `env -i /usr/bin/python3` with no
packages installed — its own Gauss-Jordan inverse, its own potential matrix. A
skeptic should be able to check the claim without trusting anything of ours,
including our test suite.

That costs speed (48 µs/layout) and legibility is the product, so it will not be
optimized. There is a note to that effect where someone would otherwise be
tempted.

## Why the Space is static

It runs CPython in the browser through WebAssembly, so no file is uploaded and
no server executes anything. The Gradio Lite version is **pinned**: newer
releases currently fail to resolve their own `huggingface-hub` dependency inside
Pyodide, which surfaces as a console error rather than anything visible on the
page.

## Where each refusal lives

The abstention discipline is enforced at the layer that owns the question:

| Refusal | Layer | Why there |
|---|---|---|
| `NaN` in a file | the reader | Nothing downstream should ever see it |
| Singular conversion | `touchstone_tools.network` | The conversion is what has no answer |
| No coupling reference | `maxwell-lint` argument parsing | The ratio is undefined before any physics runs |
| Unreported law → `INCOMPLETE` | the scorer's verdict | Only the scorer knows what was not checked |
| No SARIF line region | the emitter | The only layer that would be inventing one |

## The one shared rule

**Every checker ships proof that it still discriminates.** A negative control in
`sparam-lint`, a must-fail model in `maxwell-lint`, a metric-gaming model in
`abstain-bench`, an inward-rounding fault injection in `interval-core`, and
independent re-derivation of every label in `sparam-conformance`.

A physics checker reporting 100% compliance is indistinguishable from one that
has quietly stopped working. That is the failure mode the whole portfolio is
built against, and it is why a clean report here is evidence rather than an
assertion.
