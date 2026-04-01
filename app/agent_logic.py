"""
Boston MBTA weather analysis pipeline.

Parses incoming natural-language messages for time windows, routes/modes,
geographic hints, and weather hazard terms, then produces a structured
MBTA-specific risk assessment.
"""

from __future__ import annotations
import re
import logging
from datetime import datetime, timezone

from app.scoring import compute_risk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vocabulary lookups
# ---------------------------------------------------------------------------

TIME_WINDOWS: list[tuple[str, str]] = [
    (r"tomorrow morning", "tomorrow morning"),
    (r"tomorrow evening", "tomorrow evening"),
    (r"tomorrow", "tomorrow"),
    (r"this morning", "this morning"),
    (r"this evening", "this evening"),
    (r"tonight", "tonight"),
    (r"morning commute", "morning commute"),
    (r"evening commute", "evening commute"),
    (r"this weekend", "this weekend"),
    (r"today", "today"),
    (r"now", "now"),
]

ROUTE_PATTERNS: list[tuple[str, str]] = [
    (r"red line", "Red"),
    (r"orange line", "Orange"),
    (r"blue line", "Blue"),
    (r"green line", "Green"),
    (r"mattapan", "Mattapan"),
]

MODE_PATTERNS: list[tuple[str, str]] = [
    (r"commuter rail", "commuter rail"),
    (r"ferry|boat", "ferry"),
    (r"bus(?:es)?", "bus"),
    (r"subway|rapid transit|t line|mbta", "subway"),
]

HAZARD_PATTERNS: list[tuple[str, str]] = [
    (r"coastal flooding", "coastal flooding"),
    (r"flood(?:ing)?", "flooding"),
    (r"freezing rain", "freezing rain"),
    (r"heavy rain", "heavy rain"),
    (r"sleet", "sleet"),
    (r"snow(?:storm|fall)?", "snow"),
    (r"ice|icy|black ice", "ice"),
    (r"high wind|strong wind", "high wind"),
    (r"wind(?:y|s|gusts?)?", "wind"),
    (r"gust(?:s|y)?", "gusts"),
    (r"rain(?:y)?", "rain"),
    (r"fog(?:gy)?|mist(?:y)?", "fog"),
    (r"visib(?:ility)?", "visibility"),
    (r"extreme cold|frigid|below zero", "extreme cold"),
    (r"extreme heat|heat wave|very hot", "extreme heat"),
]

GEO_PATTERNS: list[tuple[str, str]] = [
    (r"seaport|south boston waterfront", "Seaport"),
    (r"downtown|financial district", "downtown"),
    (r"cambridge", "Cambridge"),
    (r"somerville", "Somerville"),
    (r"back bay", "Back Bay"),
    (r"north station", "North Station"),
    (r"south station", "South Station"),
    (r"waterfront|harbor", "waterfront"),
    (r"boston", "Boston"),
]

PEAK_WINDOWS = {"tomorrow morning", "this morning", "morning commute", "tonight", "this evening", "evening commute"}

# Modes implied by route names
ROUTE_TO_MODE: dict[str, str] = {
    "Red": "subway",
    "Orange": "subway",
    "Blue": "subway",
    "Green": "subway",
    "Mattapan": "subway",
}

# ---------------------------------------------------------------------------
# Operational impact templates
# ---------------------------------------------------------------------------

def _operational_impact(risk_level: str, hazards: list[str], modes: list[str]) -> str:
    if risk_level == "severe":
        return "Severe conditions likely causing significant service disruptions across multiple MBTA modes"
    if risk_level == "high":
        return "High probability of delays, reduced speed, and longer station throughput times"
    if risk_level == "moderate":
        return "Moderate chance of delays and slower service on affected modes"
    return "Minimal operational impact expected; monitor MBTA alerts for updates"


def _rider_impact(risk_level: str, hazards: list[str], modes: list[str]) -> str:
    parts = []
    if "freezing rain" in hazards or "ice" in hazards:
        parts.append("icy platforms and sidewalks increase slip risk")
    if "snow" in hazards:
        parts.append("snow-covered stops and slower boarding expected")
    if "flooding" in hazards or "coastal flooding" in hazards:
        parts.append("some station approaches may be affected by water")
    if "high wind" in hazards or "wind" in hazards:
        parts.append("wind chill and exposed areas will be uncomfortable")
    if "heavy rain" in hazards or "rain" in hazards:
        parts.append("expect crowding as riders avoid walking in rain")
    if not parts:
        parts.append("minor rider inconvenience expected")
    base = "Riders should expect " + "; ".join(parts)
    if risk_level in ("high", "severe"):
        base += "; allow extra travel time door-to-door"
    return base


