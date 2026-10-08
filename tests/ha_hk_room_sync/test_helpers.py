"""Tests for helpers."""

from __future__ import annotations

from unittest.mock import patch

from custom_components.ha_hk_room_sync.helpers import (
    collect_area_entities,
    parse_entity_list,
    resolve_entity_area_id,
    sanitize_bridge_name,
)
from tests.conftest import (
    FakeDevice,
    FakeDeviceRegistry,
    FakeEntity,
    FakeEntityRegistry,
    make_hass,
)


def test_parse_entity_list_multiline():
    assert parse_entity_list("light.a\nswitch.b, light.a") == [
        "light.a",
        "switch.b",
    ]


def test_sanitize_bridge_name():
    assert sanitize_bridge_name("Living Room") == "HA Living Room"
    assert sanitize_bridge_name("  ") == "HA Room"


def test_resolve_entity_area_prefers_entity():
    entity = FakeEntity("light.x", area_id="kitchen", device_id="dev1")
    devices = FakeDeviceRegistry([FakeDevice("dev1", area_id="living")])
    assert resolve_entity_area_id(entity, devices) == "kitchen"


def test_resolve_entity_area_falls_back_to_device():
    entity = FakeEntity("light.x", area_id=None, device_id="dev1")
    devices = FakeDeviceRegistry([FakeDevice("dev1", area_id="living")])
    assert resolve_entity_area_id(entity, devices) == "living"


def test_collect_area_entities_filters_domains_and_excludes():
    hass = make_hass()
    entities = FakeEntityRegistry(
        [
            FakeEntity("light.kitchen", area_id="kitchen"),
            FakeEntity("switch.kitchen", area_id="kitchen"),
            FakeEntity("sensor.kitchen", area_id="kitchen"),
            FakeEntity("light.living", area_id="living"),
            FakeEntity("light.hidden", area_id="kitchen", hidden_by="user"),
            FakeEntity("light.excluded", area_id="kitchen"),
        ]
    )
    devices = FakeDeviceRegistry([])

    with (
        patch(
            "custom_components.ha_hk_room_sync.helpers.er.async_get",
            return_value=entities,
        ),
        patch(
            "custom_components.ha_hk_room_sync.helpers.dr.async_get",
            return_value=devices,
        ),
    ):
        result = collect_area_entities(
            hass,
            area_ids={"kitchen", "living"},
            domains={"light", "switch"},
            include_entities=set(),
            exclude_entities={"light.excluded"},
        )

    assert result["kitchen"] == {"light.kitchen", "switch.kitchen"}
    assert result["living"] == {"light.living"}
    assert "sensor.kitchen" not in result["kitchen"]
    assert "light.hidden" not in result["kitchen"]
