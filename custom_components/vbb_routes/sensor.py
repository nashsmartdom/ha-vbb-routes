from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_TOP_N, DEFAULT_TOP_N, DOMAIN
from .coordinator import VBBRoutesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    coordinator: VBBRoutesCoordinator = hass.data[DOMAIN][entry.entry_id]
    top_n = int(entry.data.get(CONF_TOP_N, DEFAULT_TOP_N))
    async_add_entities([VBBRouteSensor(coordinator, entry, index) for index in range(top_n)])


class VBBRouteSensor(CoordinatorEntity[VBBRoutesCoordinator], SensorEntity):
    _attr_icon = "mdi:train"

    def __init__(
        self,
        coordinator: VBBRoutesCoordinator,
        entry: ConfigEntry,
        index: int,
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.index = index
        route_number = index + 1
        self._attr_name = f"{entry.title} Route {route_number}"
        self._attr_unique_id = f"{entry.entry_id}_route_{route_number}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="VBB",
            model="Journey polling integration",
        )

    @property
    def route(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        routes = data.get("routes") or []
        if self.index >= len(routes):
            return None
        return routes[self.index]

    @property
    def native_value(self) -> str | None:
        route = self.route
        if route is None:
            return "—"
        return route.get("leave_home") or "—"

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        route = self.route

        attrs: dict[str, Any] = {
            "route_available": route is not None,
            "api_ok": data.get("api_ok"),
            "served_from_cache": data.get("served_from_cache"),
            "updated_at": data.get("updated_at"),
            "origin": data.get("origin"),
            "destination": data.get("destination"),
            "min_depart_offset_min": data.get("min_depart_offset_min"),
            "max_transfers": data.get("max_transfers"),
        }

        if data.get("error"):
            attrs["error"] = data.get("error")

        if data.get("cache_returned_at"):
            attrs["cache_returned_at"] = data.get("cache_returned_at")

        if route is None:
            return attrs

        attrs.update(
            {
                "leave_home": route.get("leave_home"),
                "departure": route.get("departure"),
                "arrival": route.get("arrival"),
                "duration_min": route.get("duration_min"),
                "minutes_until_leave": route.get("minutes_until_leave"),
                "transfers": route.get("transfers"),
                "change_at": route.get("change_at"),
                "max_delay_min": route.get("max_delay_min"),
                "legs": route.get("legs"),
            }
        )
        return attrs
