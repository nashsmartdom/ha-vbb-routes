from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
    DEFAULT_MAX_TRANSFERS,
    DEFAULT_MIN_DEPART_OFFSET_MIN,
    DEFAULT_RESULTS,
    DEFAULT_TOP_N,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    VBB_JOURNEYS_URL,
)

_LOGGER = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Berlin")

LINE_COLOURS: dict[str, tuple[str, str]] = {
    "U1": ("#7DAD4B", "#FFFFFF"),
    "U2": ("#DA421E", "#FFFFFF"),
    "U3": ("#16683D", "#FFFFFF"),
    "U4": ("#F0D722", "#000000"),
    "U5": ("#7E5330", "#FFFFFF"),
    "U6": ("#8C6DAB", "#FFFFFF"),
    "U7": ("#009BD8", "#FFFFFF"),
    "U8": ("#224F86", "#FFFFFF"),
    "U9": ("#F3791D", "#FFFFFF"),
    "S1": ("#DB6394", "#FFFFFF"),
    "S2": ("#007734", "#FFFFFF"),
    "S3": ("#00983A", "#FFFFFF"),
    "S5": ("#EB7405", "#FFFFFF"),
    "S7": ("#6F4E9B", "#FFFFFF"),
    "S8": ("#55A822", "#FFFFFF"),
    "S9": ("#8A1002", "#FFFFFF"),
}

DEFAULT_COLOURS: dict[str, tuple[str, str]] = {
    "subway": ("#333333", "#FFFFFF"),
    "suburban": ("#007A3D", "#FFFFFF"),
    "tram": ("#BE1414", "#FFFFFF"),
    "bus": ("#6A6A6A", "#FFFFFF"),
    "walking": ("#444444", "#FFFFFF"),
}


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TZ)


