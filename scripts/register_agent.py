#!/usr/bin/env python3
"""
Register the MBTA Boston Weather Agent with the NANDA registry.

Usage:
    python scripts/register_agent.py
"""

import sys
import os

# Allow running from project root without install
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

def build_payload(alive: bool = True) -> dict:
    return {
        "agent_id": AGENT_ID,
        "name": "MBTA Boston Weather Agent",
        "endpoint": AGENT_PUBLIC_URL,
        "description": DESCRIPTION,
        "agent_type": "analysis",
        "capabilities": CAPABILITIES,
        "tags": TAGS,
        "alive": alive,
    }

agents_url = f"{REGISTRY_URL.rstrip('/')}/agents"
agent_url = f"{agents_url}/{AGENT_ID}"
payload = build_payload(alive=True)
print(f"Publishing registry entry for {AGENT_ID} at {agent_url} ...")
try:
    resp = httpx.put(agent_url, json=payload, timeout=10)
    if resp.status_code == 404:
        resp = httpx.post(agents_url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"Registry entry published: {resp.json()}")
except httpx.HTTPStatusError as exc:
    print(f"HTTP error {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)
