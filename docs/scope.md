# What this proves — and what it does not

Every artifact in this portfolio has a "Scope, honestly" section. This is the
same argument in one place, because the distinction matters more than any
individual tool and it is the thing most likely to be misread from a green
result.

## Necessary, not sufficient

The five laws, the screening ceiling, the certified bound — all of them are
**necessary conditions**. A physically realizable network must satisfy them.
It does not follow that satisfying them makes a network realizable, or correct,
or a good model of the thing you built.

A perfectly passive, perfectly reciprocal, perfectly causal model of *entirely
the wrong structure* passes every check in this portfolio.

So the honest reading of a green result is: **nothing was caught**. That is
genuinely worth having — it rules out a class of failure that is otherwise
invisible and that simulators propagate silently — and it is not validation.

## Admissibility is not accuracy

This is the same point in the vocabulary the tools use.

- **Admissible**: could exist. The laws test this.
- **Accurate**: matches the thing you fabricated. Nothing here tests this.

The only way to establish accuracy is comparison against measurement or against
a converged field solve. No tool in this portfolio does either, and none claims
to.

## Computational, not measured

**Nothing here has touched a probe.** Every number in every artifact is
computed. The corpus is synthesised from closed-form models, the coupling
reference models are thin-wire forms in a homogeneous medium, and the certified
bound is a theorem about a model.

Where a number came from something that is not in the release, the artifact says
so at the number rather than in a footnote. Three such figures exist across the
portfolio and each is labelled where it appears.

## A theorem about a model is not a theorem about Maxwell

`screening-ceiling` publishes a genuine machine-certified result: for every
layout in a four-parameter family, `k ≤ 0.909090909091`. Interval
branch-and-bound, 237,490 certified leaves, zero failure regions.

That is a theorem about a **monopole-closure model** — a zero-parameter analytic
multiple-scattering approximation. It matches a boundary-element reference to
0.081% in the exact two-cylinder limit, and the closure-versus-solver gap is an
**additive, disclosed, unresolved** term that is never absorbed into the bound.

That `0.081%` is the one figure on this site you **cannot** re-derive from
published code: it came from the boundary-element solver used to develop the
closure, which is not part of any release here. It is quoted because it bounds
how much trust the closure has earned, and a reader is entitled to know which
numbers are checkable and which are taken on our word. Everything else on these
pages is reproducible with the commands beside it.

The distinction is not pedantry. A reader who takes it as a statement about
Maxwell's equations has been misled, and the dataset's own scope line travels
with the data in `theorem.json` precisely so that cannot happen quietly.

## Sampling cannot prove; it can refute

The browser demo lets you move four sliders and hunt for a layout that breaks
the certified bound. You will not find one — but the reason matters. Sampling a
continuum establishes nothing about the points you did not sample. What sampling
*can* do is refute, and handing a skeptical reader a cheap way to try to catch
us being wrong is the point of shipping it.

The same applies to `interval-core`'s self-check: it samples, so it can find a
broken enclosure and cannot certify a correct one. It is evidence, not proof.

## Where a law firing is *not* a defect

The clearest case in the portfolio, and the one that most often surprises people:

**A ferrite isolator is real, buyable hardware, and it fails reciprocity.**

Its medium is non-reciprocal, so `S ≠ Sᵀ` is the device working correctly. The
check firing there is a **true positive for the law and a false alarm for the
device**.

`sparam-conformance` keeps such a case in its corpus deliberately, because any
honest tool has to handle it. A checker that treats every law failure as a
defect will reject legitimate hardware; one that suppresses reciprocity to quiet
the noise goes blind to the transposed-reshape bug the law exists to catch. The
right answer is neither — it is to record that non-reciprocity is expected for
that file.

Similar situations exist for `maxwell-lint` (a conversion that is genuinely
singular) and `abstain-bench` (a model that abstains correctly and is therefore
"wrong" on OOD cases by construction).

## What the tools refuse to guess

Throughout the portfolio, **when there is no answer the tools refuse rather than
producing one**. That is a deliberate stance and it costs convenience:

- a file containing `NaN` is refused, not parsed, because a verdict computed on
  `NaN` is not a verdict;
- a singular S→Y conversion is refused with the frequency named, not returned as
  a large finite number that looks actionable;
- a coupling ceiling with no reference matrix is refused, because `k` is a ratio
  and there is no verdict without a denominator;
- a checker that never reported a law is `INCOMPLETE`, not `CONFORMING` — an
  unreported law was not checked, and a corpus cannot certify what it never saw;
- SARIF results carry no line region, because a physics failure happens at a
  *frequency* and inventing a line would misreport where the problem is.

Each of those has an "easier" alternative that produces a confident-looking
answer. That is exactly why they are refusals.

## What would change these limits

Honest answers, not roadmap items:

| Limit | What would lift it |
|---|---|
| Admissibility, not accuracy | Comparison against measurement or a converged field solve |
| Computational, not measured | A VNA on real hardware |
| A model, not Maxwell | Bounding the closure-versus-solver gap, not just disclosing it |
| One family, not all layouts | More families through the same prover |
| Synthetic corpus | Labelled measured data with its artefacts |

None of these is close. Saying so is more useful than a roadmap that implies
otherwise.
