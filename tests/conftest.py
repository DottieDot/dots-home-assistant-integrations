"""Minimal Home Assistant stand-ins for unit tests."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock


def _install_ha_stubs() -> None:
    """Install lightweight homeassistant modules if the real package is absent."""
    if "homeassistant" in sys.modules:
        return

    ha = types.ModuleType("homeassistant")
    sys.modules["homeassistant"] = ha

    # config_entries
    config_entries = types.ModuleType("homeassistant.config_entries")

    class ConfigEntry:  # noqa: D401
        def __init__(
            self,
            *,
            domain: str = "",
            title: str = "",
            data: dict | None = None,
            options: dict | None = None,
            entry_id: str = "entry",
            unique_id: str | None = None,
            source: str = "user",
            version: int = 1,
        ) -> None:
            self.domain = domain
            self.title = title
            self.data = data or {}
            self.options = options or {}
            self.entry_id = entry_id
            self.unique_id = unique_id
            self.source = source
            self.version = version

        def async_on_unload(self, _cb) -> None:
            return None

        def add_update_listener(self, _cb):
            return lambda: None

    class ConfigFlow:
        def __init_subclass__(cls, domain: str | None = None, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.domain = domain

        async def async_set_unique_id(self, _uid):
            return None

        def _abort_if_unique_id_configured(self):
            return None

        def async_abort(self, reason: str):
            return {"type": "abort", "reason": reason}

        def async_create_entry(self, title: str, data: dict):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    class OptionsFlow:
        hass = None
        handler = None

    class ConfigFlowResult(dict):
        pass

    SOURCE_IMPORT = "import"
    config_entries.ConfigEntry = ConfigEntry
    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.ConfigFlowResult = ConfigFlowResult
    config_entries.SOURCE_IMPORT = SOURCE_IMPORT
    sys.modules["homeassistant.config_entries"] = config_entries

    # core
    core = types.ModuleType("homeassistant.core")

    class HomeAssistant:
        pass

    class Event:
        pass

    class ServiceCall:
        def __init__(self, data=None):
            self.data = data or {}

    def callback(func):
        return func

    def split_entity_id(entity_id: str):
        domain, object_id = entity_id.split(".", 1)
        return domain, object_id

    core.HomeAssistant = HomeAssistant
    core.Event = Event
    core.ServiceCall = ServiceCall
    core.callback = callback
    core.split_entity_id = split_entity_id
    sys.modules["homeassistant.core"] = core

    # const / exceptions / helpers
    const = types.ModuleType("homeassistant.const")

    class Platform:
        SENSOR = "sensor"

    const.Platform = Platform
    const.CONF_NAME = "name"
    const.CONF_PORT = "port"
    sys.modules["homeassistant.const"] = const

    exceptions = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions.HomeAssistantError = HomeAssistantError
    sys.modules["homeassistant.exceptions"] = exceptions

    helpers = types.ModuleType("homeassistant.helpers")
    sys.modules["homeassistant.helpers"] = helpers

    area_registry = types.ModuleType("homeassistant.helpers.area_registry")
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    config_validation = types.ModuleType("homeassistant.helpers.config_validation")
    selector = types.ModuleType("homeassistant.helpers.selector")
    event_helpers = types.ModuleType("homeassistant.helpers.event")
    entity_mod = types.ModuleType("homeassistant.helpers.entity")
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    typing_mod = types.ModuleType("homeassistant.helpers.typing")

    class RegistryEntry:  # placeholder type for annotations
        pass

    entity_registry.RegistryEntry = RegistryEntry
    entity_registry.async_get = MagicMock()
    device_registry.async_get = MagicMock()
    area_registry.async_get = MagicMock()

    def multi_select(options):
        return options

    config_validation.multi_select = multi_select
    config_validation.string = str

    class TextSelectorConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class TextSelectorType:
        TEXT = "text"

    class TextSelector:
        def __init__(self, config):
            self.config = config

    selector.TextSelector = TextSelector
    selector.TextSelectorConfig = TextSelectorConfig
    selector.TextSelectorType = TextSelectorType

    event_helpers.async_call_later = MagicMock()
    event_helpers.async_track_time_interval = MagicMock()

    class DeviceInfo(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    entity_mod.DeviceInfo = DeviceInfo

    entity_platform.AddEntitiesCallback = object
    typing_mod.ConfigType = dict

    sys.modules["homeassistant.helpers.area_registry"] = area_registry
    sys.modules["homeassistant.helpers.device_registry"] = device_registry
    sys.modules["homeassistant.helpers.entity_registry"] = entity_registry
    sys.modules["homeassistant.helpers.config_validation"] = config_validation
    sys.modules["homeassistant.helpers.selector"] = selector
    sys.modules["homeassistant.helpers.event"] = event_helpers
    sys.modules["homeassistant.helpers.entity"] = entity_mod
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform
    sys.modules["homeassistant.helpers.typing"] = typing_mod

    components = types.ModuleType("homeassistant.components")
    sensor_comp = types.ModuleType("homeassistant.components.sensor")

    class SensorEntity:
        async def async_added_to_hass(self):
            return None

        def async_on_remove(self, _cb):
            return None

        def async_write_ha_state(self):
            return None

    sensor_comp.SensorEntity = SensorEntity
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.sensor"] = sensor_comp

    # voluptuous stub used by config_flow / services
    if "voluptuous" not in sys.modules:
        vol = types.ModuleType("voluptuous")

        class Schema:
            def __init__(self, schema):
                self.schema = schema

            def __call__(self, data):
                return data

        class _Marker:
            def __init__(self, key, default=None):
                self.key = key
                self.default = default

            def __hash__(self):
                return hash(self.key)

            def __eq__(self, other):
                return self.key == getattr(other, "key", other)

        def Required(key, default=None):
            return _Marker(key, default)

        def Optional(key, default=None):
            return _Marker(key, default)

        vol.Schema = Schema
        vol.Required = Required
        vol.Optional = Optional
        sys.modules["voluptuous"] = vol


_install_ha_stubs()


@dataclass
class FakeEntity:
    entity_id: str
    area_id: str | None = None
    device_id: str | None = None
    disabled: bool = False
    hidden_by: Any = None
    entity_category: Any = None


@dataclass
class FakeDevice:
    id: str
    area_id: str | None = None


@dataclass
class FakeArea:
    id: str
    name: str


class FakeEntityRegistry:
    def __init__(self, entities: list[FakeEntity]):
        self.entities = {e.entity_id: e for e in entities}

    def async_get(self, entity_id: str):
        return self.entities.get(entity_id)


class FakeDeviceRegistry:
    def __init__(self, devices: list[FakeDevice]):
        self._devices = {d.id: d for d in devices}

    def async_get(self, device_id: str):
        return self._devices.get(device_id)


class FakeAreaRegistry:
    def __init__(self, areas: list[FakeArea]):
        self._areas = {a.id: a for a in areas}

    def async_get_area(self, area_id: str):
        return self._areas.get(area_id)

    def async_list_areas(self):
        return list(self._areas.values())


class FakeConfigEntries:
    def __init__(self):
        self._entries: dict[str, Any] = {}
        self.flow = SimpleNamespace(async_init=AsyncMock())
        self.async_reload = AsyncMock()

    def async_entries(self, domain: str):
        return [e for e in self._entries.values() if e.domain == domain]

    def async_get_entry(self, entry_id: str):
        return self._entries.get(entry_id)

    def async_update_entry(self, entry, *, data=None, options=None, unique_id=None, title=None):
        if data is not None:
            entry.data = data
        if options is not None:
            entry.options = options
        if unique_id is not None:
            entry.unique_id = unique_id
        if title is not None:
            entry.title = title
        self._entries[entry.entry_id] = entry

    def add(self, entry):
        self._entries[entry.entry_id] = entry


def make_hass() -> Any:
    hass = MagicMock()
    hass.config_entries = FakeConfigEntries()
    hass.services = SimpleNamespace(async_call=AsyncMock(), async_register=MagicMock(), async_remove=MagicMock())
    hass.data = {}
    hass.bus = SimpleNamespace(async_listen=MagicMock(return_value=lambda: None))
    return hass
