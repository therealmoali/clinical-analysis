# Benralizumab HES Source Audit

## Topic

Benralizumab add-on therapy versus placebo plus background therapy for FIP1L1::PDGFRA-negative hypereosinophilic syndrome.

## Verified Trial Records

| Trial | NCT ID | Source | Status in project |
|---|---|---|---|
| NATRON | NCT04191304 | AACT `studies.txt`; Nature Medicine 2026 OA article | Primary HR row included |
| HESIL5R | NCT02130882 | AACT `studies.txt`, `outcomes.txt`, `outcome_measurements.txt`, `outcome_counts.txt` | Registry-derived secondary evidence only |

Regenerated AACT audit artifact: `data/processed/aact_benralizumab_hes_audit.json`.

## Extracted Effects

| Study | Endpoint | Effect | Include in primary pool | Reason |
|---|---|---:|---|---|
| NATRON | Time to first HES flare | HR 0.35 (0.18 to 0.69) | Yes | Prespecified phase 3 primary endpoint |
| HESIL5R | 50% eosinophil reduction at 12 weeks | RR 3.00 (1.14 to 7.91) | No | Biomarker response endpoint; not comparable to time-to-flare HR |
| NATRON | Time to first hematologic relapse | HR 0.08 (0.03 to 0.20) | No | Secondary endpoint |
| NATRON | Hematologic relapse during double-blind period | OR 0.05 (0.02 to 0.13) | No | Secondary endpoint |
| NATRON | AEC below 500 cells per microliter for 24 weeks | OR 87.87 (26.09 to 295.97) | No | Biomarker endpoint |
| NATRON | Corticosteroid dose increase | OR 0.35 (0.16 to 0.73) | No | Secondary endpoint |
| NATRON | PROMIS Fatigue at week 24 | MD -4.72 (-7.64 to -1.80) | No | Continuous patient-reported endpoint |

## Static-vs-Dynamic Hardcode Disclosure

| Item | Static or dynamic | Rationale | Update path |
|---|---|---|---|
| NATRON primary HR in `rapidmeta.js` default textarea | Static source-backed value | Lets the static app open with the chosen primary evidence row; not simulated | Update from `data/extracted/benralizumab_hes_effects.csv` after source review |
| AACT zip path and file count | Static source-backed metadata | Captures the verified local snapshot used in this session | Refresh after replacing AACT snapshot |
| HESIL5R RR calculation | Static derived value | Derived from AACT counts: 9/10 vs 3/10, log-RR Wald CI | Recompute if AACT snapshot changes |
| Dashboard pooling | Dynamic | Computed in browser from loaded CSV rows | Covered by `tests/test_rapidmeta.js` |
| NATRON secondary endpoints in effects CSV | Static source-backed values | Captures additional article-reported endpoints for audit only | Do not include in primary pool unless endpoint/effect measure contract changes |

## Notes

- The current primary analysis is a single-study phase 3 effect preview, not a multi-study pooled meta-analysis, because no second comparable time-to-first-HES-flare HR was identified.
- The phase 2 randomized HES study supports biological activity but uses a different endpoint and effect measure, so it is retained as supporting evidence only.
- Re-run `python3 scripts/query_aact_benralizumab_hes.py` and `python3 scripts/build_benralizumab_effects.py` after replacing the AACT snapshot.
