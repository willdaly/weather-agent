import asyncio
import pytest
import httpx
from app.main import app as fastapi_app


class SyncTestClient:
    """
    Minimal sync test client using httpx.AsyncClient + ASGITransport.
    Replaces starlette.testclient.TestClient, which is broken with
    httpx >= 0.20 when the httpx `app=` shortcut was removed.
    """

    def __init__(self, app):
        self._app = app
        self._base = "http://testserver"

    def get(self, path, **kwargs):
        return asyncio.run(self._request("GET", path, **kwargs))

    def post(self, path, **kwargs):
        return asyncio.run(self._request("POST", path, **kwargs))

    async def _request(self, method, path, **kwargs):
        transport = httpx.ASGITransport(app=self._app)
        async with httpx.AsyncClient(transport=transport, base_url=self._base) as c:
            return await c.request(method, path, **kwargs)


@pytest.fixture
def client():
    return SyncTestClient(fastapi_app)
