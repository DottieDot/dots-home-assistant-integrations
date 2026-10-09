"""Tests for helpers."""

from __future__ import annotations

from unittest.mock import patch

from custom_components.homekit_room_sync.helpers import (
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
    assert sanitize_bridge_name("Living Room") == "Living Room"
    assert sanitize_bridge_name("  ") == "Room"


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
            "custom_components.homekit_room_sync.helpers.er.async_get",
            return_value=entities,
        ),
        patch(
            "custom_components.homekit_room_sync.helpers.dr.async_get",
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


def test_collect_area_entities_excludes_by_label():
    hass = make_hass()
    entities = FakeEntityRegistry(
        [
            FakeEntity("light.kitchen", area_id="kitchen"),
            FakeEntity(
                "binary_sensor.apple_tv_keyboard",
                area_id="kitchen",
                labels={"no_homekit"},
            ),
            FakeEntity(
                "switch.also_tagged",
                area_id="kitchen",
                labels={"no_homekit", "other"},
            ),
        ]
    )
    devices = FakeDeviceRegistry([])

    with (
        patch(
            "custom_components.homekit_room_sync.helpers.er.async_get",
            return_value=entities,
        ),
        patch(
            "custom_components.homekit_room_sync.helpers.dr.async_get",
            return_value=devices,
        ),
    ):
        result = collect_area_entities(
            hass,
            area_ids={"kitchen"},
            domains={"light", "binary_sensor", "switch"},
            include_entities=set(),
            exclude_entities=set(),
            exclude_labels={"no_homekit"},
        )

    assert result["kitchen"] == {"light.kitchen"}


def test_parse_id_list_from_selector():
    from custom_components.homekit_room_sync.helpers import parse_id_list

    assert parse_id_list(["light.a", "switch.b", "light.a"]) == [
        "light.a",
        "switch.b",
    ]
    assert parse_id_list(None) == []
