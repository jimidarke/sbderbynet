"""Aggregate campaign reporting: pass/fail matrix, diff taxonomy, and the
std-vs-dropslowest scoring comparison."""

import glob
import os
from collections import Counter
from typing import List

from .util import load_json


def load_campaign(campaign_dir: str) -> List[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(campaign_dir, "v*", "verdict.json"))):
        verdict = load_json(path)
        verdict["_dir"] = os.path.dirname(path)
        out.append(verdict)
    return out


def scoring_comparison(campaign_dir: str) -> List[dict]:
    """Pair same-seed variants run under std and dropslowest configs and
    diff who advances out of each prelim."""
    artifacts = {}
    for path in sorted(glob.glob(os.path.join(campaign_dir, "v*", "artifact.json"))):
        a = load_json(path)
        artifacts[(a["seed"], a["config"])] = a

    rows = []
    seeds = sorted({k[0] for k in artifacts})
    for seed in seeds:
        std = artifacts.get((seed, "std"))
        drop = artifacts.get((seed, "dropslowest"))
        if not std or not drop:
            continue
        for classid_s in std.get("classes", {}):
            srounds = ((std.get("expected") or {}).get(classid_s) or {}).get("rounds", {})
            drounds = ((drop.get("expected") or {}).get(classid_s) or {}).get("rounds", {})
            for seq in srounds:
                s_set = set(srounds[seq].get("advancing", []))
                d_set = set((drounds.get(seq) or {}).get("advancing", []))
                if not s_set and not d_set:
                    continue
                if s_set != d_set:
                    rows.append({
                        "seed": seed, "classid": classid_s, "round": seq,
                        "only_under_std": sorted(s_set - d_set),
                        "only_under_dropslowest": sorted(d_set - s_set),
                    })
    return rows


def render_markdown(campaign_dir: str) -> str:
    verdicts = load_campaign(campaign_dir)
    lines = ["# Simulation Campaign Report", ""]
    if not verdicts:
        return "\n".join(lines + ["No variant verdicts found.", ""])

    passed = [v for v in verdicts if v["passed"]]
    lines += [
        f"**Variants:** {len(verdicts)}  |  "
        f"**Passed:** {len(passed)}  |  **Failed:** {len(verdicts) - len(passed)}",
        "",
        "## Variant results",
        "",
        "| Variant | Seed | Config | Result | Failed checks | Anomalies |",
        "|---|---|---|---|---|---|",
    ]
    failure_kinds = Counter()
    anomaly_kinds = Counter()
    for v in verdicts:
        failed_checks = [c["name"] for c in v["checks"] if not c["ok"]]
        failure_kinds.update(failed_checks)
        anomaly_kinds.update(a.get("type", "?") for a in v.get("anomalies", []))
        lines.append("| {} | {} | {} | {} | {} | {} |".format(
            os.path.basename(v["_dir"]), v["seed"], v["config"],
            "PASS" if v["passed"] else "**FAIL**",
            ", ".join(failed_checks) or "—",
            len(v.get("anomalies", [])) or "—"))

    lines += ["", "## Failure taxonomy", ""]
    if failure_kinds:
        for kind, n in failure_kinds.most_common():
            lines.append(f"- `{kind}`: {n} variant(s)")
    else:
        lines.append("- none")

    lines += ["", "## Anomaly taxonomy (non-fatal)", ""]
    if anomaly_kinds:
        for kind, n in anomaly_kinds.most_common():
            lines.append(f"- `{kind}`: {n} occurrence(s)")
    else:
        lines.append("- none")

    dropouts = [f for v in verdicts
                for f in v.get("dropout_eligibility_findings", [])]
    if dropouts:
        lines += ["", "## Pull-forward dropout eligibility findings", "",
                  f"{len(dropouts)} case(s) where a withdrawn racer advanced "
                  "on a partial-run aggregate. The engine needs a dropout "
                  "eligibility filter before race day.", ""]

    comparison = scoring_comparison(campaign_dir)
    lines += ["", "## Scoring method comparison (std vs drop-slowest)", ""]
    if comparison:
        lines += ["Same seed, same injected times — different advancing sets:",
                  "",
                  "| Seed | Class | Round | Advances only under std | Only under drop-slowest |",
                  "|---|---|---|---|---|"]
        for row in comparison:
            lines.append("| {seed} | {classid} | {round} | {a} | {b} |".format(
                a=row["only_under_std"], b=row["only_under_dropslowest"], **row))
        lines += ["",
                  "Note: under drop-slowest a single DNF is erased by the "
                  "drop; under total-time it is a ~100s penalty. Expect the "
                  "diff rows above to be dominated by one-DNF racers.", ""]
    else:
        lines.append("No paired std/dropslowest seeds (or no differences found).")

    lines.append("")
    return "\n".join(lines)
