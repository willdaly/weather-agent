# Weather Agent Curl Examples

This document shows example `curl` calls another agent or service can make against the deployed app at `https://weather-agent-weather-app.up.railway.app/`.

## Check Service Health

Use this first if the calling agent wants to confirm the service is reachable.

```bash
curl "https://weather-agent-weather-app.up.railway.app/health"
```

Expected response shape:

```json
{
  "ok": true,
  "ready": true,
  "service": "mbta-boston-weather-agent",
  "version": "1.0.0",
  "weather_provider_configured": true,
  "location_default": "Boston, MA"
}
```

## Ask a Question via A2A

This is the main endpoint another agent should use for natural-language weather and MBTA impact questions.

```bash
curl -X POST "https://weather-agent-weather-app.up.railway.app/a2a/message" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "payload": {
      "message": "Will snow affect the Red Line tomorrow morning in Boston?",
      "conversation_id": "agent-demo-1"
    },
    "metadata": {
      "source": "other-agent"
    }
  }'
```

Example response shape:

```json
{
  "type": "response",
  "payload": {
    "ok": true,
    "text": "Snow tomorrow morning creates elevated risk for Red Line service in Boston...",
    "summary": "High Boston commute weather risk for Red Line tomorrow morning",
    "structured_data": {
      "risk_level": "high",
      "confidence": 0.81,
      "city": "Boston",
      "time_window": "tomorrow morning",
      "affected_modes": ["subway", "bus"],
      "affected_routes": ["Red"],
      "hazards": ["snow"],
      "operational_impact": "High probability of delays...",
      "rider_impact": "Longer wait times and crowded platforms are likely.",
      "recommendations": [
        "Leave earlier than usual",
        "Check MBTA alerts before departure"
      ]
    }
  },
  "metadata": {
    "status": "success",
    "agent": "mbta-boston-weather-agent",
    "timestamp": "2026-04-02T12:00:00+00:00"
  }
}
```

## Ask a Question Without a Conversation ID

`conversation_id` is optional.

```bash
curl -X POST "https://weather-agent-weather-app.up.railway.app/a2a/message" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "payload": {
      "message": "Will freezing rain affect buses in Boston tonight?"
    },
    "metadata": {
      "source": "scheduler-agent"
    }
  }'
```

## See Validation Failure Example

If a caller omits the required `payload.message`, the app returns a 422 error.

```bash
curl -X POST "https://weather-agent-weather-app.up.railway.app/a2a/message" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "payload": {},
    "metadata": {
      "source": "broken-client"
    }
  }'
```

Expected response shape:

```json
{
  "type": "error",
  "payload": {
    "error": "invalid_request",
    "text": "The request payload did not match the expected A2A schema."
  },
  "metadata": {
    "status": "error",
    "agent": "mbta-boston-weather-agent",
    "timestamp": "2026-04-02T12:00:00+00:00"
  }
}
```

## Discover MCP Tools

If the calling system uses an MCP-style flow, it can first ask the app what tools it exposes.

```bash
curl -X POST "https://weather-agent-weather-app.up.railway.app/mcp/tools/list" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected response shape:

```json
{
  "tools": [
    {
      "name": "analyze_boston_weather_impact",
      "description": "Analyze Boston weather impact on MBTA transit operations",
      "inputSchema": {
        "type": "object",
        "properties": {
          "message": {
            "type": "string",
            "description": "Natural-language question about weather and MBTA service"
          }
        },
        "required": ["message"]
      }
    }
  ]
}
```

## Call the MCP Tool

This is the MCP-style equivalent of calling `/a2a/message`.

```bash
curl -X POST "https://weather-agent-weather-app.up.railway.app/mcp/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "analyze_boston_weather_impact",
    "arguments": {
      "message": "Will heavy rain affect commuter rail service in Boston this evening?"
    }
  }'
```

Expected response shape:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Heavy rain this evening creates moderate risk for Boston commuter rail service..."
    }
  ]
}
```

## See the OpenAPI Schema

Another agent can inspect the schema directly.

```bash
curl "https://weather-agent-weather-app.up.railway.app/openapi.json"
```

## Fetch the Swagger UI HTML

This is mostly useful for a human operator, but it is still a valid endpoint.

```bash
curl "https://weather-agent-weather-app.up.railway.app/docs"
```

## Notes

- The current root path `/` returns FastAPI's default 404 because no root endpoint is defined yet.
- For plain HTTP integrations, prefer `/a2a/message`.
- For MCP-style integrations, use `/mcp/tools/list` and `/mcp/tools/call`.