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

DESCRIPTION = (
    "Analyzes Boston weather impacts on MBTA subway, bus, commuter rail, and ferry service; "
    "predicts likely disruption risk; explains rider-facing commute impacts; and recommends "
    "weather-aware travel decisions."
)

payload = {
    "agent_id": AGENT_ID,
    "name": "MBTA Boston Weather Agent",
    "endpoint": AGENT_PUBLIC_URL,
    "description": DESCRIPTION,
    "agent_type": "analysis",
    "capabilities": ["A2A", "MCP"],
}

url = f"{REGISTRY_URL.rstrip('/')}/agents"
print(f"Registering {AGENT_ID} at {url} ...")
try:
    resp = httpx.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"Registered successfully: {resp.json()}")
except httpx.HTTPStatusError as exc:
    print(f"HTTP error {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)
