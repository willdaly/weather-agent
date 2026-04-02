import asyncio

import httpx

from app import weather_client


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.request = httpx.Request("GET", "https://example.test/weather")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request, json=self._payload),
            )

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses, calls):
        self._responses = responses
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params):
        self._calls.append(params["q"])
        status_code, payload = self._responses[params["q"]]
        return _FakeResponse(status_code, payload)


def test_candidate_locations_include_openweather_fallbacks():
    assert weather_client._candidate_locations("Boston, MA") == ["Boston, MA", "Boston", "Boston,US"]


def test_fetch_forecast_retries_on_location_404(monkeypatch):
    calls = []
    responses = {
        "Boston, MA": (404, {"message": "city not found"}),
        "Boston": (200, {"weather": [{"id": 500, "description": "light rain"}], "wind": {"speed": 3}, "main": {"temp": 285}}),
    }

    monkeypatch.setattr(weather_client, "WEATHER_API_KEY", "test-key")
    monkeypatch.setattr(
        weather_client.httpx,
        "AsyncClient",
        lambda timeout: _FakeAsyncClient(responses=responses, calls=calls),
    )

    result = asyncio.run(weather_client.fetch_forecast("Boston, MA"))

    assert calls == ["Boston, MA", "Boston"]
    assert result is not None
    assert result["hazards"] == ["rain"]