"""End-to-end smoke test: start service, check health, post to /a2a/message."""
import time
import threading
import pytest
import httpx
import uvicorn

from app.main import app
from app.config import AGENT_PORT


class _Server(uvicorn.Server):
    """Uvicorn server that can be started in a background thread."""

    def install_signal_handlers(self):
        pass  # Disable so it works in a thread


def _run_server(server: _Server):
    server.run()


@pytest.fixture(scope="module")
def live_server():
    """Start a real uvicorn server for smoke tests."""
    config = uvicorn.Config(app, host="127.0.0.1", port=AGENT_PORT, log_level="warning")
    server = _Server(config=config)
    thread = threading.Thread(target=_run_server, args=(server,), daemon=True)
    thread.start()
    # Wait for server to start
    base = f"http://127.0.0.1:{AGENT_PORT}"
    for _ in range(20):
        try:
            resp = httpx.get(f"{base}/health", timeout=1)
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    yield base
    server.should_exit = True
    thread.join(timeout=5)


def test_smoke_health(live_server):
    resp = httpx.get(f"{live_server}/health", timeout=5)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["ready"] is True


def test_smoke_a2a_message(live_server):
    payload = {
        "type": "request",
        "payload": {
            "message": "Will snow affect the Red Line tomorrow morning in Boston?",
            "conversation_id": "smoke-test-1",
        },
        "metadata": {"source": "test"},
    }
    resp = httpx.post(f"{live_server}/a2a/message", json=payload, timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "response"
    assert len(data["payload"]["text"]) > 0
    sd = data["payload"]["structured_data"]
    assert sd["risk_level"] in ("low", "moderate", "high", "severe")
    assert sd["city"] == "Boston"
    assert len(sd["affected_modes"]) > 0
    assert len(sd["recommendations"]) > 0
    assert "mbta-boston-weather-agent" in data["metadata"]["agent"]
