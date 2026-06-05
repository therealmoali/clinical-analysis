#!/usr/bin/env python3
"""Build the source-backed effects table for the benralizumab HES project."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "data" / "processed" / "aact_benralizumab_hes_audit.json"
OUT_PATH = ROOT / "data" / "extracted" / "benralizumab_hes_effects.csv"

# Static article constants, intentionally disclosed. These are source-backed
# values from the open-access NATRON article and are checked by tests/docs.
NATRON_ARTICLE_URL = "https://www.nature.com/articles/s41591-026-04315-8"
NATRON_ROWS = [
    {
        "study": "NATRON",
        "nct_id": "NCT04191304",
        "year": "2026",
        "endpoint": "Time to first HES flare",
        "effect_measure": "hazard_ratio",
        "effect": "0.35",
        "ci_lower": "0.18",
        "ci_upper": "0.69",
        "source_url": NATRON_ARTICLE_URL,
        "source_type": "open_access_article",
        "pooled_include": "yes",
        "notes": "Primary endpoint from NATRON phase 3 article; 133 randomized patients; add-on benralizumab vs placebo.",
    },
    {
        "study": "NATRON",
        "nct_id": "NCT04191304",
        "year": "2026",
        "endpoint": "Time to first hematologic relapse",
        "effect_measure": "hazard_ratio",
        "effect": "0.08",
        "ci_lower": "0.03",
        "ci_upper": "0.20",
        "source_url": NATRON_ARTICLE_URL,
        "source_type": "open_access_article",
        "pooled_include": "no",
        "notes": "Key secondary endpoint from NATRON; not pooled with primary flare endpoint.",
    },
    {
        "study": "NATRON",
        "nct_id": "NCT04191304",
        "year": "2026",
        "endpoint": "Hematologic relapse during double-blind period",
        "effect_measure": "odds_ratio",
        "effect": "0.05",
        "ci_lower": "0.02",
        "ci_upper": "0.13",
        "source_url": NATRON_ARTICLE_URL,
        "source_type": "open_access_article",
        "pooled_include": "no",
        "notes": "Article reports 9.0% (6/67) vs 63.6% (42/66); endpoint differs from primary flare endpoint.",
    },
    {
        "study": "NATRON",
        "nct_id": "NCT04191304",
        "year": "2026",
        "endpoint": "AEC below 500 cells per microliter for 24 weeks",
        "effect_measure": "odds_ratio",
        "effect": "87.87",
        "ci_lower": "26.09",
        "ci_upper": "295.97",
        "source_url": NATRON_ARTICLE_URL,
        "source_type": "open_access_article",
        "pooled_include": "no",
        "notes": "Biomarker endpoint from NATRON; not pooled with clinical flare endpoint.",
    },
    {
        "study": "NATRON",
        "nct_id": "NCT04191304",
        "year": "2026",
        "endpoint": "Required an increase in corticosteroid dose",
        "effect_measure": "odds_ratio",
        "effect": "0.35",
        "ci_lower": "0.16",
        "ci_upper": "0.73",
        "source_url": NATRON_ARTICLE_URL,
        "source_type": "open_access_article",
        "pooled_include": "no",
        "notes": "Secondary endpoint from NATRON; 25.4% (17/67) vs 48.5% (32/66).",
    },
    {
        "study": "NATRON",
        "nct_id": "NCT04191304",
        "year": "2026",
        "endpoint": "PROMIS Fatigue change at week 24",
        "effect_measure": "mean_difference",
        "effect": "-4.72",
        "ci_lower": "-7.64",
        "ci_upper": "-1.80",
        "source_url": NATRON_ARTICLE_URL,
        "source_type": "open_access_article",
        "pooled_include": "no",
        "notes": "Key secondary patient-reported outcome; not pooled with ratio measures.",
    },
]


def ensure_audit() -> dict:
    if not AUDIT_PATH.exists():
        subprocess.run([sys.executable, "scripts/query_aact_benralizumab_hes.py"], cwd=ROOT, check=True)
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def risk_ratio_wald(events_t: int, total_t: int, events_c: int, total_c: int) -> tuple[float, float, float]:
    if min(events_t, total_t, events_c, total_c) <= 0:
        raise SystemExit("Risk-ratio calculation requires positive counts")
    risk_t = events_t / total_t
    risk_c = events_c / total_c
    rr = risk_t / risk_c
    se_log_rr = math.sqrt((1 / events_t) - (1 / total_t) + (1 / events_c) - (1 / total_c))
    lo = math.exp(math.log(rr) - 1.96 * se_log_rr)
    hi = math.exp(math.log(rr) + 1.96 * se_log_rr)
    return rr, lo, hi


def main() -> int:
    audit = ensure_audit()
    response = audit["hesil5r_response"]
    rr, lo, hi = risk_ratio_wald(
        response["benralizumab_events"],
        response["benralizumab_total"],
        response["placebo_events"],
        response["placebo_total"],
    )

    rows = [
        NATRON_ROWS[0],
        {
            "study": "HESIL5R",
            "nct_id": "NCT02130882",
            "year": "2019",
            "endpoint": "50% reduction in peripheral blood eosinophilia at 12 weeks",
            "effect_measure": "risk_ratio",
            "effect": f"{rr:.2f}",
            "ci_lower": f"{lo:.2f}",
            "ci_upper": f"{hi:.2f}",
            "source_url": "data/aact/20260604_export_ctgov.zip",
            "source_type": "aact_registry_derived",
            "pooled_include": "no",
            "notes": "Derived from AACT outcome_measurements and outcome_counts: 9/10 benralizumab vs 3/10 placebo. Not pooled with NATRON HR because endpoint and effect measure differ.",
        },
        *NATRON_ROWS[1:],
    ]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
