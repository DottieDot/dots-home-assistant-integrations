# Dot's Home Assistant integrations

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Disclaimer:** This repository is mostly vibe-coded, has not been thoroughly
> reviewed, and was built for my personal Home Assistant setup. Use at your own
> risk. Expect rough edges, incomplete docs, and breaking changes.

Monorepo for Home Assistant custom integrations. Each integration lives under
[`custom_components/`](custom_components/) as a standard domain package.

## Integrations

| Integration | Domain | Description |
|-------------|--------|-------------|
| [HomeKit Room Sync](custom_components/homekit_room_sync/README.md) | `homekit_room_sync` | Syncs Home Assistant Areas to Apple HomeKit rooms via one HomeKit Bridge per Area |

## Install

### HACS (HomeKit Room Sync)

HACS only manages **one** integration per repository. This repo’s HACS entry is
**HomeKit Room Sync**.

1. Open **HACS → Integrations**.
2. ⋮ menu → **Custom repositories**.
3. Add `https://github.com/DottieDot/dots-home-assistant-integrations` as category **Integration**.
4. Install **HomeKit Room Sync**, then restart Home Assistant.

Or use a My Home Assistant link after the first release is published.

### Manual (any / all integrations)

Copy one or more folders from `custom_components/` into your Home Assistant
`config/custom_components/` directory and restart.

## Releases

HACS picks up versions from **GitHub Releases** (not bare tags).

1. Bump / choose a semver tag such as `v1.0.0`.
2. Publish a GitHub Release for that tag (UI, `gh release create`, or the
   release workflow below).
3. CI attaches a `homekit_room_sync.zip` asset and stamps `manifest.json`
   with the release version so HACS installs a matching build.

## Adding another integration

See [`custom_components/README.md`](custom_components/README.md). CI validates
every `custom_components/*/manifest.json` and brand icon automatically.

If a new integration should also be installable via HACS, give it its own
public GitHub repository — HACS does not support multi-integration monorepos as
a single custom repository listing.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
python scripts/validate_manifests.py
```

## Acknowledgements

- [lcrostarosa/homekit-room-sync](https://github.com/lcrostarosa/homekit-room-sync)
  (also known as [aequitas/homekit-room-sync](https://github.com/aequitas/homekit-room-sync)) —
  earlier HACS/community work on Area ↔ HomeKit bridge sync that inspired parts
  of this integration’s approach and structure.
- [Home Assistant](https://www.home-assistant.io/) and [HACS](https://hacs.xyz/)

## License

MIT — see [LICENSE](LICENSE).
