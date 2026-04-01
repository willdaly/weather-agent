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

_OWM_RANGES: list[tuple[range, str]] = [
    (range(200, 300), "wind"),
    (range(300, 400), "rain"),
    (range(500, 502), "rain"),
    (range(502, 505), "heavy rain"),
    (range(511, 512), "freezing rain"),
    (range(520, 532), "rain"),
    (range(600, 602), "snow"),
    (range(602, 620), "snow"),
    (range(611, 613), "sleet"),
    (range(613, 616), "freezing rain"),
    (range(616, 622), "snow"),
    (range(620, 623), "snow"),
    (range(700, 722), "fog"),
    (range(722, 762), "visibility"),
    (range(900, 902), "extreme wind"),
    (range(952, 960), "wind"),
    (range(960, 963), "high wind"),
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
    params = {"q": loc, "appid": WEATHER_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return _normalize_owm(data)
    except httpx.TimeoutException:
        logger.warning("Weather API timeout for location=%s", loc)
    except httpx.HTTPStatusError as exc:
        logger.warning("Weather API HTTP error %s for location=%s", exc.response.status_code, loc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Weather API unexpected error: %s", exc)
    return None
