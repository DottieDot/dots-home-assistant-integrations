#!/usr/bin/env python3
"""Local validation of hacs.json and the integration manifest.

The HACS GitHub Action downloads these files via raw.githubusercontent.com,
which fails for private repositories (and for branch names containing '/').
This script keeps those checks covered in CI by validating the checked-out
files directly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HACS_JSON = ROOT / "hacs.json"
MANIFEST = ROOT / "custom_components" / "ha_hk_room_sync" / "manifest.json"
BRAND_ICON = ROOT / "custom_components" / "ha_hk_room_sync" / "brand" / "icon.png"


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _load_json(path: Path) -> dict:
    if not path.is_file():
        _fail(f"Missing required file: {path.relative_to(ROOT)}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        _fail(f"Invalid JSON in {path.relative_to(ROOT)}: {err}")
    if not isinstance(data, dict):
        _fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return data


def _require_https_url(value: object, field: str) -> None:
    if not isinstance(value, str) or not value:
        _fail(f"manifest.json '{field}' must be a non-empty string URL")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        _fail(f"manifest.json '{field}' must be an absolute http(s) URL")


def validate_hacs_json() -> None:
    data = _load_json(HACS_JSON)
    if "name" not in data or not isinstance(data["name"], str) or not data["name"].strip():
        _fail("hacs.json requires a non-empty string 'name'")
    if "homeassistant" in data and not isinstance(data["homeassistant"], str):
        _fail("hacs.json 'homeassistant' must be a string when present")
    if "render_readme" in data and not isinstance(data["render_readme"], bool):
        _fail("hacs.json 'render_readme' must be a boolean when present")
    print(f"OK  {HACS_JSON.relative_to(ROOT)}")


def validate_integration_manifest() -> None:
    data = _load_json(MANIFEST)
    required = {
        "domain": str,
        "name": str,
        "documentation": str,
        "issue_tracker": str,
        "codeowners": list,
        "version": str,
    }
    for key, expected in required.items():
        if key not in data:
            _fail(f"manifest.json missing required key '{key}'")
        if not isinstance(data[key], expected):
            _fail(f"manifest.json '{key}' must be {expected.__name__}")
    if not data["domain"].strip() or not data["name"].strip() or not data["version"].strip():
        _fail("manifest.json domain/name/version must be non-empty")
    if not data["codeowners"]:
        _fail("manifest.json 'codeowners' must not be empty")
    _require_https_url(data["documentation"], "documentation")
    _require_https_url(data["issue_tracker"], "issue_tracker")
    print(f"OK  {MANIFEST.relative_to(ROOT)}")


def validate_brand_icon() -> None:
    if not BRAND_ICON.is_file():
        _fail(f"Missing brand icon: {BRAND_ICON.relative_to(ROOT)}")
    if BRAND_ICON.stat().st_size < 50:
        _fail("brand/icon.png looks empty")
    header = BRAND_ICON.read_bytes()[:8]
    if header != b"\x89PNG\r\n\x1a\n":
        _fail("brand/icon.png is not a PNG file")
    print(f"OK  {BRAND_ICON.relative_to(ROOT)}")


def main() -> None:
    validate_hacs_json()
    validate_integration_manifest()
    validate_brand_icon()
    print("All manifest checks passed.")


if __name__ == "__main__":
    main()
