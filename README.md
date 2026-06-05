# Benralizumab HES RapidMeta

Static RapidMeta-style workspace for benralizumab add-on therapy in FIP1L1::PDGFRA-negative hypereosinophilic syndrome.

## Files

- `index.html` — browser dashboard with Protocol, Data, Analysis, and Audit tabs.
- `rapidmeta.js` — dependency-free parsing, pooling, forest-rendering, and audit state.
- `rapidmeta.css` — app styling.
- `style.meta` — machine-readable project contract and release gates.
- `data/extracted/benralizumab_hes_effects.csv` — source-audited extracted effects.
- `data/processed/aact_benralizumab_hes_audit.json` — regenerated AACT evidence audit.
- `docs/source-audit.md` — identifier, endpoint, and hardcode-disclosure audit.
- `E156.md` — micro-paper draft.
- `RELEASE_CHECKLIST.md` — ship gate status and claim limits.
- `truthcert.json` — artifact hash manifest, signed when `TRUTHCERT_HMAC_KEY` is available.
- `data/aact/20260604_export_ctgov.zip` — local AACT flat-file export, ignored by git.

## Use

Open `index.html` in a browser. It starts with the source-verified NATRON primary endpoint:

```csv
study,effect,ci_lower,ci_upper
NATRON,0.35,0.18,0.69
```

The dashboard computes fixed-effect and DerSimonian-Laird random-effects estimates on the log scale. With only NATRON eligible for the primary HR endpoint, it reports a single-study effect preview rather than a multi-study pooled estimate.

The earlier randomized HES study (`NCT02130882`) is retained as supporting registry-derived evidence because its endpoint is eosinophil response, not time to first HES flare.

## Verify

```bash
python3 scripts/query_aact_benralizumab_hes.py
python3 scripts/build_benralizumab_effects.py
node tests/test_rapidmeta.js
python3 tests/test_ui.py
node --check rapidmeta.js
python3 -m json.tool style.meta
python3 scripts/make_truthcert.py
python3 scripts/verify_truthcert.py
sentinel scan --repo /Users/mo/clinical-analysis
```
