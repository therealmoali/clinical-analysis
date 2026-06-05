#!/usr/bin/env python3
"""Create a lightweight release manifest with artifact hashes.

If TRUTHCERT_HMAC_KEY is set, the manifest includes an HMAC-SHA256 signature.
The key itself is never written.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "truthcert.json"
ARTIFACTS = [
    "index.html",
    "rapidmeta.js",
    "rapidmeta.css",
    "style.meta",
    "E156.md",
    "RELEASE_CHECKLIST.md",
    "README.md",
    ".nojekyll",
    "docs/source-audit.md",
    "data/extracted/benralizumab_hes_effects.csv",
    "data/processed/aact_benralizumab_hes_audit.json",
    "tests/test_rapidmeta.js",
    "tests/test_ui.py",
    "scripts/query_aact_benralizumab_hes.py",
    "scripts/build_benralizumab_effects.py",
    "scripts/make_truthcert.py",
    "scripts/verify_truthcert.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    missing = [name for name in ARTIFACTS if not (ROOT / name).exists()]
    if missing:
        raise SystemExit(f"Cannot make TruthCert; missing artifacts: {missing}")

    payload = {
        "schema": "truthcert.light.v1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project": "benralizumab-hes",
        "claim": "NATRON provides 2026 phase 3 randomized evidence that benralizumab reduces time to first HES flare versus placebo plus background therapy: HR 0.35 (95% CI 0.18 to 0.69).",
        "limitations": [
            "Single-study primary effect preview.",
            "No pooled primary clinical meta-analysis claimed.",
            "HESIL5R biomarker response RR is supporting evidence only."
        ],
        "artifacts": {name: sha256(ROOT / name) for name in ARTIFACTS},
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    key = os.environ.get("TRUTHCERT_HMAC_KEY")
    if key:
        payload["signature"] = {
            "type": "hmac-sha256",
            "digest": hmac.new(key.encode("utf-8"), canonical, hashlib.sha256).hexdigest(),
        }
    else:
        payload["signature"] = {
            "type": "unsigned",
            "reason": "TRUTHCERT_HMAC_KEY not set in this process",
        }
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({payload['signature']['type']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
