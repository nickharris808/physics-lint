"""SARIF 2.1.0 output, so findings land inline on a GitHub pull request.

Why this lives in the meta-package rather than in each checker: SARIF is a
pure function of the structured JSON the checkers already emit, and three
independent copies of a serialization format is three chances to drift.

**No fabricated locations.** SARIF results usually carry a line and column, and
there is a strong pull to invent one so the annotation renders in the diff. A
physics failure does not happen at a line -- it happens at a *frequency* -- and
a Touchstone file's rows are not the unit a user reasons about. So results
point at the artifact with no ``region``, and the frequency goes in the message
where it is true. An annotation on line 1 would render more prettily and would
be a lie about where the problem is.
"""

from __future__ import annotations

from typing import Any

__all__ = ["SCHEMA", "VERSION", "sarif_from_sparam", "sarif_from_coupling"]

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
VERSION = "2.1.0"

_HELP = {
    "passivity":
        "The largest singular value of S exceeds 1, so the network delivers "
        "more power than is put into it. No passive device can do this.",
    "reciprocity":
        "S is not equal to its transpose. Usually a transposed reshape or a "
        "port-ordering bug -- but a ferrite isolator or circulator fails this "
        "legitimately, because its medium is non-reciprocal.",
    "energy_conservation":
        "Driving one port yields more power out than in, summed over the row. "
        "A global norm can average this away; the per-row check cannot.",
    "positive_real_z0":
        "The real part of the input impedance is negative at some frequency, "
        "which is negative resistance.",
    "group_delay_nonneg":
        "Negative group delay means the output precedes the input. Often an "
        "un-unwrapped phase rather than a genuinely non-causal model.",
    "screening_ceiling":
        "A predicted screening factor k = |C_full|/|C_iso| above 1 is "
        "anti-screening: it says a grounded conductor between two others "
        "increases their coupling. No passive arrangement can produce it.",
    "unreadable":
        "The file could not be parsed, so no verdict was reached. This is "
        "reported rather than passed over: a checker that skips what it "
        "cannot read silently approves it.",
}


def _rule(rule_id: str) -> dict[str, Any]:
    return {
        "id": rule_id,
        "name": rule_id,
        "shortDescription": {"text": rule_id.replace("_", " ")},
        "fullDescription": {"text": _HELP.get(rule_id, rule_id)},
        "defaultConfiguration": {"level": "error"},
        "properties": {"tags": ["physics", "correctness"]},
    }


def _run(tool_name: str, version: str, rules: list[dict], results: list[dict],
         info_uri: str) -> dict[str, Any]:
    return {
        "$schema": SCHEMA,
        "version": VERSION,
        "runs": [{
            "tool": {"driver": {
                "name": tool_name,
                "version": version,
                "informationUri": info_uri,
                "rules": rules,
            }},
            "results": results,
        }],
    }


def _result(rule_id: str, message: str, uri: str, level: str = "error") -> dict[str, Any]:
    return {
        "ruleId": rule_id,
        "level": level,
        "message": {"text": message},
        # No "region": see the module docstring. A physics failure has a
        # frequency, not a line, and inventing one would misreport the location.
        "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}}}],
    }


def sarif_from_sparam(report: dict[str, Any], version: str = "0") -> dict[str, Any]:
    """Convert `sparam-lint --json` output (either shape) to SARIF."""
    files = report.get("files", [report])
    results, seen = [], set()

    for entry in files:
        uri = entry.get("file", "<unknown>")
        if "error" in entry:
            seen.add("unreadable")
            results.append(_result("unreadable", entry["error"], uri))
            continue
        for law in entry.get("laws", []):
            if law.get("passed", True):
                continue
            rule = law.get("law") or law.get("name") or "unknown"
            seen.add(rule)
            results.append(_result(rule, law.get("message", rule), uri))

    return _run("sparam-lint", version, [_rule(r) for r in sorted(seen)], results,
                "https://github.com/nickharris808/sparam-lint")


def sarif_from_coupling(report: dict[str, Any], uri: str,
                        version: str = "0") -> dict[str, Any]:
    """Convert a `maxwell-lint --json` ceiling report to SARIF."""
    results, seen = [], set()
    n_viol = report.get("n_violations", 0)
    if n_viol:
        seen.add("screening_ceiling")
        worst = report.get("worst_pair")
        where = f" worst pair {tuple(worst)}." if worst else ""
        results.append(_result(
            "screening_ceiling",
            f"{n_viol} of {report.get('n_pairs', '?')} pairs exceed the "
            f"screening ceiling; max k = {report.get('max_k', float('nan')):.4f}."
            + where,
            uri,
        ))
    return _run("maxwell-lint", version, [_rule(r) for r in sorted(seen)], results,
                "https://github.com/nickharris808/maxwell-lint")
