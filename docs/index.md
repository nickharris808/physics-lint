# Is this model physically possible?

Eleven artifacts. One question.

An S-parameter file, a coupling extractor, a machine-learned surrogate — each
arrives as numbers, and numbers do not announce that they describe something
which cannot exist. A model that produces power from nothing, responds before it
is excited, or claims that adding a grounded conductor between two others
*increases* their coupling looks exactly like a model that does not. Simulators
believe them. Accuracy metrics do not object.

This is a set of tools that object.

## The one thing to understand before using any of it

**Every tool here is a grader. It can tell you a model is wrong. None of them
can tell you a model is right.**

That is not modesty, it is the actual logical shape. These checks test
*necessary* conditions — properties any physically realizable network must have.
Passing them means nothing was caught. A perfectly passive model of entirely the
wrong structure passes every law in the portfolio.

If you take one thing from these docs, take that. Everything else follows from
it, including several design decisions that look inconvenient until you see why.

## Start where your problem is

| You have | Start with |
|---|---|
| A folder of `.s2p` files from a vendor | [`sparam-lint`](https://github.com/nickharris808/sparam-lint) |
| A parasitic extractor you are writing | [`maxwell-lint`](https://github.com/nickharris808/maxwell-lint) |
| An ML surrogate about to ship | [`abstain-bench`](https://github.com/nickharris808/abstain-bench) |
| Network files to read, write or convert | [`touchstone-tools`](https://github.com/nickharris808/touchstone-tools) |
| A CI pipeline | [`physics-lint-action`](https://github.com/nickharris808/physics-lint-action) |
| An AI agent reasoning about hardware | [`physics-lint-mcp`](https://github.com/nickharris808/physics-lint-mcp) |
| A checker of your own, and no way to grade it | [`sparam-conformance`](https://huggingface.co/datasets/nickh007/sparam-conformance) |
| A proof that needs sound enclosures | [`interval-core`](https://github.com/nickharris808/interval-core) |
| Thirty seconds and curiosity | [the browser demo](https://huggingface.co/spaces/nickh007/physics-lint) |

Or install the front door and let it route:

```bash
pip install git+https://github.com/nickharris808/physics-lint.git
physics-lint doctor
physics-lint check .
```

## How the pieces relate

```
                    sparam-conformance          screening-ceiling
                  (labelled ground truth)     (a certified theorem)
                            │ grades                    │ produced by
                            ▼                           ▼
  .sNp files ─► touchstone-tools ─► sparam-lint ──┐   interval-core
                (read/write/convert)              │
                                                  ├─► physics-lint ─┬─► the Action (CI)
  an extractor ──────────────► maxwell-lint ──────┤   (one CLI,     └─► the MCP server (agents)
                                                  │    SARIF)
  any model ─────────────────► abstain-bench ─────┘
```

Two of these are not tools at all. `sparam-conformance` is a corpus of labelled
networks that **grades the graders** — without it, "our checker works" is an
assertion. `screening-ceiling` is a machine-certified impossibility result, and
`interval-core` is the arithmetic that produced it.

## The four documents worth reading

<div class="grid cards" markdown>

- **[What this proves — and what it does not](scope.md)**
  The necessary-versus-sufficient distinction, in full. Read this before you
  quote a green result to anyone.

- **[The concepts](concepts.md)**
  Passivity, reciprocity, the screening ceiling, certified bounds — explained
  for someone who did not do the course.

- **[An end-to-end walkthrough](tutorial.md)**
  A folder of unknown vendor models to a green CI badge, passing through most
  of the portfolio.

- **[FAQ](faq.md)**
  Written from the objections people actually raise, including the ones that
  are right.

</div>

## The design rule they share

**Every checker ships proof that it still discriminates.**

A physics checker reporting 100% compliance is indistinguishable from one that
has quietly stopped working — a tolerance widened until nothing fails, a
transposed reshape, an aliased phase unwrap. So:

- `sparam-lint --self-test` builds a network violating each law and requires
  each check to reject it;
- `maxwell-lint` ships a reference model that **must** fail;
- `abstain-bench` ships a model that games the metric and must still be refused;
- `interval-core`'s self-check is tested against a deliberately broken rounding;
- `sparam-conformance` re-derives every ground-truth label by independent linear
  algebra — which caught **three wrong labels** in its own corpus during
  development.

## Licence and provenance

Code is Apache-2.0; the two datasets are CC-BY-4.0. Everything is synthetic or
computational — no proprietary or measured data anywhere in the portfolio.

These tools **grade** a model, or move one between formats. Producing one that is
passive *by construction* — so it cannot fail these laws whatever its parameters
— and accurate at speed in the many-body regime, with calibrated abstention and
a fail-closed signoff certificate, is the commercial core:
**[ChipletOS](https://chipletos.com)**.
