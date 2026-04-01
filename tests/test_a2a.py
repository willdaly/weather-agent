import pytest

VALID_REQUEST = {
    "type": "request",
    "payload": {
        "message": "Will freezing rain affect the Red Line tomorrow morning in Boston?",
        "conversation_id": "test-conv-1",
    },
    "metadata": {"source": "stategraph"},
}

INVALID_REQUEST = {
    "type": "request",
    "payload": {},  # missing required 'message' field
}


def test_valid_a2a_request(client):
    resp = client.post("/a2a/message", json=VALID_REQUEST)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "response"
    assert data["payload"]["ok"] is True
    assert len(data["payload"]["text"]) > 0
    assert data["payload"]["structured_data"]["risk_level"] in ("low", "moderate", "high", "severe")
    assert data["metadata"]["agent"] == "mbta-boston-weather-agent"
    assert data["metadata"]["status"] == "success"


def test_invalid_a2a_request(client):
    resp = client.post("/a2a/message", json=INVALID_REQUEST)
    assert resp.status_code == 422
    data = resp.json()
    assert data["type"] == "error"
    assert "error" in data["payload"]


def test_a2a_boston_fields(client):
    resp = client.post("/a2a/message", json=VALID_REQUEST)
    assert resp.status_code == 200
    sd = resp.json()["payload"]["structured_data"]
    assert sd["city"] == "Boston"
    assert "subway" in sd["affected_modes"] or "bus" in sd["affected_modes"]
    assert len(sd["recommendations"]) > 0


def test_a2a_no_conversation_id(client):
    req = {
        "type": "request",
        "payload": {"message": "Will snow affect the Orange Line tonight?"},
    }
    resp = client.post("/a2a/message", json=req)
    assert resp.status_code == 200
    assert resp.json()["type"] == "response"
