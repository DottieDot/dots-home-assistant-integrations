# HA HomeKit Room Sync

Keeps Home Assistant Areas synchronized with Apple HomeKit rooms by managing
**one HomeKit Bridge per Area**.

This repository is a monorepo of custom integrations. HACS installs the
**HA HomeKit Room Sync** integration from it.

## One-time setup

1. Install via HACS and restart Home Assistant.
2. Add the integration and select your Areas.
3. Pair each created HomeKit Bridge in the Apple Home app into the matching room.

After that, adding, removing, or moving devices between Areas in Home Assistant
updates HomeKit automatically.

Full docs: [`custom_components/ha_hk_room_sync/README.md`](custom_components/ha_hk_room_sync/README.md)
