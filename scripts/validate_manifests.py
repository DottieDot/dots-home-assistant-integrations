#!/usr/bin/env python3
"""Validate root hacs.json and every integration under custom_components/."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HACS_JSON = ROOT / "hacs.json"
CUSTOM_COMPONENTS = ROOT / "custom_components"


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


def _require_https_url(value: object, field: str, where: str) -> None:
    if not isinstance(value, str) or not value:
        _fail(f"{where} '{field}' must be a non-empty string URL")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        _fail(f"{where} '{field}' must be an absolute http(s) URL")


def validate_hacs_json() -> None:
    data = _load_json(HACS_JSON)
    if "name" not in data or not isinstance(data["name"], str) or not data["name"].strip():
        _fail("hacs.json requires a non-empty string 'name'")
    if "homeassistant" in data and not isinstance(data["homeassistant"], str):
        _fail("hacs.json 'homeassistant' must be a string when present")
    if "render_readme" in data and not isinstance(data["render_readme"], bool):
        _fail("hacs.json 'render_readme' must be a boolean when present")
    if data.get("zip_release"):
        filename = data.get("filename")
        if not isinstance(filename, str) or not filename.endswith(".zip"):
            _fail("hacs.json zip_release=true requires a .zip filename")
    print(f"OK  {HACS_JSON.relative_to(ROOT)}")


def iter_integrations() -> list[Path]:
    if not CUSTOM_COMPONENTS.is_dir():
        _fail("Missing custom_components/ directory")
    integrations = sorted(
        path
        for path in CUSTOM_COMPONENTS.iterdir()
        if path.is_dir() and not path.name.startswith(".") and path.name != "__pycache__"
    )
    if not integrations:
        _fail("No integrations found under custom_components/")
    return integrations


def validate_integration(integration_dir: Path) -> None:
    where = str(integration_dir.relative_to(ROOT) / "manifest.json")
    manifest_path = integration_dir / "manifest.json"
    data = _load_json(manifest_path)

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
            _fail(f"{where} missing required key '{key}'")
        if not isinstance(data[key], expected):
            _fail(f"{where} '{key}' must be {expected.__name__}")

    if not data["domain"].strip() or not data["name"].strip() or not data["version"].strip():
        _fail(f"{where} domain/name/version must be non-empty")
    if data["domain"] != integration_dir.name:
        _fail(
            f"{where} domain '{data['domain']}' must match folder name "
            f"'{integration_dir.name}'"
        )
    if not data["codeowners"]:
        _fail(f"{where} 'codeowners' must not be empty")
    _require_https_url(data["documentation"], "documentation", where)
    _require_https_url(data["issue_tracker"], "issue_tracker", where)
    print(f"OK  {manifest_path.relative_to(ROOT)}")

    brand_icon = integration_dir / "brand" / "icon.png"
    if not brand_icon.is_file():
        _fail(f"Missing brand icon: {brand_icon.relative_to(ROOT)}")
    if brand_icon.stat().st_size < 50:
        _fail(f"{brand_icon.relative_to(ROOT)} looks empty")
    header = brand_icon.read_bytes()[:8]
    if header != b"\x89PNG\r\n\x1a\n":
        _fail(f"{brand_icon.relative_to(ROOT)} is not a PNG file")
    print(f"OK  {brand_icon.relative_to(ROOT)}")

    readme = integration_dir / "README.md"
    if not readme.is_file():
        _fail(f"Missing integration README: {readme.relative_to(ROOT)}")
    print(f"OK  {readme.relative_to(ROOT)}")


def main() -> None:
    validate_hacs_json()
    integrations = iter_integrations()
    print(f"Found {len(integrations)} integration(s)")
    for integration_dir in integrations:
        validate_integration(integration_dir)
    print("All manifest checks passed.")


if __name__ == "__main__":
    main()
