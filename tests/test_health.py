def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["ready"] is True
    assert data["service"] == "mbta-boston-weather-agent"
    assert "weather_provider_configured" in data
    assert data["location_default"] == "Boston, MA"