def _recommendations(risk_level: str, hazards: list[str], modes: list[str], is_peak: bool) -> list[str]:
    recs = []
    if risk_level in ("high", "severe"):
        recs.append("leave 15-20 minutes earlier than usual")
    elif risk_level == "moderate":
        recs.append("consider leaving 10 minutes earlier")
    recs.append("check MBTA alerts and real-time departures before leaving")
    if "ice" in hazards or "freezing rain" in hazards:
        recs.append("use caution on platforms, stairs, and sidewalks")
    if "snow" in hazards:
        recs.append("allow extra time for boarding and transfers")
    if "ferry" in modes and ("wind" in hazards or "high wind" in hazards):
        recs.append("check ferry service status — cancellations possible in high wind")
    if "bus" in modes and ("snow" in hazards or "flooding" in hazards):
        recs.append("bus delays likely; consider subway if available")
    if is_peak:
        recs.append("peak-period crowding will compound weather delays")
    return recs


def _build_text(
    message: str,
    time_window: str,
    risk_level: str,
    hazards: list[str],
    modes: list[str],
    routes: list[str],
    recommendations: list[str],
    is_simulated: bool,
) -> str:
    """Produce plain-English analyst-style response text."""
    hazard_str = ", ".join(hazards) if hazards else "adverse weather"
    mode_str = " and ".join(modes) if modes else "transit"
    route_str = (", ".join(routes) + " Line") if routes else ""
    window_str = time_window if time_window != "unknown" else "the queried period"

    prefix = "[Simulated forecast — no live weather data configured] " if is_simulated else ""
    severity_phrase = {
        "low": "low",
        "moderate": "moderate",
        "high": "elevated",
        "severe": "severe",
    }.get(risk_level, risk_level)

    if routes:
        lead = f"{prefix}{hazard_str.capitalize()} during {window_str} creates a {severity_phrase} risk for {route_str} and connecting {mode_str} in Boston."
    else:
        lead = f"{prefix}{hazard_str.capitalize()} during {window_str} creates a {severity_phrase} MBTA service risk in Boston."

    rec_str = "; ".join(recommendations[:3]) if recommendations else "monitor MBTA alerts"
    return f"{lead} Riders should {rec_str}."


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def _match_patterns(text: str, patterns: list[tuple[str, str]]) -> list[str]:
    results = []
    for pattern, label in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            results.append(label)
    return results


def _infer_modes_from_routes(routes: list[str], explicit_modes: list[str]) -> list[str]:
    modes = list(explicit_modes)
    for r in routes:
        implied = ROUTE_TO_MODE.get(r)
        if implied and implied not in modes:
            modes.append(implied)
    return modes


def analyze(message: str, forecast: dict | None = None) -> dict:
    """
    Main analysis entry point.

    Args:
        message: natural-language question from the caller
        forecast: optional normalized forecast dict from weather_client

    Returns:
        Internal result dict ready for response building.
    """
    lower = message.lower()

    # Parse context from message
    time_windows = _match_patterns(lower, TIME_WINDOWS)
    time_window = time_windows[0] if time_windows else "unspecified time"

    routes = _match_patterns(lower, ROUTE_PATTERNS)
    explicit_modes = _match_patterns(lower, MODE_PATTERNS)
    modes = _infer_modes_from_routes(routes, explicit_modes)

    # Default to all rapid-transit modes if none extracted
    if not modes:
        modes = ["subway", "bus"]

    geo_hints = _match_patterns(lower, GEO_PATTERNS)
    city = geo_hints[0] if geo_hints else "Boston"

    # Use forecast hazards if available, else parse from message
    is_simulated = forecast is None
    if forecast and forecast.get("hazards"):
        hazards = forecast["hazards"]
        if forecast.get("time_window") and time_window == "unspecified time":
            time_window = forecast["time_window"]
    else:
        hazards = _match_patterns(lower, HAZARD_PATTERNS)
        # Fallback: if no hazards detected, assume generic adverse weather
        if not hazards:
            hazards = ["adverse weather"]

    is_peak = time_window in PEAK_WINDOWS

    logger.info(
        "analyze: time_window=%s routes=%s modes=%s hazards=%s is_peak=%s",
        time_window, routes, modes, hazards, is_peak,
    )

    risk_level, confidence = compute_risk(hazards, modes, is_peak)

    op_impact = _operational_impact(risk_level, hazards, modes)
    rider_impact = _rider_impact(risk_level, hazards, modes)
    recs = _recommendations(risk_level, hazards, modes, is_peak)

    text = _build_text(message, time_window, risk_level, hazards, modes, routes, recs, is_simulated)
    forecast_summary = f"{', '.join(hazards).capitalize()} during the {time_window} Boston commute"

    summary = f"{risk_level.capitalize()} Boston commute weather risk"
    if routes:
        summary += f" for {', '.join(routes)} Line"
    if time_window != "unspecified time":
        summary += f" {time_window}"

    return {
        "text": text,
        "summary": summary,
        "forecast_summary": forecast_summary,
        "city": city,
        "time_window": time_window,
        "risk_level": risk_level,
        "confidence": confidence,
        "affected_modes": modes,
        "affected_routes": routes,
        "hazards": hazards,
        "operational_impact": op_impact,
        "rider_impact": rider_impact,
        "recommendations": recs,
        "is_simulated": is_simulated,
    }