def fmt_time(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%H:%M")


def is_walking_leg(leg: dict[str, Any]) -> bool:
    return bool(leg.get("walking")) or not leg.get("line")


def get_line_colour(line_name: str | None, product: str | None) -> tuple[str, str]:
    if line_name and line_name in LINE_COLOURS:
        return LINE_COLOURS[line_name]
    return DEFAULT_COLOURS.get(product or "", ("#555555", "#FFFFFF"))


def normalize_leg(leg: dict[str, Any]) -> dict[str, Any]:
    walking = is_walking_leg(leg)
    line = leg.get("line") or {}
    line_name = line.get("name")
    product = line.get("product") or line.get("mode")

    if walking:
        line_name = "Fußweg"
        product = "walking"

    bg, fg = get_line_colour(line_name, product)
    dep = parse_dt(leg.get("departure") or leg.get("plannedDeparture"))
    arr = parse_dt(leg.get("arrival") or leg.get("plannedArrival"))

    raw_delay = leg.get("departureDelay") if leg.get("departureDelay") is not None else leg.get("arrivalDelay")
    if raw_delay is None:
        raw_delay = leg.get("delay", 0)

    try:
        delay_min = int(raw_delay / 60)
    except (TypeError, ValueError):
        delay_min = 0

    return {
        "line": line_name,
        "product": product,
        "walking": walking,
        "origin": (leg.get("origin") or {}).get("name"),
        "destination": (leg.get("destination") or {}).get("name"),
        "departure": fmt_time(dep),
        "arrival": fmt_time(arr),
        "delay_min": delay_min,
        "bg": bg,
        "fg": fg,
    }


def normalize_journey(journey: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    raw_legs = journey.get("legs") or []
    if not raw_legs:
        return None

    legs = [normalize_leg(leg) for leg in raw_legs]
    non_walking_legs = [leg for leg in legs if not leg["walking"]]
    transfers = max(0, len(non_walking_legs) - 1)

    first_raw = raw_legs[0]
    last_raw = raw_legs[-1]

    leave_dt = parse_dt(first_raw.get("departure") or first_raw.get("plannedDeparture"))
    arrival_dt = parse_dt(last_raw.get("arrival") or last_raw.get("plannedArrival"))

    first_transport_raw = None
    for leg in raw_legs:
        if not is_walking_leg(leg):
            first_transport_raw = leg
            break

    if first_transport_raw:
        departure_dt = parse_dt(first_transport_raw.get("departure") or first_transport_raw.get("plannedDeparture"))
    else:
        departure_dt = leave_dt

    if leave_dt is None or arrival_dt is None:
        return None

    duration_min = int((arrival_dt - leave_dt).total_seconds() / 60)
    minutes_until_leave = int((leave_dt - now).total_seconds() / 60)

    change_at = None
    if len(non_walking_legs) >= 2:
        change_at = non_walking_legs[0]["destination"]

    max_delay_min = 0
    for leg in legs:
        try:
            max_delay_min = max(max_delay_min, int(leg.get("delay_min") or 0))
        except (TypeError, ValueError):
            pass

    return {
        "leave_home": fmt_time(leave_dt),
        "departure": fmt_time(departure_dt),
        "arrival": fmt_time(arrival_dt),
        "duration_min": duration_min,
        "transfers": transfers,
        "minutes_until_leave": minutes_until_leave,
        "change_at": change_at,
        "max_delay_min": max_delay_min,
        "legs": legs,
    }


class VBBRoutesCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self._last_good: dict[str, Any] | None = None

        update_interval = int(entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self._fetch_routes()
            self._last_good = data
            return data
        except Exception as err:
            _LOGGER.warning("VBB update failed: %s", err)
            if self._last_good is not None:
                cached = dict(self._last_good)
                cached["api_ok"] = False
                cached["served_from_cache"] = True
                cached["error"] = str(err)
                cached["cache_returned_at"] = datetime.now(TZ).isoformat()
                return cached
            raise UpdateFailed(f"VBB update failed: {err}") from err

    async def _fetch_routes(self) -> dict[str, Any]:
        entry_data = self.entry.data
        now = datetime.now(TZ)

        min_depart_offset = int(entry_data.get(CONF_MIN_DEPART_OFFSET_MIN, DEFAULT_MIN_DEPART_OFFSET_MIN))
        max_transfers = int(entry_data.get(CONF_MAX_TRANSFERS, DEFAULT_MAX_TRANSFERS))
        results = int(entry_data.get(CONF_RESULTS, DEFAULT_RESULTS))
        top_n = int(entry_data.get(CONF_TOP_N, DEFAULT_TOP_N))
        min_depart = now + timedelta(minutes=min_depart_offset)

        params = {
            "from.latitude": float(entry_data[CONF_ORIGIN_LAT]),
            "from.longitude": float(entry_data[CONF_ORIGIN_LON]),
            "from.address": entry_data[CONF_ORIGIN_ADDRESS],
            "to": entry_data[CONF_DESTINATION_ID],
            "departure": min_depart.isoformat(),
            "transfers": max_transfers,
            "results": results,
            "stopovers": "false",
            "remarks": "false",
            "language": "de",
        }

        try:
            async with self.session.get(VBB_JOURNEYS_URL, params=params, timeout=15) as response:
                if response.status != 200:
                    text = await response.text()
                    raise UpdateFailed(f"VBB HTTP {response.status}: {text[:300]}")
                payload = await response.json()
        except ClientError as err:
            raise UpdateFailed(f"VBB connection error: {err}") from err

        routes: list[dict[str, Any] | None] = []
        for journey in payload.get("journeys", []):
            route = normalize_journey(journey, now)
            if route is None:
                continue
            if route["minutes_until_leave"] < min_depart_offset:
                continue
            if route["transfers"] > max_transfers:
                continue
            routes.append(route)

        routes.sort(key=lambda item: item["minutes_until_leave"] if item else 999999)
        routes = routes[:top_n]

        while len(routes) < top_n:
            routes.append(None)

        return {
            "api_ok": True,
            "served_from_cache": False,
            "updated_at": now.isoformat(),
            "origin": entry_data[CONF_ORIGIN_NAME],
            "destination": entry_data[CONF_DESTINATION_NAME],
            "min_depart_offset_min": min_depart_offset,
            "max_transfers": max_transfers,
            "routes": routes,
        }
