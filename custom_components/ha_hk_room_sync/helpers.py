"""Shared helpers for HA HomeKit Room Sync."""

from __future__ import annotations

from typing import Any, Iterable

from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.entity_registry import RegistryEntry

from .const import DEFAULT_DOMAINS


def parse_entity_list(value: Any) -> list[str]:
    """Normalize a text/list field into sorted unique entity ids."""
    if value is None:
        return []
    if isinstance(value, list):
        source = ",".join(str(item) for item in value)
    else:
        source = str(value)
    parts = {part.strip() for part in source.replace("\n", ",").split(",")}
    return sorted(part for part in parts if part)


def entity_list_to_text(values: Iterable[str]) -> str:
    """Convert entity ids to a newline-separated text field."""
    return "\n".join(sorted({value for value in values if value}))


def resolve_entity_area_id(
    entry: RegistryEntry,
    device_reg: dr.DeviceRegistry,
) -> str | None:
    """Resolve an entity's effective area (entity area, else device area)."""
    if entry.area_id:
        return entry.area_id
    if not entry.device_id:
        return None
    device = device_reg.async_get(entry.device_id)
    return device.area_id if device else None


def is_exposible_entity(entry: RegistryEntry) -> bool:
    """Return True if the entity should be considered for HomeKit exposure."""
    if entry.disabled:
        return False
    if entry.hidden_by is not None:
        return False
    if entry.entity_category is not None:
        return False
    return True


def collect_area_entities(
    hass: HomeAssistant,
    area_ids: set[str],
    domains: set[str],
    include_entities: set[str],
    exclude_entities: set[str],
) -> dict[str, set[str]]:
    """Map each area_id to the set of entity_ids that belong there.

    Entities are included when:
    - their effective area is one of ``area_ids``
    - their domain is in ``domains`` OR they are in ``include_entities``
    - they are not in ``exclude_entities``
    - they are not disabled/hidden/config/diagnostic
    """
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    by_area: dict[str, set[str]] = {area_id: set() for area_id in area_ids}

    for entry in ent_reg.entities.values():
        if entry.entity_id in exclude_entities:
            continue
        if not is_exposible_entity(entry):
            # Explicit includes can still force exposure.
            if entry.entity_id not in include_entities:
                continue

        domain = split_entity_id(entry.entity_id)[0]
        forced = entry.entity_id in include_entities
        if not forced and domain not in domains:
            continue

        area_id = resolve_entity_area_id(entry, dev_reg)
        if area_id is None or area_id not in by_area:
            # Forced includes without a managed area are ignored for room sync;
            # they cannot be placed into a room bridge without an area.
            continue

        by_area[area_id].add(entry.entity_id)

    return by_area


def area_label(hass: HomeAssistant, area_id: str) -> str:
    """Return a human-readable area name."""
    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area and area.name else area_id


def sanitize_bridge_name(area_name: str) -> str:
    """Build a HomeKit bridge name from an area name."""
    # HomeKit bridge names must be unique and reasonably short.
    cleaned = " ".join(area_name.split())
    if not cleaned:
        cleaned = "Room"
    return f"HA {cleaned}"[:30]


def default_domains() -> list[str]:
    """Return a mutable copy of the default domain list."""
    return list(DEFAULT_DOMAINS)
