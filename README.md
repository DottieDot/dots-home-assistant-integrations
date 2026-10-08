# Home Assistant custom integrations

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Monorepo for Home Assistant custom integrations. Each integration lives under
[`custom_components/`](custom_components/) as a standard HA domain package.

## Integrations

| Integration | Domain | Description |
|-------------|--------|-------------|
| [HA HomeKit Room Sync](custom_components/ha_hk_room_sync/README.md) | `ha_hk_room_sync` | Syncs Home Assistant Areas to Apple HomeKit rooms via one HomeKit Bridge per Area |

## Install

### HACS (HomeKit Room Sync)

HACS only manages **one** integration per repository. This repo’s HACS entry is
**HA HomeKit Room Sync**.

1. Open **HACS → Integrations**.
2. ⋮ menu → **Custom repositories**.
3. Add this repository URL as category **Integration**.
4. Install **HA HomeKit Room Sync**, then restart Home Assistant.

The repository must be **public**, with a GitHub description, topics, and a
detected open-source license on the default branch.

### Manual (any / all integrations)

Copy one or more folders from `custom_components/` into your Home Assistant
`config/custom_components/` directory and restart.

## Adding another integration

See [`custom_components/README.md`](custom_components/README.md) for the folder
layout and checklist. CI validates every `custom_components/*/manifest.json`
and brand icon automatically.

If the new integration should also be installable via HACS, give it its own
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

## License

MIT — see [LICENSE](LICENSE).
