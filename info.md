# HomeKit Room Sync

Keeps Home Assistant Areas synchronized with Apple HomeKit rooms by managing
**one HomeKit Bridge per Area**.

> Mostly vibe-coded for personal use — not thoroughly reviewed. Use at your own risk.

This repository is a monorepo of custom integrations. HACS installs the
**HomeKit Room Sync** integration from it.

## One-time setup

1. Install via HACS and restart Home Assistant.
2. Add the integration and select your Areas.
3. Pair each created HomeKit Bridge in the Apple Home app into the matching room.

After that, adding, removing, or moving devices between Areas in Home Assistant
updates HomeKit automatically.

Full docs: [`custom_components/homekit_room_sync/README.md`](custom_components/homekit_room_sync/README.md)
