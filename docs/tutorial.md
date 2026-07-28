# An end-to-end walkthrough

A directory of vendor models with no provenance, to a green CI badge. Every
transcript here is real output; you can reproduce all of it.

## Setup

```bash
pip install git+https://github.com/nickharris808/physics-lint.git \
            git+https://github.com/nickharris808/sparam-lint.git \
            git+https://github.com/nickharris808/maxwell-lint.git \
            git+https://github.com/nickharris808/touchstone-tools.git

physics-lint doctor      # confirm all three checkers imported
```

For models to look at, the labelled corpus works as a stand-in for your folder:

```bash
git clone https://huggingface.co/datasets/nickh007/sparam-conformance
mkdir models && cp sparam-conformance/data/{passive_line,active_gain,ferrite_isolator}.s2p models/
```

## Step 1 — prove the checker still works

Before trusting a clean report, establish that the thing producing it can still
produce a dirty one.

```bash
$ sparam-lint --self-test
negative control
  [REJECTED] passivity
  [REJECTED] reciprocity
  [REJECTED] energy_conservation
  [REJECTED] positive_real_z0
  [REJECTED] group_delay_nonneg

  battery discriminates: True
```

Five networks built to violate one law each, each rejected. If any law failed to
reject its own violator this exits `3`, and no verdict from that run is worth
anything.

Do this first, every time. It costs a second.

## Step 2 — check everything at once

```bash
$ sparam-lint --quiet models/*.s2p
```

`--quiet` prints only the files with violations; clean ones are still counted in
the summary. Two of the three fail, and **the two failures are completely
different in kind**.

The first is a genuine defect:

```
── models/active_gain.s2p
  [FAIL] passivity              largest singular value 2.882175 > 1 at 25.1429 GHz -- this network produces more power than is put into it
  [FAIL] energy_conservation    worst row power 8.023758 > 1 at 18.9524 GHz -- driving one port yields more power out than in

  2 of 5 laws FAILED
  This network is not physically realizable as a passive device.
```

The second is not:

```
── models/ferrite_isolator.s2p
  [FAIL] reciprocity            normalized asymmetry 1.382e+00 > 1e-06 at 18.9524 GHz -- S is not symmetric; if the medium is reciprocal this indicates a port-ordering or transpose error

  1 of 5 laws FAILED
  S is not symmetric. That is a defect in a reciprocal medium and correct behaviour in a non-reciprocal one -- a ferrite isolator or circulator fails this by design. No other law failed.
```

```
  3 file(s), 2 with violations
```

Notice the tool changes what it concludes based on *which* law failed. A ferrite
isolator is real, buyable hardware; telling its owner the model is "not
physically realizable" would be false. Energy and causality failures license
that statement — reciprocity alone does not.

**This is the judgement call the tool will not make for you.** The right response
to the isolator is to record that non-reciprocity is expected for that file, not
to switch the law off. Suppressing reciprocity to quiet one isolator also goes
blind to the transposed-reshape bug the law exists to catch.

## Step 3 — act on it programmatically

```bash
$ sparam-lint --json models/*.s2p | python3 -c '
import json,sys
for f in json.load(sys.stdin)["files"]:
    bad = [law["law"] for law in f.get("laws", []) if not law["passed"]]
    print(f["file"], "->", ", ".join(bad) or "clean")
'
models/active_gain.s2p -> passivity, energy_conservation
models/ferrite_isolator.s2p -> reciprocity
models/passive_line.s2p -> clean
```

One file emits a flat object; several emit an envelope with a `summary`. The
presence of `files` is how a consumer tells them apart.

## Step 4 — fix what is fixable

Say the isolator arrived referenced to 75 Ω and your stack expects 50 Ω.
`touchstone-tools` re-references it without going near a physics verdict:

```bash
$ touchstone-tools info models/ferrite_isolator.s2p
ferrite_isolator.s2p: 2-port S, 64 points, 1-40 GHz, z0=50Ω
  max |entry|        0.95
  max |S - S^T|      1.900e+00  (reported, not judged)

$ touchstone-tools renorm models/ferrite_isolator.s2p iso75.s2p --z0 75
wrote iso75.s2p  (2-port S, 64 points, z0=75Ω, RI)
```

`info` reports the asymmetry and stops — it will not tell you whether that is a
defect, because that is a question about the device. The split between the two
libraries is deliberate.

## Step 5 — put it in CI

```yaml
name: Physics
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: nickharris808/physics-lint-action@v1
        id: lint
        with:
          files: 'models/**/*.s*p'
          sarif-file: physics.sarif
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: ${{ steps.lint.outputs.sarif }}
```

**Expect the first run to be red**, and read it before reacting. A repository
that has never had a physics check almost always contains something that fails
one. Sort them by the step-2 distinction: energy and causality failures are
defects, reciprocity on a non-reciprocal part is not.

Narrow the glob or exclude the file, and say why in the commit message. Do not
set `fail-on-error: false` globally to cope with one file — that turns the whole
check into decoration.

## Step 6 — grade your own checker, if you have one

If you maintain a validation tool of your own, the corpus grades it:

```bash
$ cd sparam-conformance
$ python score.py --checker your_adapter:check
  false passes : 0   <- must be 0
  false fails  : 0
  errors       : 0
  verdict      : CONFORMING
```

Three verdicts, not two. `CONFORMING` needs zero false passes **and** every law
reported on every case. A checker that never reported a law is `INCOMPLETE` and
exits `1` — it did not look, and the corpus cannot certify what it never saw.

## What you have now, and what you do not

You have ruled out a class of failure that is otherwise invisible and that
simulators propagate silently, with a check that proved it still discriminates
before it ran.

You have **not** established that any of those models is accurate. Every law
here is a necessary condition; a passive model of entirely the wrong structure
passes all of them. See [what this proves](scope.md).
