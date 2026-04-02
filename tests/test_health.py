def test_health_ok(client, monkeypatch):
    async def fake_fetch_forecast():
        return {"hazards": ["rain"], "source": "openweathermap"}

    monkeypatch.setattr("app.main.fetch_forecast", fake_fetch_forecast)

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["ready"] is True
    assert data["service"] == "mbta-boston-weather-agent"
    assert data["weather_provider_configured"] is True
    assert data["weather_provider_reachable"] is True
    assert data["weather_mode"] == "live"
    assert data["location_default"] == "Boston, MA"


def test_health_reports_string_location_default(client, monkeypatch):
    async def fake_fetch_forecast():
        return None

    monkeypatch.setattr("app.main.fetch_forecast", fake_fetch_forecast)

    data = client.get("/health").json()
    assert isinstance(data["location_default"], str)
    assert data["weather_provider_reachable"] is False
    assert data["weather_mode"] == "simulated"
