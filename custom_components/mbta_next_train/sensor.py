"""Sensors for MBTA Next Train."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [NextTrainTimeSensor(coordinator, entry), NextTrainMinutesSensor(coordinator, entry)]
    )


class _Base(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:subway-variant"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def _next(self) -> dict | None:
        return self.coordinator.data[0] if self.coordinator.data else None


class NextTrainTimeSensor(_Base):
    """Departure time of the next train (HA shows it as 'in X minutes')."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = f"{entry.title} next departure"
        self._attr_unique_id = f"{entry.entry_id}_departure"

    @property
    def native_value(self):
        return self._next["departure"] if self._next else None

    @property
    def extra_state_attributes(self):
        nxt = self._next or {}
        return {
            "headsign": nxt.get("headsign"),
            "status": nxt.get("status"),
            "source": nxt.get("source"),
            "upcoming": [
                {
                    "time": d["departure"].isoformat(),
                    "minutes": d["minutes"],
                    "status": d["status"],
                }
                for d in (self.coordinator.data or [])[:5]
            ],
        }


class NextTrainMinutesSensor(_Base):
    """Minutes until the next train departs."""

    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = f"{entry.title} minutes away"
        self._attr_unique_id = f"{entry.entry_id}_minutes"

    @property
    def native_value(self):
        return self._next["minutes"] if self._next else None
