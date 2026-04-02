#!/usr/bin/env python3
"""
Mark the MBTA Boston Weather Agent as alive in the NANDA registry.

Usage:
    python scripts/set_agent_alive.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from dotenv import load_dotenv
load_dotenv()

from app.config import AGENT_ID, AGENT_PUBLIC_URL, REGISTRY_URL

CAPABILITIES = [
    "boston-weather-analysis",
    "mbta-weather-risk-assessment",
    "commute-impact-prediction",
    "rider-guidance",
    "mode-specific-weather-analysis",
]

TAGS = [
    "boston",
    "mbta",
    "weather",
    "commute",
    "forecast",
    "risk",
    "operations",
]

DESCRIPTION = (
    "Analyzes Boston weather impacts on MBTA subway, bus, commuter rail, and ferry service; "
    "predicts likely disruption risk; explains rider-facing commute impacts; and recommends "
    "weather-aware travel decisions."
)

payload = {
    "agent_id": AGENT_ID,
    "name": "MBTA Boston Weather Agent",
    "endpoint": AGENT_PUBLIC_URL,
    "agent_type": "analysis",
    "alive": True,
    "capabilities": CAPABILITIES,
    "tags": TAGS,
    "description": DESCRIPTION,
}

url = f"{REGISTRY_URL.rstrip('/')}/agents/{AGENT_ID}"
print(f"Publishing agent metadata for {AGENT_ID} at {url} ...")
try:
    resp = httpx.put(url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"Agent metadata updated: {resp.json()}")
except httpx.HTTPStatusError as exc:
    print(f"HTTP error {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)
