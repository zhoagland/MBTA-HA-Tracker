"""MBTA Next Train integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE,
    CONF_API_KEY,
    CONF_DIRECTION,
    CONF_ROUTE,
    CONF_STOP,
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


class MbtaCoordinator(DataUpdateCoordinator):
    """Fetches upcoming departures from the MBTA v3 API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.session = async_get_clientsession(hass)

    async def _get(self, path: str, params: dict) -> dict:
        headers = {"accept": "application/vnd.api+json"}
        if key := self.entry.data.get(CONF_API_KEY):
            headers["x-api-key"] = key
        async with self.session.get(
            f"{API_BASE}{path}", params=params, headers=headers, timeout=15
        ) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"MBTA API returned {resp.status}")
            return await resp.json(content_type=None)

    async def _async_update_data(self) -> list[dict]:
        data = self.entry.data
        params = {
            "filter[stop]": data[CONF_STOP],
            "filter[route]": data[CONF_ROUTE],
            "filter[direction_id]": str(data[CONF_DIRECTION]),
            "sort": "departure_time",
            "include": "trip",
            "page[limit]": "10",
        }
        try:
            departures = _parse(await self._get("/predictions", params), "prediction")
            if not departures:
                # No live predictions (e.g. late night) -> fall back to the schedule.
                params["filter[min_time]"] = dt_util.now().strftime("%H:%M")
                departures = _parse(await self._get("/schedules", params), "schedule")
        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error talking to MBTA API: {err}") from err
        return departures


def _parse(body: dict, source: str) -> list[dict]:
    """Turn a JSON:API predictions/schedules response into a sorted departure list."""
    trips = {
        t["id"]: t["attributes"]
        for t in body.get("included", [])
        if t.get("type") == "trip"
    }
    now = dt_util.utcnow()
    out = []
    for item in body.get("data", []):
        attrs = item["attributes"]
        if attrs.get("schedule_relationship") in ("CANCELLED", "SKIPPED"):
            continue
        dep = attrs.get("departure_time")
        if not dep:  # arrival-only (train ends here)
            continue
        dep_dt = dt_util.parse_datetime(dep)
        if dep_dt is None or dep_dt < now:
            continue
        trip_ref = item.get("relationships", {}).get("trip", {}).get("data") or {}
        trip = trips.get(trip_ref.get("id"), {})
        out.append(
            {
                "departure": dep_dt,
                "minutes": int((dep_dt - now).total_seconds() // 60),
                "status": attrs.get("status"),
                "headsign": trip.get("headsign"),
                "source": source,
            }
        )
    out.sort(key=lambda d: d["departure"])
    return out


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = MbtaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
