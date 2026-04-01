from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class A2APayload(BaseModel):
    message: str
    conversation_id: str | None = None

    model_config = {"extra": "ignore"}


class A2AMetadata(BaseModel):
    source: str | None = None

    model_config = {"extra": "ignore"}


class A2ARequest(BaseModel):
    type: str = "request"
    payload: A2APayload
    metadata: A2AMetadata | None = None

    model_config = {"extra": "ignore"}


class StructuredData(BaseModel):
    risk_level: str
    confidence: float
    city: str
    time_window: str
    affected_modes: list[str]
    affected_routes: list[str]
    hazards: list[str]
    operational_impact: str
    rider_impact: str
    recommendations: list[str]


class ResponsePayload(BaseModel):
    ok: bool
    text: str
    summary: str
    structured_data: StructuredData


class ErrorPayload(BaseModel):
    error: str
    text: str


class ResponseMetadata(BaseModel):
    status: str
    agent: str
    timestamp: str


class A2AResponse(BaseModel):
    type: str
    payload: ResponsePayload | ErrorPayload
    metadata: ResponseMetadata
