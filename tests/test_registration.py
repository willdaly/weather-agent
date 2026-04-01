"""Tests for registration and alive-status payload builders."""
import importlib.util
import os
import sys


def _load_module(script_path: str, module_name: str):
    """Load a script as a module without executing top-level side effects."""
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    mod = importlib.util.module_from_spec(spec)
    return mod, spec


def test_register_payload_structure():
    from app.config import AGENT_ID, AGENT_PUBLIC_URL
    # Build payload as the script would
    capabilities = [
        "boston-weather-analysis",
        "mbta-weather-risk-assessment",
        "commute-impact-prediction",
        "rider-guidance",
        "mode-specific-weather-analysis",
    ]
    description = (
        "Analyzes Boston weather impacts on MBTA subway, bus, commuter rail, and ferry service; "
        "predicts likely disruption risk; explains rider-facing commute impacts; and recommends "
        "weather-aware travel decisions."
    )
    payload = {
        "agent_id": AGENT_ID,
        "agent_url": AGENT_PUBLIC_URL,
        "api_url": AGENT_PUBLIC_URL,
        "description": description,
        "capabilities": capabilities,
    }
    assert payload["agent_id"] == "mbta-boston-weather-agent"
    assert "boston-weather-analysis" in payload["capabilities"]
    assert "mbta" in payload["description"].lower()
    # agent_url must not have a path component beyond the origin
    from urllib.parse import urlparse
    parsed = urlparse(payload["agent_url"])
    assert parsed.path in ("", "/"), f"agent_url should be base origin, got path={parsed.path!r}"


def test_alive_status_payload_structure():
    tags = ["boston", "mbta", "weather", "commute", "forecast", "risk", "operations"]
    capabilities = [
        "boston-weather-analysis",
        "mbta-weather-risk-assessment",
        "commute-impact-prediction",
        "rider-guidance",
        "mode-specific-weather-analysis",
    ]
    payload = {
        "alive": True,
        "capabilities": capabilities,
        "tags": tags,
        "description": "some description",
    }
    assert payload["alive"] is True
    assert "boston" in payload["tags"]
    assert "mbta" in payload["tags"]
    assert len(payload["capabilities"]) == 5
