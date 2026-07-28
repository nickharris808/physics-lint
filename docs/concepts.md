# The concepts

Written for someone competent who did not do this particular course. No
derivations you could look up; just the ideas the tools act on, and the traps
that make them worth automating.

## S-parameters, in one paragraph

Drive port *i* of a network with a wave and measure what comes back out of every
port. `S_ij` is the complex ratio of the wave leaving port *i* to the wave
entering port *j*. Collect them into an N×N complex matrix, repeat at every
frequency, and that is an S-parameter model: an (F, N, N) array. It says nothing
about what is inside the box, only how the box responds.

Touchstone (`.s2p`, `.s4p`, …) is the near-universal file format for those
arrays. The port count lives in the **extension**, not in the file.

## Passivity: σ_max(S) ≤ 1

A passive device cannot deliver more power than it receives. Written as a
condition on the matrix, the largest singular value of `S` must not exceed 1.

Singular values rather than entries, because power can be created by a
*combination* of ports even when no single entry exceeds 1. `σ_max` is the worst
case over every possible input vector, which is why it is the right test and
why checking `|S_ij| ≤ 1` entrywise is not.

**What it catches:** models that create energy — a de-embedding gone wrong, a
fitted model extrapolated past its data, an amplifier pasted into a passive
cascade.

## Reciprocity: S = Sᵀ

Most media are reciprocal: a wave going from port 1 to port 2 sees the same
transfer as one going the other way. So `S` equals its transpose.

**What it catches:** almost always a *software* bug rather than a physics one.
A transposed reshape. A port-ordering mistake. And most specifically:

### The trap: 2-port files are column-major

Touchstone stores a 2-port row as **S11 S21 S12 S22** — column-major — while
three-port and above are row-major (S11 S12 S13 S21 …). This is a genuine
inconsistency in the format, and it is the single most common way a hand-rolled
parser is subtly wrong.

A parser that assumes row-major everywhere silently **transposes every 2-port
file it reads**. That turns the reciprocity check into a no-op: `S` and `Sᵀ` are
swapped, and `S = Sᵀ` still holds, so nothing complains. A transposed model with
a working reciprocity check looks identical to a correct one.

It is worth dwelling on how hard this is to catch by testing. A *symmetric*
network round-trips perfectly through a transposing writer **and** a transposing
reader. Every test built on a reciprocal fixture passes. You need an asymmetric
network with four distinguishable values to see it at all, which is exactly what
`touchstone-tools` and `sparam-lint` both pin.

### And the case where the law is right and the device is fine

