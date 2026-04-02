"""
Optional weather provider client.

Supports OpenWeatherMap (current + forecast) by default.
If WEATHER_API_KEY is not configured, all calls return None
and the caller falls back to simulated analysis.

Normalized hazard output avoids leaking provider-specific schema
into business logic.
"""

from __future__ import annotations
import logging
from typing import Any

import httpx

from app.config import (
    WEATHER_API_KEY,
    WEATHER_API_BASE_URL,
    WEATHER_DEFAULT_LOCATION,
    WEATHER_PROVIDER_NAME,
)

logger = logging.getLogger(__name__)

TIMEOUT = 8.0  # seconds


def _candidate_locations(location: str) -> list[str]:
    candidates: list[str] = []

    def add(candidate: str) -> None:
        normalized = candidate.strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    add(location)

    if "," in location:
        city, _, region = location.partition(",")
        city = city.strip()
        region = region.strip()
        add(city)
        if len(region) == 2 and region.isalpha():
            add(f"{city},US")

    return candidates

# OWM condition ID ranges mapped to normalized hazard labels.
# Ranges are non-overlapping and checked in order; first match wins.
# OWM reference: https://openweathermap.org/weather-conditions
_OWM_RANGES: list[tuple[range, str]] = [
    (range(200, 300), "high wind"),     # thunderstorm group — treat as severe wind/rain
    (range(300, 400), "rain"),          # drizzle
    (range(500, 502), "rain"),          # light/moderate rain
    (range(502, 505), "heavy rain"),    # heavy/extreme rain
    (range(511, 512), "freezing rain"), # freezing rain (511 only)
    (range(512, 532), "rain"),          # shower rain variants
    (range(600, 611), "snow"),          # light/moderate/heavy snow
    (range(611, 613), "sleet"),         # sleet
    (range(613, 616), "freezing rain"), # shower sleet / rain and sleet
    (range(616, 623), "snow"),          # rain and snow, shower snow, heavy shower snow
    (range(700, 722), "fog"),           # mist, smoke, haze, sand/dust whirls, fog, sand
    (range(722, 762), "visibility"),    # volcanic ash, squalls, tornado
    (range(900, 902), "high wind"),     # tornado, tropical storm
    (range(952, 960), "wind"),          # breeze to very windy
    (range(960, 963), "high wind"),     # storm / violent storm
]


def _owm_condition_to_hazard(condition_id: int, description: str) -> str | None:
    desc = description.lower()
    for crange, label in _OWM_RANGES:
        if condition_id in crange:
            return label
    if "flood" in desc:
        return "flooding"
    if "coast" in desc:
        return "coastal flooding"
    if "ice" in desc or "icy" in desc:
        return "ice"
    if "extreme cold" in desc or "frigid" in desc:
        return "extreme cold"
    if "extreme heat" in desc or "heat" in desc:
        return "extreme heat"
    return None


def _normalize_owm(data: dict[str, Any]) -> dict[str, Any]:
    """Convert OWM /weather response to normalized hazard dict."""
    hazards: list[str] = []
    weather_list = data.get("weather", [])
    for w in weather_list:
        h = _owm_condition_to_hazard(w.get("id", 0), w.get("description", ""))
        if h and h not in hazards:
            hazards.append(h)

    wind_speed = data.get("wind", {}).get("speed", 0)
    if wind_speed >= 20:
        if "high wind" not in hazards:
            hazards.append("high wind")
    elif wind_speed >= 10 and "wind" not in hazards:
        hazards.append("wind")

    temp_k = data.get("main", {}).get("temp", 273)
    temp_f = (temp_k - 273.15) * 9 / 5 + 32
    if temp_f <= 10:
        if "extreme cold" not in hazards:
            hazards.append("extreme cold")
    elif temp_f >= 95:
        if "extreme heat" not in hazards:
            hazards.append("extreme heat")

    desc_parts = [w.get("description", "") for w in weather_list]
    return {
        "hazards": hazards,
        "description": "; ".join(desc_parts),
        "time_window": "now",
        "source": "openweathermap",
    }


async def fetch_forecast(location: str | None = None) -> dict[str, Any] | None:
    """
    Fetch current weather for location and return normalized hazard dict.
    Returns None if API key is not configured or on any error.
    """
    if not WEATHER_API_KEY:
        logger.debug("No WEATHER_API_KEY configured; skipping live forecast")
        return None

    loc = location or WEATHER_DEFAULT_LOCATION
    url = f"{WEATHER_API_BASE_URL}/weather"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for candidate in _candidate_locations(loc):
                params = {"q": candidate, "appid": WEATHER_API_KEY}
                try:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    return _normalize_owm(data)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        logger.info("Weather API location not found for query=%s; trying fallback if available", candidate)
                        continue
                    logger.warning("Weather API HTTP error %s for location=%s", exc.response.status_code, candidate)
                    return None
    except httpx.TimeoutException:
        logger.warning("Weather API timeout for location=%s", loc)
    except (httpx.RequestError, ValueError, KeyError) as exc:
        logger.warning("Weather API error: %s", exc)

    logger.warning("Weather API could not resolve a forecast for location=%s", loc)
    return None
