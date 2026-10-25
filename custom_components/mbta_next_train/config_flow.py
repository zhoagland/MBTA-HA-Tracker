"""Config flow for MBTA Next Train."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_BASE,
    CONF_API_KEY,
    CONF_DIRECTION,
    CONF_ROUTE,
    CONF_STOP,
    DEFAULT_DIRECTION,
    DEFAULT_ROUTE,
    DEFAULT_STOP,
    DOMAIN,
)


class MbtaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input[CONF_DIRECTION] = int(user_input[CONF_DIRECTION])
            await self.async_set_unique_id(
                f"{user_input[CONF_STOP]}_{user_input[CONF_ROUTE]}_{user_input[CONF_DIRECTION]}"
            )
            self._abort_if_unique_id_configured()

            title = await self._title(user_input)
            if title is None:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_STOP, default=DEFAULT_STOP): str,
                vol.Required(CONF_ROUTE, default=DEFAULT_ROUTE): str,
                vol.Required(CONF_DIRECTION, default=str(DEFAULT_DIRECTION)): vol.In(
                    {"0": "0 - Orange: toward Forest Hills", "1": "1 - Orange: toward Oak Grove"}
                ),
                vol.Optional(CONF_API_KEY, default=""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _title(self, data) -> str | None:
        """Validate stop/route and build a name like 'Malden Center to Forest Hills'."""
        session = async_get_clientsession(self.hass)
        headers = {"x-api-key": data[CONF_API_KEY]} if data.get(CONF_API_KEY) else {}
        try:
            async with session.get(
                f"{API_BASE}/stops/{data[CONF_STOP]}", headers=headers, timeout=15
            ) as r:
                if r.status != 200:
                    return None
                stop = (await r.json(content_type=None))["data"]["attributes"]["name"]
            async with session.get(
                f"{API_BASE}/routes/{data[CONF_ROUTE]}", headers=headers, timeout=15
            ) as r:
                if r.status != 200:
                    return None
                attrs = (await r.json(content_type=None))["data"]["attributes"]
                dest = attrs["direction_destinations"][data[CONF_DIRECTION]]
        except Exception:  # noqa: BLE001
            return None
        return f"{stop} to {dest}"
