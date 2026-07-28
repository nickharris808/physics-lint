# The eleven artifacts

| Artifact | What it answers | Licence |
|---|---|---|
| [`physics-lint`](https://github.com/nickharris808/physics-lint) | One command for all the checkers. SARIF for CI. | Apache-2.0 |
| [`sparam-lint`](https://github.com/nickharris808/sparam-lint) | Is an S-parameter model physically possible? Five laws + a negative control. | Apache-2.0 |
| [`maxwell-lint`](https://github.com/nickharris808/maxwell-lint) | Does a coupling extractor predict impossible physics? Screening ceiling k ≤ 1. | Apache-2.0 |
| [`abstain-bench`](https://github.com/nickharris808/abstain-bench) | Does a model know when to shut up? Abstention recall, never pooled with accuracy. | Apache-2.0 |
| [`touchstone-tools`](https://github.com/nickharris808/touchstone-tools) | Read, write and convert N-port files. Refuses to emit what it would not read. | Apache-2.0 |
| [`interval-core`](https://github.com/nickharris808/interval-core) | Validated interval arithmetic. Ships the enclosure self-check. | Apache-2.0 |
| [`physics-lint-action`](https://github.com/nickharris808/physics-lint-action) | The same checks, in your CI. | Apache-2.0 |
| [`physics-lint-mcp`](https://github.com/nickharris808/physics-lint-mcp) | A physics oracle an AI agent can call. | Apache-2.0 |
| [`sparam-conformance`](https://huggingface.co/datasets/nickh007/sparam-conformance) | 11 labelled networks with verified ground truth. Grades the graders. | CC-BY-4.0 |
| [`screening-ceiling`](https://huggingface.co/datasets/nickh007/screening-ceiling) | A certified impossibility result + 27 counterexamples. Zero-dependency verifier. | CC-BY-4.0 |
| [physics-lint (Space)](https://huggingface.co/spaces/nickh007/physics-lint) | Try three of the checks in a browser, no install. | Apache-2.0 |

Each repository carries its own CLI reference, API table, troubleshooting
section and worked example. This site covers what is true *across* them.

## Contributing

Every repository has a `CONTRIBUTING.md` stating one non-negotiable rule, and
they differ by design:

- **`sparam-lint`** — every new law needs a violator that the law must reject.
- **`touchstone-tools`** — the writer may never emit what the reader would
  refuse, and a singular answer is refused rather than regularized.
- **`interval-core`** — an enclosure may widen, never narrow.
- **`sparam-conformance`** — new cases need construction-derived labels, not
  another tool's opinion.

The most useful contribution to the portfolio is a **new pathological case** for
the corpus: a network that breaks a checker in a way the corpus does not yet
cover.

## Citing

Each repository carries a `CITATION.cff`. For the datasets:

```bibtex
@misc{screening_ceiling_2026,
  title  = {Screening Ceiling: Certified Regions and Counterexamples for
            Many-Body Coupling Extraction},
  author = {ChipletOS / Genesis contributors},
  year   = {2026},
  note   = {CC-BY-4.0}
}
```
