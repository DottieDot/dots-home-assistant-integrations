"""Tests for RoomSyncManager filter sync behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT

from custom_components.homekit_room_sync.bridge_manager import (
    RoomSyncManager,
    empty_include_filter,
)
from custom_components.homekit_room_sync.const import (
    CONF_AREA_BRIDGES,
    CONF_AREAS,
    CONF_DOMAINS,
    CONF_ENTRY_ID,
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    HK_CONF_FILTER,
    HK_CONF_NAME,
    HK_CONF_PORT,
    HK_FILTER_INCLUDE_ENTITIES,
    HOMEKIT_DOMAIN,
)
from tests.conftest import (
    FakeArea,
    FakeAreaRegistry,
    FakeDeviceRegistry,
    FakeEntity,
    FakeEntityRegistry,
    make_hass,
)


def _sync_entry(**overrides) -> ConfigEntry:
    data = {
        CONF_AREAS: ["kitchen", "living"],
        CONF_DOMAINS: ["light", "switch"],
        CONF_INCLUDE_ENTITIES: [],
        CONF_EXCLUDE_ENTITIES: [],
        CONF_AREA_BRIDGES: {},
    }
    data.update(overrides)
    return ConfigEntry(
        domain="homekit_room_sync",
        title="HomeKit Room Sync",
        data=data,
        entry_id="sync1",
    )


def _homekit_entry(
    entry_id: str,
    name: str,
    port: int,
    entities: list[str] | None = None,
    unique_id: str | None = None,
) -> ConfigEntry:
    entities = entities or []
    return ConfigEntry(
        domain=HOMEKIT_DOMAIN,
        title=f"{name}:{port}",
        data={HK_CONF_NAME: name, HK_CONF_PORT: port},
        options={HK_CONF_FILTER: empty_include_filter(entities)},
        entry_id=entry_id,
        unique_id=unique_id,
    )


@pytest.mark.asyncio
async def test_sync_updates_options_filter():
    hass = make_hass()
    kitchen = _homekit_entry("hk_kitchen", "Kitchen", 21064, [])
    living = _homekit_entry("hk_living", "Living Room", 21065, [])
    hass.config_entries.add(kitchen)
    hass.config_entries.add(living)

    sync_entry = _sync_entry(
        **{
            CONF_AREA_BRIDGES: {
                "kitchen": {
                    "area_id": "kitchen",
                    CONF_ENTRY_ID: "hk_kitchen",
                    "bridge_name": "Kitchen",
                    "port": 21064,
                },
                "living": {
                    "area_id": "living",
                    CONF_ENTRY_ID: "hk_living",
                    "bridge_name": "Living Room",
                    "port": 21065,
                },
            }
        }
    )
    hass.config_entries.add(sync_entry)

    entities = FakeEntityRegistry(
        [
            FakeEntity("light.kitchen", area_id="kitchen"),
            FakeEntity("light.living", area_id="living"),
            FakeEntity("switch.kitchen", area_id="kitchen"),
        ]
    )

    with (
        patch(
            "custom_components.homekit_room_sync.helpers.er.async_get",
            return_value=entities,
        ),
        patch(
            "custom_components.homekit_room_sync.helpers.dr.async_get",
            return_value=FakeDeviceRegistry([]),
        ),
        patch(
            "custom_components.homekit_room_sync.helpers.ar.async_get",
            return_value=FakeAreaRegistry(
                [
                    FakeArea("kitchen", "Kitchen"),
                    FakeArea("living", "Living Room"),
                ]
            ),
        ),
    ):
        manager = RoomSyncManager(hass, sync_entry)
        summary = await manager.async_sync()

    assert summary["entities"] == 3
    assert summary["bridges_updated"] == 2
    kitchen_entities = kitchen.options[HK_CONF_FILTER][HK_FILTER_INCLUDE_ENTITIES]
    living_entities = living.options[HK_CONF_FILTER][HK_FILTER_INCLUDE_ENTITIES]
    assert kitchen_entities == ["light.kitchen", "switch.kitchen"]
    assert living_entities == ["light.living"]
    assert hass.config_entries.async_reload.await_count == 2


@pytest.mark.asyncio
async def test_move_removes_before_add():
    hass = make_hass()
    kitchen = _homekit_entry(
        "hk_kitchen", "Kitchen", 21064, ["light.move_me"]
    )
    living = _homekit_entry("hk_living", "Living Room", 21065, [])
    hass.config_entries.add(kitchen)
    hass.config_entries.add(living)

    sync_entry = _sync_entry(
        **{
            CONF_AREA_BRIDGES: {
                "kitchen": {
                    "area_id": "kitchen",
                    CONF_ENTRY_ID: "hk_kitchen",
                    "bridge_name": "Kitchen",
                    "port": 21064,
                },
                "living": {
                    "area_id": "living",
                    CONF_ENTRY_ID: "hk_living",
                    "bridge_name": "Living Room",
                    "port": 21065,
                },
            }
        }
    )
    reload_order: list[str] = []

    async def _reload(entry_id: str):
        reload_order.append(entry_id)

    hass.config_entries.async_reload = AsyncMock(side_effect=_reload)

    # Entity now lives in living room
    entities = FakeEntityRegistry(
        [FakeEntity("light.move_me", area_id="living")]
    )

    with (
        patch(
            "custom_components.homekit_room_sync.helpers.er.async_get",
            return_value=entities,
        ),
        patch(
            "custom_components.homekit_room_sync.helpers.dr.async_get",
            return_value=FakeDeviceRegistry([]),
        ),
        patch(
            "custom_components.homekit_room_sync.helpers.ar.async_get",
            return_value=FakeAreaRegistry(
                [
                    FakeArea("kitchen", "Kitchen"),
                    FakeArea("living", "Living Room"),
                ]
            ),
        ),
    ):
        manager = RoomSyncManager(hass, sync_entry)
        await manager.async_sync()

    assert kitchen.options[HK_CONF_FILTER][HK_FILTER_INCLUDE_ENTITIES] == []
    assert living.options[HK_CONF_FILTER][HK_FILTER_INCLUDE_ENTITIES] == [
        "light.move_me"
    ]
    # Removal (kitchen) must happen before addition (living)
    assert reload_order == ["hk_kitchen", "hk_living"]


@pytest.mark.asyncio
async def test_create_bridge_via_import_flow():
    hass = make_hass()
    sync_entry = _sync_entry(
        **{CONF_AREAS: ["office"], CONF_AREA_BRIDGES: {}}
    )
    hass.config_entries.add(sync_entry)

    created = _homekit_entry("hk_office", "Office", 21064, unique_id=None)

    async def _flow_init(domain, context=None, data=None):
        assert domain == HOMEKIT_DOMAIN
        assert context["source"] == SOURCE_IMPORT
        hass.config_entries.add(created)
        return {"type": "create_entry", "data": data}

    hass.config_entries.flow.async_init = AsyncMock(side_effect=_flow_init)

    with patch(
        "custom_components.homekit_room_sync.helpers.ar.async_get",
        return_value=FakeAreaRegistry([FakeArea("office", "Office")]),
    ):
        manager = RoomSyncManager(hass, sync_entry)
        # Avoid entity collection complications for this create-only assertion
        with patch(
            "custom_components.homekit_room_sync.bridge_manager.collect_area_entities",
            return_value={"office": set()},
        ):
            await manager.async_sync()

    assert created.unique_id == "homekit_room_sync_area_office"
    assert "office" in sync_entry.data[CONF_AREA_BRIDGES]
    assert sync_entry.data[CONF_AREA_BRIDGES]["office"][CONF_ENTRY_ID] == "hk_office"