A **ferrite isolator** is real hardware whose medium is non-reciprocal. `S ≠ Sᵀ`
is it working. See [scope](scope.md#where-a-law-firing-is-not-a-defect).

## Energy conservation, per driven port

For each port *i*, the power leaving all ports when *i* is driven cannot exceed
the power put in: `Σⱼ |S_ij|² ≤ 1`.

This is not implied by passivity being *nearly* satisfied, and it is not the same
as a global norm. A per-row violation can hide inside a matrix whose overall norm
looks fine — averaging is exactly what conceals it.

## Positive-real input impedance

Convert `S` to an impedance `Z` and look at the real part at each port. Negative
resistance means the port sources power. Physical for an active device, not for
the passive network you thought you had.

## Group delay ≥ 0

Group delay is `−dφ/dω`, the derivative of phase with respect to frequency.
Negative group delay on the through path means the output precedes the input.

**The trap here is arithmetic, not physics.** Phase is measured modulo 2π, so a
naive difference of successive phase samples jumps by ~2π at every wrap and
reports enormous spurious negative delay. The fix is to unwrap the phase before
differencing, and `sparam-conformance` keeps a sharp resonator in its corpus
specifically to catch checkers that forget.

Because it is a derivative, group delay needs at least three frequency points.
With fewer, `sparam-lint` reports **SKIP** with a reason rather than guessing —
a skipped law is never folded into the pass count.

## The screening ceiling: k ≤ 1

Now the coupling side, which is where the more interesting result lives.

Pack conductors together and every *other* conductor screens the field between
any two of them. So a pair's mutual capacitance measured inside the array is at
most what it would be with only that pair present:

```
k = |C_full| / |C_iso|  ≤  1
```

A predicted `k > 1` is **anti-screening**: it says that adding a grounded
conductor *between* two others increases their coupling. No passive arrangement
of conductors in a linear medium can do that.

This is a good property to automate precisely because **no accuracy metric will
tell you it happened**. A learned or approximate extractor can have excellent
mean error and still predict impossible physics on a subset of pairs.

### Why pairwise-superposition extraction is always wrong here

Fast parasitic extraction often assumes `k ≡ 1` — compute each pair in isolation
and superpose. Since real screening gives `k < 1`, that assumption
**over-predicts** coupling, always, in one direction.

Writing the screening depth as `δ = −log₁₀ k ≥ 0`, the relative error of
assuming `k ≡ 1` is

```
E(δ) = 10^δ − 1
```

which has three properties worth stating as properties rather than as a fitted
trend: it is zero exactly when there is no screening; it is one-sided, so
pairwise never *under*-predicts; and it is strictly increasing, so there is no
depth past which it stops getting worse. Denser designs make it worse
monotonically.

### The truncated-correction trap

The obvious cheap fix is a second-order Born correction — a truncated
perturbation series. It is what a competent engineer reaches for when a full
solve is too slow, and it is not a strawman.

Truncating an alternating series overshoots. On tight-pitch arrays the overshoot
pushes the prediction into `k > 1`: a first-order correction to a known
structural error makes the answer *qualitatively unphysical* rather than merely
inaccurate. `maxwell-lint demo` reproduces this on the bundled models.

## Certified bounds, and why sampling is not one

`screening-ceiling` claims something stronger than "we sampled and found no
violation": for **every** layout in a continuous four-parameter family,
`k ≤ 0.909090909091`.

You cannot get that by sampling. The technique is **interval branch-and-bound**:

1. Evaluate `k` over a whole *box* of parameters at once, using arithmetic that
   returns an interval guaranteed to contain every value the box can produce.
2. If the interval's upper end is below the bound, the entire box is certified —
   infinitely many layouts, one evaluation.
3. If not, split the box and recurse.
4. Terminate when every box is certified, or report the ones that are not.

237,490 certified leaves, zero failure regions, full volume coverage.

The soundness rests entirely on step 1: **the interval must never be narrower
than the truth**. That is what [`interval-core`](https://github.com/nickharris808/interval-core)
provides — directed outward rounding, so the lower bound rounds down and the
upper bound rounds up. An interval library that rounds the wrong way produces
tighter, better-looking, unsound results, and the failure is invisible until
someone's theorem turns out to be false. Which is why that package ships a
self-check and tests it against a deliberately inward-rounding multiplication.

### The consequence, stated carefully

Since the bound is `10/11` and pairwise assumes `k ≡ 1`, a pairwise extractor
over-predicts the worst coupling in that family by **at least 10.000002%** —
not on average, not usually, always. The odd last digits are real: the figure is
derived from the supremum the proof actually certified rather than from the
target bound, which makes it very slightly stronger than `100/k̄ − 100`.

## Abstention, and why accuracy hides it

Last concept, and the one with the widest reach beyond RF.

A model asked a question outside its training envelope has two honest options:
answer, or decline. Most fitted models do neither — they extrapolate
confidently, because nothing in the loss function ever taught them where their
data stopped.

**Your accuracy number is measured on the cases your model chose to answer.** If
it answers everything, that number is silently including extrapolations you
would never have accepted had you been asked.

`abstain-bench` scores the recall of abstention on out-of-distribution cases and
**refuses to pool it** with in-envelope accuracy, because pooling conceals
exactly the thing being measured. It also enforces a utility floor, since a model
that abstains on everything has perfect recall and no value. Neither number is a
score on its own — that is why they sit under separate floors.
