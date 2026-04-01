# MBTA Boston Weather Agent

A standalone Python FastAPI service that analyzes Boston weather impacts on MBTA transit and provides rider-facing guidance and service risk assessments.

Designed to interoperate with the MBTA Winter 2026 application via the local NANDA registry and the app's HTTP A2A interface.

---

## Setup

### Requirements

- Python 3.11+
- pip

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| `AGENT_ID` | `mbta-boston-weather-agent` | Stable agent identifier |
| `AGENT_HOST` | `0.0.0.0` | Bind address |
| `AGENT_PORT` | `8004` | Bind port |
| `AGENT_PUBLIC_URL` | `http://localhost:8004` | Base URL published to registry (no path) |
| `REGISTRY_URL` | `http://localhost:8000` | NANDA registry base URL |
| `WEATHER_API_KEY` | _(empty)_ | OpenWeatherMap API key — leave blank for fallback mode |
| `WEATHER_API_BASE_URL` | `https://api.openweathermap.org/data/2.5` | Weather API base |
| `WEATHER_DEFAULT_LOCATION` | `Boston, MA` | Default location for weather queries |

---

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8004
```

Or directly:

```bash
python -m app.main
```

---

## Register the agent

```bash
python scripts/register_agent.py
```

This calls `POST {REGISTRY_URL}/register` with the agent's ID, URL, capabilities, and description.

---

## Mark the agent alive

```bash
python scripts/set_agent_alive.py
```

This calls `PUT {REGISTRY_URL}/agents/{AGENT_ID}/status` with `alive: true`, capabilities, tags, and description.

---

## Example: call /a2a/message

```bash
curl -X POST http://localhost:8004/a2a/message \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "payload": {
      "message": "Will freezing rain affect the Red Line tomorrow morning in Boston?",
      "conversation_id": "demo-1"
    },
    "metadata": {"source": "curl"}
  }'
```

Expected response shape:

```json
{
  "type": "response",
  "payload": {
    "ok": true,
    "text": "Freezing rain during tomorrow morning creates an elevated risk for Red Line and connecting subway and bus in Boston...",
    "summary": "High Boston commute weather risk for Red Line tomorrow morning",
    "structured_data": {
      "risk_level": "high",
      "confidence": 0.81,
      "city": "Boston",
      "time_window": "tomorrow morning",
      "affected_modes": ["subway", "bus"],
      "affected_routes": ["Red"],
      "hazards": ["freezing rain"],
      "operational_impact": "High probability of delays...",
      "rider_impact": "...",
      "recommendations": ["leave 15-20 minutes earlier than usual", "..."]
    }
  },
  "metadata": {
    "status": "success",
    "agent": "mbta-boston-weather-agent",
    "timestamp": "2026-01-15T08:00:00+00:00"
  }
}
```

---

## Boston-specific MBTA weather heuristics

The agent uses explicit deterministic heuristics rather than an LLM, ensuring consistent, auditable results.

### Hazard base scores

| Hazard | Base score |
|---|---|
| Light rain | 1 |
| Rain | 2 |
| Heavy rain | 4 |
| Flooding | 6 |
| Coastal flooding | 7 |
| Snow | 5 |
| Sleet | 6 |
| Freezing rain | 7 |
| Ice | 6 |
| Wind | 3 |
| High wind | 5 |
| Gusts | 4 |
| Fog / visibility | 3 |
| Extreme cold | 3 |
| Extreme heat | 2 |

### Mode sensitivity extras (added to base score)

| Mode | Sensitive to | Extra |
|---|---|---|
| Bus | snow, ice, freezing rain, sleet, flooding, heavy rain | +1 to +2 |
| Ferry | wind, high wind, gusts, visibility, fog | +2 to +3 |
| Commuter rail | snow, wind, high wind, ice, freezing rain | +2 |
| Subway | freezing rain, ice, flooding | +1 |

### Risk bands

| Total score | Risk level |
|---|---|
| 0–3 | low |
| 4–6 | moderate |
| 7–9 | high |
| 10+ | severe |

### Peak-period weighting

If the queried time window overlaps a Boston peak commute period (morning commute, this morning, evening commute, tonight) **and** the base score ≥ 4, the score is increased by +2, potentially pushing the result to the next band.

Peak commute windows: **6:30–9:30 AM** and **4:00–7:00 PM** Boston time.

---

## Fallback behavior

If `WEATHER_API_KEY` is not configured, the agent operates in **simulated mode**:

- All hazard detection is derived from the incoming message text rather than a live forecast.
- Responses include a `[Simulated forecast — no live weather data configured]` prefix in `payload.text`.
- The response contract (shape, fields, risk_level, recommendations) is identical to live mode.

This ensures the agent is always usable, even without a weather API key.

---

## Run tests

```bash
pytest tests/ -v
```

---

## Project structure

```
app/
  __init__.py
  config.py         # environment variable loading
  models.py         # Pydantic request/response models
  agent_logic.py    # Boston MBTA weather analysis pipeline
  weather_client.py # optional weather API client (OpenWeatherMap)
  scoring.py        # deterministic risk heuristics and scoring model
  main.py           # FastAPI app (/health, /a2a/message, /mcp/*)
scripts/
  register_agent.py # POST /register to NANDA registry
  set_agent_alive.py # PUT /agents/{id}/status to NANDA registry
tests/
  test_health.py
  test_a2a.py
  test_agent_logic.py
  test_scoring.py
  test_registration.py
  test_smoke.py
.env.example
requirements.txt
README.md
```
