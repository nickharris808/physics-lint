# FAQ

Written from objections people actually raise. Several of them are right, and
those are marked.

## "My model passed. Is it correct?"

No. The checks are **necessary conditions**: passing means nothing was caught,
not that the model is right. A perfectly passive model of entirely the wrong
structure passes every law here. See [what this proves](scope.md).

## "Isn't this just checking that σ_max ≤ 1? I can write that in ten lines."

You can, and that is roughly what the passivity check is. The value is not in
the ten lines — it is in the four things around them:

1. **Reading the file correctly.** 2-port Touchstone is column-major and 3-port
   and above is row-major, so the obvious parser transposes every 2-port file
   and turns the reciprocity check into a no-op. That bug passes every test
   built on a symmetric fixture.
2. **The negative control.** Your ten lines will report 100% compliance whether
   they work or not, and you will have no way to tell which.
3. **The refusals.** `NaN` in the file, fewer than three frequency points for a
   derivative, a sweep that runs backwards — each needs a decision, and the easy
   decision produces a confident wrong answer.
4. **The corpus.** `sparam-conformance` exists because "my checker works" is an
   assertion otherwise. It caught three wrong labels in its own ground truth
   during development.

If you write your own anyway, please [score it against the corpus](https://huggingface.co/datasets/nickh007/sparam-conformance)
and tell us what it finds.

## "The tool flagged my ferrite isolator. That's a false positive."

**Half right, and the distinction matters.** The check is a *true positive for
the law* and a *false alarm for the device*. A ferrite isolator's medium is
non-reciprocal, so `S ≠ Sᵀ` is it working correctly.

The tool now says exactly that rather than claiming the network is unrealizable
— that was a real over-claim, found while writing the tutorial and fixed.

What it will not do is decide for you. Record that non-reciprocity is expected
for that file. Do not switch the law off globally: it exists to catch transposed
reshapes, and a suppressed law catches nothing.

## "Why won't it just skip files it can't parse?"

Because a checker that skips what it cannot read silently approves it. Exit code
`2` (could not parse) deliberately **outranks** exit `1` (checked and failed):
"I could not check this" is a worse answer than "I checked it and it failed", so
it wins.

## "Why does a file with NaN get refused instead of ignored?"

A physics verdict computed on `NaN` is not a verdict. There is no flag to
override this, on purpose.

## "SARIF findings don't show up on my PR diff."

Expected. SARIF results here carry **no line region**, because a physics failure
happens at a *frequency* and a Touchstone file's rows are not the unit anyone
reasons about. Inventing a line would make the annotation render and would be a
claim about location we cannot support. Findings appear in the Security tab and
the check summary.

## "Isn't the screening ceiling obvious? Of course screening reduces coupling."

**Right that it is obvious; wrong that it is therefore not worth checking.** The
point is not that engineers do not know it — it is that *fitted and truncated
models violate it anyway*, and no accuracy metric reports that. `maxwell-lint
demo` shows a second-order Born correction — the standard cheap fix — predicting
`k > 1` on 78% of pairs. Its mean error looks fine.

## "You claim a theorem. About Maxwell's equations?"

**No, and this is the objection most worth pressing.** It is a theorem about a
**monopole-closure model** — a zero-parameter analytic approximation that matches
a boundary-element reference to 0.081% in the exact two-cylinder limit. The
closure-versus-solver gap is an additive, disclosed, unresolved term that is
never folded into the bound.

The dataset's scope line travels with the data in `theorem.json` for exactly
this reason.

## "Sampling the slider demo never finds a violation. Isn't that circular?"

Sampling cannot prove the bound; it can only refute it. That is why it is
offered — it is a cheap, dependency-free way for a skeptical reader to try to
catch us being wrong. Failing to find a counterexample is the honest expected
outcome and is not the evidence. The evidence is the branch-and-bound proof, and
its soundness rests on the interval arithmetic, which ships its own self-check.

## "Why is `interval-core` a separate package?"

Because it is general and the family-specific certifiers are not. 745 lines of
screening-law machinery stayed in the private tree deliberately; mixing them in
would make a general-purpose library into a confused one. The published package
is the arithmetic, not the application.

## "Why does `abstain-bench` fail a model with 100% accuracy?"

Read the table by column. `overconfident` has a perfect in-envelope pass rate and
answers every out-of-distribution query confidently, which is the default
behaviour of almost every fitted model. `timid` has perfect abstention recall and
abstains on everything.

Neither number is a score on its own. **Your accuracy is measured on the cases
your model chose to answer** — that is the whole point, and pooling the two
metrics conceals it.

## "Can I use these on measured VNA data?"

You can run them, and the laws still apply. But the corpus is synthetic
closed-form networks, so passing it does not establish that a checker behaves
well on measured data with noise, drift and de-embedding artefacts. That gap is
real and stated in the corpus's own scope section.

## "Are any of these on PyPI?"

Not yet. Every install is `pip install git+https://…`, which is stated wherever
a bare `pip install <name>` appears. The release workflows use PyPI Trusted
Publishing and need no stored token; what is missing is a one-time browser step
by the account owner.

## "Has any of this touched real hardware?"

No. **Every number in the portfolio is computational.** Nothing here has been
near a probe. Where a figure came from tooling that is not in a release, the
artifact says so at the figure rather than in a footnote.

## "What is the commercial angle?"

These tools **grade** a model. Producing one that is passive *by construction* —
so it cannot fail these laws whatever its parameters — and accurate at speed in
the many-body regime, with calibrated abstention and a fail-closed signoff
certificate, is [ChipletOS](https://chipletos.com).

The split is deliberate and the boundary is where it is because it was measured:
at matched compute, data-heavy training beat architecture-heavy 6.37% to 14.44%,
and a from-scratch reimplementation of the calibration reproduced the deployed
threshold exactly. The algorithms are not the moat, so they are published.

## "Can I contribute?"

Yes, and the most useful thing you can send is a **new pathological case** for
`sparam-conformance` — a network that breaks a checker in a way the corpus does
not currently cover. Each repository's `CONTRIBUTING.md` states its own
non-negotiable rule; they differ, and they are the reason each package is
trustworthy.
