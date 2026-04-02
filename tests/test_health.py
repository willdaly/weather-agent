def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["ready"] is True
    assert data["service"] == "mbta-boston-weather-agent"
    assert "weather_provider_configured" in data
    assert data["location_default"] == "Boston, MA"


def test_health_reports_string_location_default(client):
    data = client.get("/health").json()
    assert isinstance(data["location_default"], str)
