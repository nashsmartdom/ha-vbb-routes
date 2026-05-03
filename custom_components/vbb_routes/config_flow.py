from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DESTINATION_ID,
    CONF_DESTINATION_NAME,
    CONF_MAX_TRANSFERS,
    CONF_MIN_DEPART_OFFSET_MIN,
    CONF_ORIGIN_ADDRESS,
    CONF_ORIGIN_LAT,
    CONF_ORIGIN_LON,
    CONF_ORIGIN_NAME,
    CONF_RESULTS,
    CONF_TOP_N,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DESTINATION_ID,
    DEFAULT_DESTINATION_NAME,
    DEFAULT_MAX_TRANSFERS,
    DEFAULT_MIN_DEPART_OFFSET_MIN,
    DEFAULT_NAME,
    DEFAULT_ORIGIN_ADDRESS,
    DEFAULT_ORIGIN_LAT,
    DEFAULT_ORIGIN_LON,
    DEFAULT_ORIGIN_NAME,
    DEFAULT_RESULTS,
    DEFAULT_TOP_N,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


class VBBRoutesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = (
                f"{user_input[CONF_ORIGIN_LAT]}_"
                f"{user_input[CONF_ORIGIN_LON]}_"
                f"{user_input[CONF_DESTINATION_ID]}"
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_ORIGIN_NAME, default=DEFAULT_ORIGIN_NAME): str,
                vol.Required(CONF_ORIGIN_ADDRESS, default=DEFAULT_ORIGIN_ADDRESS): str,
                vol.Required(CONF_ORIGIN_LAT, default=DEFAULT_ORIGIN_LAT): vol.Coerce(float),
                vol.Required(CONF_ORIGIN_LON, default=DEFAULT_ORIGIN_LON): vol.Coerce(float),
                vol.Required(CONF_DESTINATION_ID, default=DEFAULT_DESTINATION_ID): str,
                vol.Required(CONF_DESTINATION_NAME, default=DEFAULT_DESTINATION_NAME): str,
                vol.Required(CONF_MIN_DEPART_OFFSET_MIN, default=DEFAULT_MIN_DEPART_OFFSET_MIN): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
                vol.Required(CONF_MAX_TRANSFERS, default=DEFAULT_MAX_TRANSFERS): vol.All(vol.Coerce(int), vol.Range(min=0, max=5)),
                vol.Required(CONF_RESULTS, default=DEFAULT_RESULTS): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
                vol.Required(CONF_TOP_N, default=DEFAULT_TOP_N): vol.All(vol.Coerce(int), vol.Range(min=1, max=6)),
                vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
