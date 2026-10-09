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
from homeassistant.helpers import area_registry as ar, selector

from .const import (
    AVAILABLE_DOMAINS,
    CONF_AREA_BRIDGES,
    CONF_AREAS,
    CONF_DOMAINS,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_LABELS,
    CONF_INCLUDE_ENTITIES,
    DOMAIN,
)
from .helpers import default_domains, parse_id_list

STEP_USER = "user"


def _has_areas(hass) -> bool:
    registry = ar.async_get(hass)
    return any(area.id for area in registry.async_list_areas())


def _domain_select_options() -> list[dict[str, str]]:
    return [
        {
            "value": domain,
            "label": domain.replace("_", " ").title(),
        }
        for domain in AVAILABLE_DOMAINS
    ]


def _config_schema(
    *,
    areas_default: list[str] | None = None,
    domains_default: list[str] | None = None,
    include_default: list[str] | None = None,
    exclude_entities_default: list[str] | None = None,
    exclude_labels_default: list[str] | None = None,
) -> vol.Schema:
    """Build the shared setup/options schema with selection-based UI."""
    return vol.Schema(
        {
            vol.Required(
                CONF_AREAS,
                default=areas_default or [],
            ): selector.AreaSelector(
                selector.AreaSelectorConfig(multiple=True),
            ),
            vol.Required(
                CONF_DOMAINS,
                default=domains_default if domains_default is not None else default_domains(),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_domain_select_options(),
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                    sort=True,
                )
            ),
            vol.Optional(
                CONF_INCLUDE_ENTITIES,
                default=include_default or [],
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=True),
            ),
            vol.Optional(
                CONF_EXCLUDE_ENTITIES,
                default=exclude_entities_default or [],
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=True),
            ),
            vol.Optional(
                CONF_EXCLUDE_LABELS,
                default=exclude_labels_default or [],
            ): selector.LabelSelector(
                selector.LabelSelectorConfig(multiple=True),
            ),
        }
    )


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize selector values into stored config lists."""
    return {
        CONF_AREAS: parse_id_list(user_input.get(CONF_AREAS)),
        CONF_DOMAINS: parse_id_list(user_input.get(CONF_DOMAINS)),
        CONF_INCLUDE_ENTITIES: parse_id_list(user_input.get(CONF_INCLUDE_ENTITIES)),
        CONF_EXCLUDE_ENTITIES: parse_id_list(user_input.get(CONF_EXCLUDE_ENTITIES)),
        CONF_EXCLUDE_LABELS: parse_id_list(user_input.get(CONF_EXCLUDE_LABELS)),
    }


class HaHkRoomSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeKit Room Sync."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial setup: choose areas and domains."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if not _has_areas(self.hass):
            return self.async_abort(reason="no_areas")

        errors: dict[str, str] = {}
        if user_input is not None:
            data = _normalize_user_input(user_input)
            if not data[CONF_AREAS]:
                errors["base"] = "areas_required"
            elif not data[CONF_DOMAINS]:
                errors["base"] = "domains_required"
            else:
                return self.async_create_entry(
                    title="HomeKit Room Sync",
                    data=data,
                )

        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=_config_schema(),
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
        errors: dict[str, str] = {}
        config_entry = self._entry()

        if user_input is not None:
            data = _normalize_user_input(user_input)
            if not data[CONF_AREAS]:
                errors["base"] = "areas_required"
            elif not data[CONF_DOMAINS]:
                errors["base"] = "domains_required"
            else:
                data[CONF_AREA_BRIDGES] = config_entry.data.get(
                    CONF_AREA_BRIDGES, {}
                )
                self.hass.config_entries.async_update_entry(config_entry, data=data)
                return self.async_create_entry(title="", data={})

        current = config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=_config_schema(
                areas_default=list(current.get(CONF_AREAS, [])),
                domains_default=list(
                    current.get(CONF_DOMAINS, default_domains())
                ),
                include_default=list(current.get(CONF_INCLUDE_ENTITIES, [])),
                exclude_entities_default=list(
                    current.get(CONF_EXCLUDE_ENTITIES, [])
                ),
                exclude_labels_default=list(
                    current.get(CONF_EXCLUDE_LABELS, [])
                ),
            ),
            errors=errors,
        )
