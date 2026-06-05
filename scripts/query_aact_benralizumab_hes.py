#!/usr/bin/env python3
"""Extract source records for the benralizumab HES RapidMeta project.

Reads the local AACT flat-file zip and writes a compact audit JSON. The script
fails closed if required tables, columns, NCT IDs, or source counts are absent.
"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AACT_ZIP = ROOT / "data" / "aact" / "20260604_export_ctgov.zip"
OUT_PATH = ROOT / "data" / "processed" / "aact_benralizumab_hes_audit.json"

NATRON = "NCT04191304"
HESIL5R = "NCT02130882"
NCT_IDS = {NATRON, HESIL5R}


def read_table(zip_file: zipfile.ZipFile, name: str, required: set[str]) -> list[dict[str, str]]:
    if name not in zip_file.namelist():
        raise SystemExit(f"AACT table missing from zip: {name}")
    with zip_file.open(name) as raw:
        text = (line.decode("utf-8-sig") for line in raw)
        reader = csv.DictReader(text, delimiter="|")
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{name} missing required columns: {sorted(missing)}")
        return [row for row in reader if row.get("nct_id") in NCT_IDS]


def one_row(rows: list[dict[str, str]], label: str, predicate) -> dict[str, str]:
    matches = [row for row in rows if predicate(row)]
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {label}; found {len(matches)}")
    return matches[0]


def main() -> int:
    if not AACT_ZIP.exists():
        raise SystemExit(f"AACT zip not found: {AACT_ZIP}")

    with zipfile.ZipFile(AACT_ZIP) as zf:
        studies = read_table(
            zf,
            "studies.txt",
            {
                "nct_id",
                "acronym",
                "brief_title",
                "official_title",
                "phase",
                "enrollment",
                "overall_status",
                "study_type",
                "primary_completion_date",
                "source_class",
            },
        )
        interventions = read_table(
            zf,
            "interventions.txt",
            {"nct_id", "intervention_type", "name", "description"},
        )
        outcomes = read_table(
            zf,
            "outcomes.txt",
            {"id", "nct_id", "outcome_type", "title", "description", "time_frame", "param_type"},
        )
        outcome_measurements = read_table(
            zf,
            "outcome_measurements.txt",
            {
                "nct_id",
                "outcome_id",
                "ctgov_group_code",
                "title",
                "units",
                "param_type",
                "param_value_num",
            },
        )
        outcome_counts = read_table(
            zf,
            "outcome_counts.txt",
            {"nct_id", "outcome_id", "ctgov_group_code", "scope", "units", "count"},
        )

    if {row["nct_id"] for row in studies} != NCT_IDS:
        raise SystemExit("Did not recover both required NCT IDs from studies.txt")

    for row in interventions:
        row["intervention_type"] = row["intervention_type"].lower()

    primary_response = one_row(
        outcomes,
        "HESIL5R eosinophil-response outcome",
        lambda row: row["nct_id"] == HESIL5R and "50% Reduction" in row["title"],
    )
    outcome_id = primary_response["id"]
    response_counts = {
        row["ctgov_group_code"]: int(row["count"])
        for row in outcome_counts
        if row["nct_id"] == HESIL5R and row["outcome_id"] == outcome_id and row["scope"] == "Measure"
    }
    response_values = {
        row["ctgov_group_code"]: float(row["param_value_num"])
        for row in outcome_measurements
        if row["nct_id"] == HESIL5R and row["outcome_id"] == outcome_id
    }
    if response_counts != {"OG000": 10, "OG001": 10}:
        raise SystemExit(f"Unexpected HESIL5R response denominators: {response_counts}")
    if response_values != {"OG000": 9.0, "OG001": 3.0}:
        raise SystemExit(f"Unexpected HESIL5R response counts: {response_values}")

    audit = {
        "aact_zip": str(AACT_ZIP.relative_to(ROOT)),
        "snapshot_exported": "2026-06-04",
        "nct_ids": sorted(NCT_IDS),
        "studies": sorted(studies, key=lambda row: row["nct_id"]),
        "interventions": sorted(interventions, key=lambda row: (row["nct_id"], row["name"].lower())),
        "hesil5r_response": {
            "nct_id": HESIL5R,
            "outcome_id": outcome_id,
            "endpoint": primary_response["title"],
            "benralizumab_events": int(response_values["OG000"]),
            "benralizumab_total": response_counts["OG000"],
            "placebo_events": int(response_values["OG001"]),
            "placebo_total": response_counts["OG001"],
        },
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
