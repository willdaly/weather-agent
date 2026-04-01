import logging
from datetime import datetime, timezone

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import (
    AGENT_ID,
    AGENT_HOST,
    AGENT_PORT,
    LOG_LEVEL,
    VERSION,
    WEATHER_API_KEY,
    WEATHER_DEFAULT_LOCATION,
)
from app.models import A2ARequest, A2AResponse, ResponsePayload, ErrorPayload, ResponseMetadata, StructuredData
from app.agent_logic import analyze
from app.weather_client import fetch_forecast

logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="MBTA Boston Weather Agent", version=VERSION)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta(status: str) -> ResponseMetadata:
    return ResponseMetadata(status=status, agent=AGENT_ID, timestamp=_now_iso())


@app.get("/health")
async def health():
    weather_configured = bool(WEATHER_API_KEY)
    return {
        "ok": True,
        "ready": True,
        "service": AGENT_ID,
        "version": VERSION,
        "weather_provider_configured": weather_configured,
        "location_default": WEATHER_DEFAULT_LOCATION,
    }


@app.post("/a2a/message")
async def a2a_message(request: Request):
    body = await request.json()
    logger.info("Received A2A request: conversation_id=%s", body.get("payload", {}).get("conversation_id"))

    try:
        req = A2ARequest.model_validate(body)
    except ValidationError as exc:
        logger.warning("Invalid A2A request: %s", exc)
        return JSONResponse(
            status_code=422,
            content={
                "type": "error",
                "payload": {
                    "error": "invalid_request",
                    "text": "The request payload did not match the expected A2A schema.",
                },
                "metadata": _meta("error").model_dump(),
            },
        )

    message = req.payload.message
    logger.info("Processing message: %s", message[:120])

    # Attempt live weather fetch; fall back to None (simulated) on failure
    try:
        forecast = await fetch_forecast()
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError) as exc:
        logger.warning("Weather fetch failed: %s", exc)
        forecast = None

    result = analyze(message, forecast)

    logger.info(
        "Analysis complete: risk_level=%s confidence=%s modes=%s hazards=%s",
        result["risk_level"], result["confidence"], result["affected_modes"], result["hazards"],
    )

    structured = StructuredData(
        risk_level=result["risk_level"],
        confidence=result["confidence"],
        city=result["city"],
        time_window=result["time_window"],
        affected_modes=result["affected_modes"],
        affected_routes=result["affected_routes"],
        hazards=result["hazards"],
        operational_impact=result["operational_impact"],
        rider_impact=result["rider_impact"],
        recommendations=result["recommendations"],
    )

    response_payload = ResponsePayload(
        ok=True,
        text=result["text"],
        summary=result["summary"],
        structured_data=structured,
    )

    return {
        "type": "response",
        "payload": response_payload.model_dump(),
        "metadata": _meta("success").model_dump(),
    }


# Optional MCP endpoints
@app.post("/mcp/tools/list")
async def mcp_tools_list():
    return {
        "tools": [
            {
                "name": "analyze_boston_weather_impact",
                "description": "Analyze Boston weather impact on MBTA transit operations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Natural-language question about weather and MBTA service"}
                    },
                    "required": ["message"],
                },
            }
        ]
    }


@app.post("/mcp/tools/call")
async def mcp_tools_call(request: Request):
    body = await request.json()
    tool_name = body.get("name")
    args = body.get("arguments", {})
    if tool_name != "analyze_boston_weather_impact":
        return JSONResponse(status_code=404, content={"error": f"Unknown tool: {tool_name}"})
    message = args.get("message", "")
    forecast = await fetch_forecast()
    result = analyze(message, forecast)
    return {"content": [{"type": "text", "text": result["text"]}]}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=AGENT_HOST, port=AGENT_PORT, reload=False)
