#!/usr/bin/env python3
"""Static UI and release-contract tests for the RapidMeta dashboard."""

from __future__ import annotations

import csv
import html.parser
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IdCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.scripts: list[str] = []
        self.inline_script_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if "id" in attr:
            self.ids.add(attr["id"] or "")
        if tag == "script":
            src = attr.get("src")
            if src:
                self.scripts.append(src)
            else:
                self.inline_script_count += 1


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_html_contract() -> None:
    html = read("index.html")
    parser = IdCollector()
    parser.feed(html)
    required_ids = {
        "effect-csv",
        "load-effects",
        "forest",
        "model-json",
        "analysis-state",
        "source-list",
        "readiness-list",
    }
    assert required_ids <= parser.ids
    assert parser.scripts == ["rapidmeta.js"]
    assert parser.inline_script_count == 0
    assert "Content-Security-Policy" in html
    assert "Benralizumab for hypereosinophilic syndrome" in html


def test_effect_csv_contract() -> None:
    rows = list(csv.DictReader((ROOT / "data/extracted/benralizumab_hes_effects.csv").open(encoding="utf-8", newline="")))
    assert len(rows) == 7
    included = [row for row in rows if row["pooled_include"] == "yes"]
    assert [row["study"] for row in included] == ["NATRON"]
    assert included[0]["effect_measure"] == "hazard_ratio"
    assert included[0]["effect"] == "0.35"
    assert included[0]["ci_lower"] == "0.18"
    assert included[0]["ci_upper"] == "0.69"
    assert any(row["nct_id"] == "NCT02130882" and row["pooled_include"] == "no" for row in rows)
    for row in rows:
        assert row["nct_id"].startswith("NCT")
        assert row["source_url"]
        float(row["effect"])
        float(row["ci_lower"])
        float(row["ci_upper"])


def test_style_meta_contract() -> None:
    meta = json.loads(read("style.meta"))
    assert meta["status"] == "release_prepared_single_study_primary"
    assert meta["project"]["slug"] == "benralizumab-hes"
    assert meta["review_question"]["outcome"] == "Time to first HES flare"
    assert meta["outputs"]["extraction_table"] == "data/extracted/benralizumab_hes_effects.csv"
    included = [row for row in meta["studies"] if row.get("pooled_include") is True]
    assert len(included) == 1
    assert included[0]["nct_id"] == "NCT04191304"
    assert any(row["nct_id"] == "NCT02130882" and row.get("pooled_include") is False for row in meta["studies"])


def test_aact_audit_contract() -> None:
    audit = json.loads(read("data/processed/aact_benralizumab_hes_audit.json"))
    assert audit["nct_ids"] == ["NCT02130882", "NCT04191304"]
    response = audit["hesil5r_response"]
    assert response["benralizumab_events"] == 9
    assert response["benralizumab_total"] == 10
    assert response["placebo_events"] == 3
    assert response["placebo_total"] == 10
    assert all(row["intervention_type"] == row["intervention_type"].lower() for row in audit["interventions"])


def test_node_engine_contract() -> None:
    result = subprocess.run(
        ["node", "tests/test_rapidmeta.js"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "rapidmeta tests passed" in result.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ui tests passed")
