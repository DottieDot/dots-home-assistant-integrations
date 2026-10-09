# HomeKit Room Sync

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../LICENSE)

> Mostly vibe-coded for personal use and not thoroughly reviewed. Use at your own risk.

Home Assistant custom integration that keeps **Home Assistant Areas** aligned with **Apple HomeKit rooms**.

HomeKit Bridge can expose your devices to the Home app, but it cannot assign accessories to rooms by itself — room membership lives in Apple Home. This integration uses the proven **one HomeKit Bridge per Area** pattern so room placement works after a single pairing step per room.

## What you get

| Requirement | How it works |
|-------------|--------------|
| One-time setup per room | Creates one HomeKit Bridge per selected HA Area. Pair each bridge once in the Home app into the matching room. |
| New HA devices appear in HK | Entities added to an Area are added to that Area’s bridge filter and show up in that room. |
| Removed HA devices leave HK | Entities removed / unassigned are dropped from the bridge and disappear from Home. |
| Move between rooms | Changing an entity/device Area moves it from one bridge to another (and therefore to the new room). |
| HA as source of truth | Bridge membership is always recomputed from HA Areas. Manual Home-app room moves are not pushed back into HA (see limitations). |

## How it works

```text
HA Area "Living Room" ──creates/manages──▶ HomeKit Bridge "Living Room"
                                              │
                                              │  (you pair once into
                                              │   Apple Home room
                                              │   "Living Room")
                                              ▼
                                   New accessories on that bridge
                                   land in "Living Room" automatically
```

1. The integration creates (or reuses) a **HomeKit Bridge config entry per Area**.
2. It writes each bridge’s `options.filter.include_entities` from current Area membership.
3. Registry changes (entity / device / area) trigger a debounced sync + bridge reload.
4. Moves are applied in two passes (remove from old bridge, then add to new) to avoid accessory ID clashes.

## Installation

### HACS (recommended)

1. Open **HACS → Integrations**.
2. ⋮ menu → **Custom repositories**.
3. Add this repository URL as category **Integration**.
4. Search for **HomeKit Room Sync**, install, then **restart Home Assistant**.

### Manual

Copy this folder (`homekit_room_sync`) into your Home Assistant `config/custom_components/` directory and restart.

## Setup

1. Make sure the built-in **HomeKit Bridge** integration is available.
2. Create your **Areas** in Home Assistant (Settings → Areas).
3. Settings → Devices & services → **Add Integration** → **HomeKit Room Sync**.
4. Select the Areas to manage and the entity domains to expose.
5. After setup, open the persistent notification (or the **Managed bridges** sensor attributes) for the list of bridges.
6. In the Apple **Home** app, add each bridge and assign it to the **same-named room**.

That pairing step is the only per-room setup. Afterward, Area changes in HA drive HomeKit.

## Configuration options

All options use Home Assistant pickers (areas, domains, entities, labels) — no need to type IDs by hand.

| Option | Description |
|--------|-------------|
| **Areas** | HA Areas that each get a dedicated HomeKit Bridge |
| **Domains** | Entity domains eligible for exposure (lights, switches, …). Scene and script are available but **off by default** because HomeKit Bridge can only expose them as switches, not as native Apple Home scenes. |
| **Include entities** | Always expose these entities (still must belong to a managed Area) |
| **Exclude entities** | Never expose these entities |
| **Exclude labels** | Never expose entities that carry any of these HA labels (e.g. tag junk with `no-homekit`) |

Labels on the **entity** or its parent **device** both count (area labels do not roll up). Create labels under **Settings → Areas, labels & zones**.

## Services

- `homekit_room_sync.sync` — recompute membership and update bridges (optional `area_id`)
- `homekit_room_sync.ensure_bridges` — create any missing per-area bridges, then sync

## Sensors

- **Synced entities** — count from the last sync (+ attributes for areas / updates)
- **Managed bridges** — bridge count (+ attributes listing area → bridge → suggested HomeKit room)

## Migrating from a single HomeKit Bridge

1. Install and configure this integration for your Areas.
2. Pair each new per-room bridge into the matching Apple Home room.
3. Narrow or remove the old catch-all bridge’s entity filter so devices are not exposed twice.
4. Prefer managing Areas in HA going forward; avoid manually re-rooming accessories in the Home app.

## Requirements

- Home Assistant **2024.1+**
- Built-in **HomeKit Bridge** integration
- Apple Home hub (HomePod / Apple TV / iPad) as usual for remote HomeKit access

## Limitations

- **Apple Home controls room assignment.** Bridges cannot call `HMHome.assignAccessory`. The per-bridge-per-room pattern is what makes automatic placement work after pairing.
- If you manually drag an accessory to another room inside the Home app, HA cannot see or revert that. Prefer moving the device’s **Area in Home Assistant**.
- Moving a device between Areas removes it from one bridge and adds it to another. HomeKit treats that as a new accessory on the destination bridge — Home scenes/automations that referenced the old tile may need to be recreated.
- Cameras generally need HomeKit **accessory mode** and are not included in the default domain list.
- HA scenes/scripts cannot become native Apple Home scenes via HomeKit Bridge (HAP limitation); they only appear as switches if you enable those domains.
- Each bridge has a HomeKit limit of ~150 accessories; per-room bridges help stay under that.

## Troubleshooting

1. Confirm each Area bridge is paired and assigned to the matching HomeKit room.
2. Check that the entity’s Area (or its device’s Area) is one of the managed Areas.
3. Check the entity domain is enabled in the integration options, the entity is not hidden/disabled/config/diagnostic, and neither the entity nor its device carries an excluded label.
4. Call `homekit_room_sync.sync` and watch Home Assistant logs.
5. Force-close and reopen the Home app if the UI looks stale.

### Bridge showed my entire home in Apple Home

Home Assistant treats a HomeKit filter with **no include rules** as “expose everything.” Older builds of this integration could create (or empty) a per-area bridge with that unsafe filter, so pairing pulled in the whole house.

This integration now always writes an include-only filter (with a never-matching sentinel when an area has no entities) and creates bridges with the Area’s entities already applied.

**Recovery:**

1. Update HomeKit Room Sync, restart Home Assistant, then call `homekit_room_sync.sync`.
2. In **Settings → Devices & services → HomeKit Bridge**, open the room bridge and confirm only that Area’s entities are listed.
3. In the Apple **Home** app, remove the mis-paired bridge, then pair it again into the matching room.

```yaml
logger:
  default: info
  logs:
    custom_components.homekit_room_sync: debug
```

## Acknowledgements

Inspired by earlier community work on Area ↔ HomeKit bridge sync:

- [lcrostarosa/homekit-room-sync](https://github.com/lcrostarosa/homekit-room-sync)
- [aequitas/homekit-room-sync](https://github.com/aequitas/homekit-room-sync)
