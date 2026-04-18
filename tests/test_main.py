from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_stream_endpoint_exists():
    # SSE endpoint - just check it responds
    with client.stream("GET", "/stream") as response:
        assert response.status_code == 200