"""Status sensors for HA HomeKit Room Sync."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .bridge_manager import get_area_bridge_map
from .const import DOMAIN
from .helpers import area_label


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up status sensors."""
    manager = hass.data[DOMAIN][entry.entry_id]["manager"]
    async_add_entities(
        [
            RoomSyncSummarySensor(hass, entry, manager),
            RoomSyncBridgesSensor(hass, entry, manager),
        ]
    )


class _RoomSyncBaseSensor(SensorEntity):
    """Base sensor with periodic refresh from manager state."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, manager) -> None:
        self.hass = hass
        self._entry = entry
        self._manager = manager
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="HA HomeKit Room Sync",
            manufacturer="HA HomeKit Room Sync",
            model="Area ↔ Room synchronizer",
        )

    async def async_added_to_hass(self) -> None:
        """Refresh periodically so UI reflects sync activity."""
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_refresh, timedelta(seconds=30)
            )
        )
        self._async_write_ha_state_from_manager()

    @callback
    def _async_refresh(self, _now=None) -> None:
        self._async_write_ha_state_from_manager()

    @callback
    def _async_write_ha_state_from_manager(self) -> None:
        self.async_write_ha_state()


class RoomSyncSummarySensor(_RoomSyncBaseSensor):
    """Shows how many entities are currently synced."""

    _attr_name = "Synced entities"
    _attr_icon = "mdi:sync"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, manager) -> None:
        super().__init__(hass, entry, manager)
        self._attr_unique_id = f"{entry.entry_id}_synced_entities"

    @property
    def native_value(self) -> int:
        """Return entity count from last sync summary."""
        return int(self._manager.last_sync_summary.get("entities", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose last sync details."""
        summary = self._manager.last_sync_summary
        return {
            "areas": summary.get("areas", 0),
            "bridges_updated": summary.get("bridges_updated", 0),
            "bridges_created": summary.get("bridges_created", 0),
        }


class RoomSyncBridgesSensor(_RoomSyncBaseSensor):
    """Shows managed bridge count and pairing map."""

    _attr_name = "Managed bridges"
    _attr_icon = "mdi:bridge"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, manager) -> None:
        super().__init__(hass, entry, manager)
        self._attr_unique_id = f"{entry.entry_id}_managed_bridges"

    @property
    def native_value(self) -> int:
        """Return number of managed area bridges."""
        return len(get_area_bridge_map(self._entry))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """List bridges with suggested HomeKit room names."""
        bridges = []
        for item in self._manager.pairing_instructions():
            bridges.append(
                {
                    "area": item["area_name"],
                    "bridge": item["bridge_name"],
                    "port": item["port"],
                    "homekit_room": item["homekit_room"],
                }
            )
        # Keep a simple map too for templates
        room_map = {
            area_label(self.hass, area_id): meta.get("bridge_name")
            for area_id, meta in get_area_bridge_map(self._entry).items()
        }
        return {"bridges": bridges, "area_to_bridge": room_map}
