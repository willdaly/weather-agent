import pytest
from app.agent_logic import analyze, _match_patterns, TIME_WINDOWS, MODE_PATTERNS


def test_time_window_tomorrow_morning():
    result = analyze("Will snow affect the Red Line tomorrow morning?")
    assert result["time_window"] == "tomorrow morning"


def test_time_window_evening_commute():
    result = analyze("How bad is the evening commute during freezing rain?")
    assert result["time_window"] == "evening commute"


def test_mode_extraction_ferry():
    result = analyze("Will high winds affect the ferry this evening?")
    assert "ferry" in result["affected_modes"]


def test_mode_extraction_commuter_rail():
    result = analyze("How risky is commuter rail in a snowstorm tomorrow morning?")
    assert "commuter rail" in result["affected_modes"]


def test_mode_extraction_bus():
    result = analyze("Will heavy rain cause bus delays in Boston this evening?")
    assert "bus" in result["affected_modes"]


def test_route_extraction_red_line():
    result = analyze("Will freezing rain affect the Red Line?")
    assert "Red" in result["affected_routes"]
    assert "subway" in result["affected_modes"]


def test_route_extraction_green_line():
    result = analyze("Green Line during snow tomorrow?")
    assert "Green" in result["affected_routes"]


def test_hazard_extraction_snow():
    result = analyze("Heavy snow this morning on the subway")
    assert "snow" in result["hazards"]


def test_hazard_extraction_freezing_rain():
    result = analyze("Freezing rain tomorrow morning")
    assert "freezing rain" in result["hazards"]


def test_city_defaults_to_boston():
    result = analyze("Will rain affect transit today?")
    assert result["city"] == "Boston"


def test_boston_geo_detected():
    result = analyze("Weather in downtown Boston today")
    assert result["city"] in ("Boston", "downtown")


def test_recommendations_non_empty():
    result = analyze("Snow during the morning commute")
    assert len(result["recommendations"]) > 0


def test_is_simulated_without_forecast():
    result = analyze("Will it rain today?", forecast=None)
    assert result["is_simulated"] is True


def test_is_not_simulated_with_forecast():
    forecast = {"hazards": ["rain"], "time_window": "today"}
    result = analyze("Will it rain today?", forecast=forecast)
    assert result["is_simulated"] is False
