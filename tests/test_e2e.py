import subprocess
import time
import requests
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

def test_session_start():
    response = client.post("/session/start")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "path" in data

def test_stream_sends_data():
    with client.stream("GET", "/stream") as response:
        assert response.status_code == 200
        # Read first event line
        chunks = []
        start = time.time()
        for line in response.iter_lines():
            if line:
                chunks.append(line)
                if len(chunks) >= 1:
                    break
            if time.time() - start > 10:
                break
        assert len(chunks) > 0