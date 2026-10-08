"""Create and synchronize per-area HomeKit bridges."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from typing import Any

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    BRIDGE_UNIQUE_ID_PREFIX,
    CONF_AREA_BRIDGES,
    CONF_AREA_ID,
    CONF_AREAS,
    CONF_BRIDGE_NAME,
    CONF_DOMAINS,
    CONF_ENTRY_ID,
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_PORT,
    DEFAULT_PORT_START,
    HK_CONF_EXCLUDE_ACCESSORY_MODE,
    HK_CONF_FILTER,
    HK_CONF_MODE,
    HK_CONF_NAME,
    HK_CONF_PORT,
    HK_FILTER_EXCLUDE_DOMAINS,
    HK_FILTER_EXCLUDE_ENTITIES,
    HK_FILTER_EXCLUDE_ENTITY_GLOBS,
    HK_FILTER_INCLUDE_DOMAINS,
    HK_FILTER_INCLUDE_ENTITIES,
    HK_FILTER_INCLUDE_ENTITY_GLOBS,
    HK_INCLUDE_NONE_GLOB,
    HK_MODE_BRIDGE,
    HOMEKIT_DOMAIN,
    PORT_SEARCH_RANGE,
)
from .helpers import (
    area_label,
    collect_area_entities,
    sanitize_bridge_name,
)

_LOGGER = logging.getLogger(__name__)


def include_only_filter(entity_ids: list[str]) -> dict[str, list[str]]:
    """Build a HomeKit filter that exposes only the given entities.

    An entirely empty Home Assistant entity filter means "include everything".
    When ``entity_ids`` is empty we keep a never-matching include glob so the
    bridge stays in include-only mode and exposes nothing.
    """
    entities = sorted({entity_id for entity_id in entity_ids if entity_id})
    return {
        HK_FILTER_INCLUDE_DOMAINS: [],
        HK_FILTER_INCLUDE_ENTITIES: entities,
        HK_FILTER_EXCLUDE_DOMAINS: [],
        HK_FILTER_EXCLUDE_ENTITIES: [],
        HK_FILTER_INCLUDE_ENTITY_GLOBS: (
            [] if entities else [HK_INCLUDE_NONE_GLOB]
        ),
        HK_FILTER_EXCLUDE_ENTITY_GLOBS: [],
    }


def empty_include_filter(entity_ids: list[str]) -> dict[str, list[str]]:
    """Alias for :func:`include_only_filter` (kept for older call sites/tests)."""
    return include_only_filter(entity_ids)


def filter_has_include_rules(filt: dict[str, Any] | None) -> bool:
    """Return True if the filter is in include-only mode (not expose-all)."""
    if not isinstance(filt, dict):
        return False
    return bool(
        filt.get(HK_FILTER_INCLUDE_ENTITIES)
        or filt.get(HK_FILTER_INCLUDE_DOMAINS)
        or filt.get(HK_FILTER_INCLUDE_ENTITY_GLOBS)
    )


def _used_homekit_ports(hass: HomeAssistant) -> set[int]:
    ports: set[int] = set()
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        port = entry.data.get(HK_CONF_PORT)
        if isinstance(port, int):
            ports.add(port)
    return ports


def _used_homekit_names(hass: HomeAssistant) -> set[str]:
    names: set[str] = set()
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        name = entry.data.get(HK_CONF_NAME)
        if isinstance(name, str) and name:
            names.add(name)
    return names


def allocate_port(hass: HomeAssistant, preferred: int | None = None) -> int:
    """Allocate an unused HomeKit TCP port."""
    used = _used_homekit_ports(hass)
    start = preferred if preferred is not None else DEFAULT_PORT_START
    for offset in range(PORT_SEARCH_RANGE):
        candidate = start + offset
        if candidate not in used:
            return candidate
    raise HomeAssistantError("Unable to allocate a free HomeKit bridge port")


def unique_bridge_name(hass: HomeAssistant, desired: str) -> str:
    """Ensure the bridge name is unique among HomeKit entries."""
    used = _used_homekit_names(hass)
    if desired not in used:
        return desired
    for index in range(2, 100):
        candidate = f"{desired[:27]} {index}"
        if candidate not in used:
            return candidate
    raise HomeAssistantError(f"Unable to allocate a unique HomeKit name for {desired}")


def bridge_unique_id(area_id: str) -> str:
    """Return the stable unique_id used for a managed area bridge."""
    return f"{BRIDGE_UNIQUE_ID_PREFIX}{area_id}"


def find_bridge_by_unique_id(hass: HomeAssistant, area_id: str) -> ConfigEntry | None:
    """Find an existing HomeKit entry created for this area."""
    target = bridge_unique_id(area_id)
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        if entry.unique_id == target:
            return entry
    return None


def get_area_bridge_map(entry: ConfigEntry) -> dict[str, dict[str, Any]]:
    """Return area_id -> bridge metadata from the sync config entry."""
    raw = entry.data.get(CONF_AREA_BRIDGES, {})
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for area_id, meta in raw.items():
        if isinstance(meta, dict):
            result[str(area_id)] = dict(meta)
    return result


class RoomSyncManager:
    """Keep one HomeKit bridge per HA area in sync with area membership."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._lock = asyncio.Lock()
        self._set_suppress_reload: Any | None = None
        self.last_sync_summary: dict[str, Any] = {
            "areas": 0,
            "entities": 0,
            "bridges_updated": 0,
            "bridges_created": 0,
        }

    def set_suppress_reload_callback(self, callback) -> None:
        """Register a callback used while persisting bridge mappings."""
        self._set_suppress_reload = callback

    @property
    def area_ids(self) -> list[str]:
        """Configured area ids."""
        return list(self.entry.data.get(CONF_AREAS, []))

    @property
    def domains(self) -> set[str]:
        """Configured domains."""
        return set(self.entry.data.get(CONF_DOMAINS, []))

    @property
    def include_entities(self) -> set[str]:
        """Manual include overrides."""
        return set(self.entry.data.get(CONF_INCLUDE_ENTITIES, []))

    @property
    def exclude_entities(self) -> set[str]:
        """Manual exclude overrides."""
        return set(self.entry.data.get(CONF_EXCLUDE_ENTITIES, []))

    async def async_ensure_bridges(self) -> dict[str, dict[str, Any]]:
        """Create missing HomeKit bridges for configured areas."""
        async with self._lock:
            membership = self._collect_membership()
            return await self._async_ensure_bridges_unlocked(membership)

    async def async_sync(self) -> dict[str, Any]:
        """Ensure bridges exist and push current entity membership."""
        async with self._lock:
            membership = self._collect_membership()
            area_bridges = await self._async_ensure_bridges_unlocked(membership)
            return await self._async_sync_unlocked(area_bridges, membership)

    def _collect_membership(self) -> dict[str, set[str]]:
        """Compute current area → entity membership."""
        return collect_area_entities(
            self.hass,
            set(self.area_ids),
            self.domains,
            self.include_entities,
            self.exclude_entities,
        )

    async def _async_ensure_bridges_unlocked(
        self, membership: dict[str, set[str]] | None = None
    ) -> dict[str, dict[str, Any]]:
        area_bridges = get_area_bridge_map(self.entry)
        created = 0
        changed = False
        if membership is None:
            membership = self._collect_membership()

        for area_id in self.area_ids:
            existing_meta = area_bridges.get(area_id)
            homekit_entry = None

            if existing_meta and existing_meta.get(CONF_ENTRY_ID):
                homekit_entry = self.hass.config_entries.async_get_entry(
                    str(existing_meta[CONF_ENTRY_ID])
                )

            if homekit_entry is None:
                homekit_entry = find_bridge_by_unique_id(self.hass, area_id)

            if homekit_entry is None:
                initial_entities = sorted(membership.get(area_id, set()))
                homekit_entry = await self._async_create_bridge(
                    area_id, initial_entities
                )
                created += 1
                changed = True
            else:
                # Keep mapping metadata fresh even if the bridge already existed.
                meta = {
                    CONF_AREA_ID: area_id,
                    CONF_ENTRY_ID: homekit_entry.entry_id,
                    CONF_BRIDGE_NAME: homekit_entry.data.get(HK_CONF_NAME),
                    CONF_PORT: homekit_entry.data.get(HK_CONF_PORT),
                }
                if area_bridges.get(area_id) != meta:
                    area_bridges[area_id] = meta
                    changed = True

            if homekit_entry is not None:
                area_bridges[area_id] = {
                    CONF_AREA_ID: area_id,
                    CONF_ENTRY_ID: homekit_entry.entry_id,
                    CONF_BRIDGE_NAME: homekit_entry.data.get(HK_CONF_NAME),
                    CONF_PORT: homekit_entry.data.get(HK_CONF_PORT),
                }

        # Drop mappings for areas no longer selected (do not delete bridges).
        stale = [area_id for area_id in area_bridges if area_id not in self.area_ids]
        for area_id in stale:
            area_bridges.pop(area_id, None)
            changed = True
            _LOGGER.info(
                "Stopped managing HomeKit bridge for area %s "
                "(bridge left in place; remove manually if desired)",
                area_id,
            )

        if changed:
            self._persist_area_bridges(area_bridges)

        self.last_sync_summary["bridges_created"] = created
        return area_bridges

    async def _async_create_bridge(
        self, area_id: str, entity_ids: list[str] | None = None
    ) -> ConfigEntry:
        """Create a HomeKit bridge config entry for an area via import flow.

        The bridge is created with an include-only filter for ``entity_ids`` so
        HomeKit never briefly advertises the entire home (an empty HA filter
        means include-everything).
        """
        label = area_label(self.hass, area_id)
        desired_name = sanitize_bridge_name(label)
        name = unique_bridge_name(self.hass, desired_name)
        port = allocate_port(self.hass)
        initial_entities = list(entity_ids or [])

        import_data = {
            HK_CONF_NAME: name,
            HK_CONF_PORT: port,
            HK_CONF_MODE: HK_MODE_BRIDGE,
            HK_CONF_EXCLUDE_ACCESSORY_MODE: True,
            HK_CONF_FILTER: include_only_filter(initial_entities),
        }

        _LOGGER.info(
            "Creating HomeKit bridge '%s' on port %s for area '%s'",
            name,
            port,
            label,
        )

        result = await self.hass.config_entries.flow.async_init(
            HOMEKIT_DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=import_data,
        )

        result_type = str(result.get("type", ""))
        if not result_type.endswith("create_entry"):
            raise HomeAssistantError(
                f"Failed to create HomeKit bridge for area {label}: {result}"
            )

        # Locate the entry we just created (by name+port).
        homekit_entry = None
        for entry in self.hass.config_entries.async_entries(HOMEKIT_DOMAIN):
            if (
                entry.data.get(HK_CONF_NAME) == name
                and entry.data.get(HK_CONF_PORT) == port
            ):
                homekit_entry = entry
                break

        if homekit_entry is None:
            raise HomeAssistantError(
                f"HomeKit bridge for area {label} was created but could not be found"
            )

        # Stamp a stable unique_id so we can rediscover the bridge later.
        self.hass.config_entries.async_update_entry(
            homekit_entry,
            unique_id=bridge_unique_id(area_id),
            title=f"{name}:{port}",
        )
        return homekit_entry

    async def _async_sync_unlocked(
        self,
        area_bridges: dict[str, dict[str, Any]],
        membership: dict[str, set[str]] | None = None,
    ) -> dict[str, Any]:
        if membership is None:
            membership = self._collect_membership()

        # Two-pass sync so moves remove from the old bridge before adding to the new.
        # Pass 1: shrink filters (removals / moves-out)
        # Pass 2: grow filters (additions / moves-in)
        updates_pass1: list[tuple[ConfigEntry, list[str]]] = []
        updates_pass2: list[tuple[ConfigEntry, list[str]]] = []

        for area_id, meta in area_bridges.items():
            entry_id = meta.get(CONF_ENTRY_ID)
            if not entry_id:
                continue
            homekit_entry = self.hass.config_entries.async_get_entry(str(entry_id))
            if homekit_entry is None:
                _LOGGER.warning(
                    "HomeKit bridge for area %s (%s) is missing", area_id, entry_id
                )
                continue

            desired = sorted(membership.get(area_id, set()))
            current = self._current_include_entities(homekit_entry)
            desired_set = set(desired)
            current_set = set(current)
            unsafe_empty = self._has_unsafe_empty_filter(homekit_entry)

            if desired_set == current_set and not unsafe_empty:
                continue

            if desired_set == current_set and unsafe_empty:
                # Heal bridges stuck on an empty (= expose-all) HomeKit filter.
                _LOGGER.warning(
                    "HomeKit bridge %s had an empty include filter "
                    "(Home Assistant treats that as expose-all); rewriting",
                    homekit_entry.title,
                )
                updates_pass1.append((homekit_entry, desired))
                continue

            removed = current_set - desired_set
            added = desired_set - current_set

            if removed and not added:
                updates_pass1.append((homekit_entry, desired))
            elif added and not removed:
                updates_pass2.append((homekit_entry, desired))
            else:
                # Mixed change (or move involving this bridge): shrink first.
                interim = sorted(current_set - removed)
                if set(interim) != current_set or unsafe_empty:
                    updates_pass1.append((homekit_entry, interim))
                if set(interim) != desired_set:
                    updates_pass2.append((homekit_entry, desired))

        bridges_updated = 0
        for homekit_entry, entities in updates_pass1:
            if await self._async_apply_filter(homekit_entry, entities):
                bridges_updated += 1

        for homekit_entry, entities in updates_pass2:
            if await self._async_apply_filter(homekit_entry, entities):
                bridges_updated += 1

        entity_count = sum(len(v) for v in membership.values())
        summary = {
            "areas": len(self.area_ids),
            "entities": entity_count,
            "bridges_updated": bridges_updated,
            "bridges_created": self.last_sync_summary.get("bridges_created", 0),
            "membership": {area: sorted(ids) for area, ids in membership.items()},
        }
        self.last_sync_summary = summary
        _LOGGER.info(
            "Room sync complete: %s areas, %s entities, %s bridge(s) updated",
            summary["areas"],
            summary["entities"],
            summary["bridges_updated"],
        )
        return summary

    def _active_filter(self, homekit_entry: ConfigEntry) -> dict[str, Any] | None:
        """Return the active HomeKit filter dict from options (preferred) or data."""
        for container in (homekit_entry.options, homekit_entry.data):
            filt = container.get(HK_CONF_FILTER)
            if isinstance(filt, dict):
                return filt
        return None

    def _has_unsafe_empty_filter(self, homekit_entry: ConfigEntry) -> bool:
        """True when the bridge filter would expose every entity (no includes)."""
        filt = self._active_filter(homekit_entry)
        return not filter_has_include_rules(filt)

    def _current_include_entities(self, homekit_entry: ConfigEntry) -> list[str]:
        """Read the active include_entities list from options (preferred) or data."""
        filt = self._active_filter(homekit_entry)
        if isinstance(filt, dict) and HK_FILTER_INCLUDE_ENTITIES in filt:
            entities = filt.get(HK_FILTER_INCLUDE_ENTITIES) or []
            return sorted(str(item) for item in entities)
        return []

    async def _async_apply_filter(
        self, homekit_entry: ConfigEntry, entity_ids: list[str]
    ) -> bool:
        """Write include_entities into HomeKit options and reload the bridge."""
        new_filter = include_only_filter(entity_ids)

        # HomeKit runtime reads filter from options. Keep data clean of filter keys
        # once options exist (matches core's import-from-data migration).
        new_options = deepcopy(dict(homekit_entry.options))
        new_data = deepcopy(dict(homekit_entry.data))
        new_options[HK_CONF_FILTER] = new_filter
        new_options[HK_CONF_MODE] = HK_MODE_BRIDGE
        new_data.pop(HK_CONF_FILTER, None)

        if (
            new_options == dict(homekit_entry.options)
            and new_data == dict(homekit_entry.data)
        ):
            return False

        self.hass.config_entries.async_update_entry(
            homekit_entry,
            data=new_data,
            options=new_options,
        )
        await self.hass.config_entries.async_reload(homekit_entry.entry_id)
        _LOGGER.debug(
            "Updated HomeKit bridge %s with %s entities",
            homekit_entry.title,
            len(entity_ids),
        )
        return True

    def _persist_area_bridges(self, area_bridges: dict[str, dict[str, Any]]) -> None:
        data = deepcopy(dict(self.entry.data))
        data[CONF_AREA_BRIDGES] = area_bridges
        if self._set_suppress_reload is not None:
            self._set_suppress_reload(True)
        try:
            self.hass.config_entries.async_update_entry(self.entry, data=data)
        finally:
            if self._set_suppress_reload is not None:
                self._set_suppress_reload(False)

    def pairing_instructions(self) -> list[dict[str, Any]]:
        """Return pairing hints for managed bridges."""
        instructions: list[dict[str, Any]] = []
        for area_id, meta in get_area_bridge_map(self.entry).items():
            instructions.append(
                {
                    "area_id": area_id,
                    "area_name": area_label(self.hass, area_id),
                    "bridge_name": meta.get(CONF_BRIDGE_NAME),
                    "port": meta.get(CONF_PORT),
                    "entry_id": meta.get(CONF_ENTRY_ID),
                    "homekit_room": area_label(self.hass, area_id),
                }
            )
        instructions.sort(key=lambda item: str(item.get("area_name", "")).lower())
        return instructions
