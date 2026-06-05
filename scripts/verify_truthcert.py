#!/usr/bin/env python3
"""Verify artifact hashes and optional HMAC signature in truthcert.json."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRUTHCERT = ROOT / "truthcert.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    cert = json.loads(TRUTHCERT.read_text(encoding="utf-8"))
    for name, expected in cert["artifacts"].items():
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"missing artifact: {name}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"hash mismatch: {name}")

    signature = cert.get("signature", {})
    if signature.get("type") == "hmac-sha256":
        key = os.environ.get("TRUTHCERT_HMAC_KEY")
        if not key:
            print("hashes OK; HMAC signature present but TRUTHCERT_HMAC_KEY not set")
            return 0
        unsigned = dict(cert)
        unsigned.pop("signature", None)
        canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hmac.new(key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(actual, signature.get("digest", "")):
            raise SystemExit("HMAC signature mismatch")
        print("truthcert hashes and HMAC OK")
        return 0

    print("truthcert hashes OK; manifest unsigned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
