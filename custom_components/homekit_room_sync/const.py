"""Constants for HomeKit Room Sync."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "homekit_room_sync"
HOMEKIT_DOMAIN: Final = "homekit"

CONF_AREAS: Final = "areas"
CONF_DOMAINS: Final = "domains"
CONF_EXCLUDE_ENTITIES: Final = "exclude_entities"
CONF_INCLUDE_ENTITIES: Final = "include_entities"
CONF_AREA_BRIDGES: Final = "area_bridges"
CONF_CREATE_BRIDGES: Final = "create_bridges"

# Keys stored per managed area bridge mapping
CONF_AREA_ID: Final = "area_id"
CONF_ENTRY_ID: Final = "entry_id"
CONF_BRIDGE_NAME: Final = "bridge_name"
CONF_PORT: Final = "port"

# HomeKit config entry keys
HK_CONF_FILTER: Final = "filter"
HK_CONF_MODE: Final = "mode"
HK_CONF_NAME: Final = "name"
HK_CONF_PORT: Final = "port"
HK_CONF_EXCLUDE_ACCESSORY_MODE: Final = "exclude_accessory_mode"
HK_MODE_BRIDGE: Final = "bridge"
HK_FILTER_INCLUDE_DOMAINS: Final = "include_domains"
HK_FILTER_INCLUDE_ENTITIES: Final = "include_entities"
HK_FILTER_EXCLUDE_DOMAINS: Final = "exclude_domains"
HK_FILTER_EXCLUDE_ENTITIES: Final = "exclude_entities"
HK_FILTER_INCLUDE_ENTITY_GLOBS: Final = "include_entity_globs"
HK_FILTER_EXCLUDE_ENTITY_GLOBS: Final = "exclude_entity_globs"

# Home Assistant's EntityFilter treats a completely empty filter as
# "include everything". When a per-area bridge should expose nothing, we keep
# this never-matching include glob so the filter stays in include-only mode.
HK_INCLUDE_NONE_GLOB: Final = "homekit_room_sync.none"

EVENT_ENTITY_REGISTRY_UPDATED: Final = "entity_registry_updated"
EVENT_AREA_REGISTRY_UPDATED: Final = "area_registry_updated"
EVENT_DEVICE_REGISTRY_UPDATED: Final = "device_registry_updated"

SYNC_DEBOUNCE_SECONDS: Final = 2.0
DEFAULT_PORT_START: Final = 21064
PORT_SEARCH_RANGE: Final = 1000

# Stable unique_id prefix for HomeKit bridges we create
BRIDGE_UNIQUE_ID_PREFIX: Final = f"{DOMAIN}_area_"

# Domains commonly exposed on HomeKit bridges (cameras need accessory mode).
DEFAULT_DOMAINS: Final = [
    "alarm_control_panel",
    "binary_sensor",
    "button",
    "climate",
    "cover",
    "fan",
    "humidifier",
    "input_boolean",
    "light",
    "lock",
    "media_player",
    "remote",
    "scene",
    "script",
    "sensor",
    "switch",
    "vacuum",
    "valve",
    "water_heater",
]

SERVICE_SYNC: Final = "sync"
SERVICE_ENSURE_BRIDGES: Final = "ensure_bridges"

ATTR_AREA_ID: Final = "area_id"
