"""HA HomeKit Room Sync integration.

Creates one HomeKit Bridge per Home Assistant Area and keeps each bridge's
entity filter synchronized with area membership. After a one-time pairing of
each bridge into the matching Apple Home room, new/moved/removed devices
follow Home Assistant automatically.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.typing import ConfigType

from .bridge_manager import RoomSyncManager
from .const import (
    ATTR_AREA_ID,
    DOMAIN,
    EVENT_AREA_REGISTRY_UPDATED,
    EVENT_DEVICE_REGISTRY_UPDATED,
    EVENT_ENTITY_REGISTRY_UPDATED,
    SERVICE_ENSURE_BRIDGES,
    SERVICE_SYNC,
    SYNC_DEBOUNCE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the integration domain (YAML not used)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA HomeKit Room Sync from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    manager = RoomSyncManager(hass, entry)
    entry_data: dict[str, Any] = {
        "manager": manager,
        "listeners": [],
        "debounce_cancel": None,
        "suppress_reload": False,
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data
    manager.set_suppress_reload_callback(
        lambda value: entry_data.__setitem__("suppress_reload", value)
    )

    _register_services(hass)

    @callback
    def _schedule_sync(_event: Event | None = None) -> None:
        """Debounce registry changes into a single sync."""
        data = hass.data[DOMAIN].get(entry.entry_id)
        if data is None:
            return

        if data["debounce_cancel"] is not None:
            data["debounce_cancel"]()
            data["debounce_cancel"] = None

        async def _run(_now: Any) -> None:
            current = hass.data[DOMAIN].get(entry.entry_id)
            if current is None:
                return
            current["debounce_cancel"] = None
            await manager.async_sync()
            await _async_notify_pairing(hass, manager)

        data["debounce_cancel"] = async_call_later(
            hass, SYNC_DEBOUNCE_SECONDS, _run
        )

    listeners = [
        hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, _schedule_sync),
        hass.bus.async_listen(EVENT_AREA_REGISTRY_UPDATED, _schedule_sync),
        hass.bus.async_listen(EVENT_DEVICE_REGISTRY_UPDATED, _schedule_sync),
    ]
    entry_data["listeners"] = listeners

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Initial ensure + sync
    await manager.async_sync()
    await _async_notify_pairing(hass, manager)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data is None:
        return unload_ok

    if data.get("debounce_cancel") is not None:
        data["debounce_cancel"]()

    for unsub in data.get("listeners", []):
        unsub()

    # Remove services only when no entries remain.
    remaining = [
        key for key in hass.data.get(DOMAIN, {}) if key != "services_registered"
    ]
    if not remaining and hass.data.get(DOMAIN, {}).get("services_registered"):
        hass.services.async_remove(DOMAIN, SERVICE_SYNC)
        hass.services.async_remove(DOMAIN, SERVICE_ENSURE_BRIDGES)
        hass.data[DOMAIN].pop("services_registered", None)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options/data change, unless the manager is persisting mappings."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data and data.get("suppress_reload"):
        return
    await hass.config_entries.async_reload(entry.entry_id)


def _register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.data[DOMAIN].get("services_registered"):
        return

    async def _handle_sync(call: ServiceCall) -> None:
        area_id = call.data.get(ATTR_AREA_ID)
        for key, data in list(hass.data.get(DOMAIN, {}).items()):
            if key == "services_registered" or not isinstance(data, dict):
                continue
            manager: RoomSyncManager = data["manager"]
            if area_id and area_id not in manager.area_ids:
                continue
            await manager.async_sync()

    async def _handle_ensure(call: ServiceCall) -> None:
        for key, data in list(hass.data.get(DOMAIN, {}).items()):
            if key == "services_registered" or not isinstance(data, dict):
                continue
            manager: RoomSyncManager = data["manager"]
            await manager.async_ensure_bridges()
            await manager.async_sync()
            await _async_notify_pairing(hass, manager)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC,
        _handle_sync,
        schema=vol.Schema({vol.Optional(ATTR_AREA_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ENSURE_BRIDGES,
        _handle_ensure,
        schema=vol.Schema({}),
    )
    hass.data[DOMAIN]["services_registered"] = True


async def _async_notify_pairing(
    hass: HomeAssistant, manager: RoomSyncManager
) -> None:
    """Publish a persistent notification with one-time pairing instructions."""
    instructions = manager.pairing_instructions()
    if not instructions:
        return

    lines = [
        "### HA HomeKit Room Sync — one-time pairing",
        "",
        "Pair each bridge below in the Apple **Home** app and assign it to the "
        "matching room. After that, devices added/moved/removed in Home Assistant "
        "stay in sync automatically.",
        "",
    ]
    for item in instructions:
        lines.append(
            f"- **{item['area_name']}** → bridge `{item['bridge_name']}` "
            f"(port `{item['port']}`) → put this bridge in HomeKit room "
            f"**{item['homekit_room']}**"
        )
    lines.extend(
        [
            "",
            "Tips:",
            "- Open **Settings → Devices & services → HomeKit Bridge** to see pairing codes/QR.",
            "- New accessories on a paired bridge appear in that bridge's HomeKit room.",
            "- Moving a device between HA Areas moves it between bridges (and rooms).",
        ]
    )

    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "notification_id": f"{DOMAIN}_pairing",
            "title": "HA HomeKit Room Sync",
            "message": "\n".join(lines),
        },
        blocking=False,
    )
