"""Config flow for HomeKit Room Sync."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar, config_validation as cv, selector

from .const import (
    CONF_AREA_BRIDGES,
    CONF_AREAS,
    CONF_DOMAINS,
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    DEFAULT_DOMAINS,
    DOMAIN,
)
from .helpers import default_domains, entity_list_to_text, parse_entity_list

STEP_USER = "user"


def _area_options(hass) -> dict[str, str]:
    registry = ar.async_get(hass)
    return {
        area.id: area.name
        for area in sorted(
            registry.async_list_areas(),
            key=lambda item: (item.name or "").lower(),
        )
        if area.id
    }


def _domain_options() -> dict[str, str]:
    return {domain: domain.replace("_", " ").title() for domain in DEFAULT_DOMAINS}


class HaHkRoomSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeKit Room Sync."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial setup: choose areas and domains."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        areas = _area_options(self.hass)
        if not areas:
            return self.async_abort(reason="no_areas")

        errors: dict[str, str] = {}
        if user_input is not None:
            selected_areas = list(user_input.get(CONF_AREAS) or [])
            selected_domains = list(user_input.get(CONF_DOMAINS) or [])
            if not selected_areas:
                errors["base"] = "areas_required"
            elif not selected_domains:
                errors["base"] = "domains_required"
            else:
                data = {
                    CONF_AREAS: selected_areas,
                    CONF_DOMAINS: selected_domains,
                    CONF_INCLUDE_ENTITIES: parse_entity_list(
                        user_input.get(CONF_INCLUDE_ENTITIES)
                    ),
                    CONF_EXCLUDE_ENTITIES: parse_entity_list(
                        user_input.get(CONF_EXCLUDE_ENTITIES)
                    ),
                }
                return self.async_create_entry(
                    title="HomeKit Room Sync",
                    data=data,
                )

        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AREAS, default=list(areas)): cv.multi_select(
                        areas
                    ),
                    vol.Required(
                        CONF_DOMAINS, default=default_domains()
                    ): cv.multi_select(_domain_options()),
                    vol.Optional(CONF_INCLUDE_ENTITIES, default=""): selector.TextSelector(
                        selector.TextSelectorConfig(
                            multiline=True,
                            type=selector.TextSelectorType.TEXT,
                        )
                    ),
                    vol.Optional(CONF_EXCLUDE_ENTITIES, default=""): selector.TextSelector(
                        selector.TextSelectorConfig(
                            multiline=True,
                            type=selector.TextSelectorType.TEXT,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return HaHkRoomSyncOptionsFlow()


class HaHkRoomSyncOptionsFlow(OptionsFlow):
    """Handle options for HomeKit Room Sync."""

    def _entry(self) -> ConfigEntry:
        """Return the config entry being configured."""
        # Prefer the framework-provided property (HA 2024.12+).
        try:
            entry = self.config_entry  # type: ignore[attr-defined]
            if entry is not None:
                return entry
        except Exception:  # noqa: BLE001 - property may raise before init
            pass
        entry = self.hass.config_entries.async_get_entry(self.handler)  # type: ignore[arg-type]
        if entry is None:
            raise RuntimeError("Options flow is missing its config entry")
        return entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage areas/domains/overrides."""
        areas = _area_options(self.hass)
        errors: dict[str, str] = {}
        config_entry = self._entry()

        if user_input is not None:
            selected_areas = list(user_input.get(CONF_AREAS) or [])
            selected_domains = list(user_input.get(CONF_DOMAINS) or [])
            if not selected_areas:
                errors["base"] = "areas_required"
            elif not selected_domains:
                errors["base"] = "domains_required"
            else:
                data = {
                    CONF_AREAS: selected_areas,
                    CONF_DOMAINS: selected_domains,
                    CONF_INCLUDE_ENTITIES: parse_entity_list(
                        user_input.get(CONF_INCLUDE_ENTITIES)
                    ),
                    CONF_EXCLUDE_ENTITIES: parse_entity_list(
                        user_input.get(CONF_EXCLUDE_ENTITIES)
                    ),
                    # Preserve bridge mapping; manager will reconcile.
                    CONF_AREA_BRIDGES: config_entry.data.get(CONF_AREA_BRIDGES, {}),
                }
                self.hass.config_entries.async_update_entry(config_entry, data=data)
                return self.async_create_entry(title="", data={})

        current = config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AREAS,
                        default=list(current.get(CONF_AREAS, list(areas))),
                    ): cv.multi_select(areas),
                    vol.Required(
                        CONF_DOMAINS,
                        default=list(current.get(CONF_DOMAINS, default_domains())),
                    ): cv.multi_select(_domain_options()),
                    vol.Optional(
                        CONF_INCLUDE_ENTITIES,
                        default=entity_list_to_text(
                            current.get(CONF_INCLUDE_ENTITIES, [])
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            multiline=True,
                            type=selector.TextSelectorType.TEXT,
                        )
                    ),
                    vol.Optional(
                        CONF_EXCLUDE_ENTITIES,
                        default=entity_list_to_text(
                            current.get(CONF_EXCLUDE_ENTITIES, [])
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            multiline=True,
                            type=selector.TextSelectorType.TEXT,
                        )
                    ),
                }
            ),
            errors=errors,
        )
