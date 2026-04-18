import subprocess
import time
import requests
from src.api.audio_stream import AudioStreamConnector

NPR_STREAM_URL = "https://npr-ice.streamguys1.com/live.mp3"

def test_npr_stream_connection():
    """Test that NPR stream is accessible."""
    try:
        response = requests.head(NPR_STREAM_URL, timeout=10)
        assert response.status_code in [200, 301, 302], f"Stream returned {response.status_code}"
    except requests.exceptions.ConnectionError:
        # May fail in WSL without network, just skip
        pass

def test_ffmpeg_extracts_audio():
    """Test ffmpeg can extract audio from NPR stream."""
    # Extract 5 seconds of audio
    result = subprocess.run([
        "ffmpeg", "-y", "-i", NPR_STREAM_URL,
        "-t", "5", "-ar", "16000", "-ac", "1",
        "/tmp/test_npr.wav"
    ], capture_output=True, timeout=30)

    assert result.returncode == 0, f"ffmpeg failed: {result.stderr}"
    assert subprocess.run(["stat", "/tmp/test_npr.wav"]).returncode == 0

def test_audio_stream_yields_chunks():
    """Test AudioStreamConnector yields audio chunks."""
    if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0:
        return  # Skip if no ffmpeg

    connector = AudioStreamConnector(NPR_STREAM_URL)
    connector.start()

    chunks = []
    start = time.time()
    while time.time() - start < 5:  # Collect 5 seconds
        try:
            chunk = connector._queue.get(timeout=1.0)
            chunks.append(chunk)
        except:
            break

    connector.stop()

    assert len(chunks) > 0, "Should have received audio chunks"
    # Each chunk should be ~1 second of 16kHz audio
    assert chunks[0].shape[1] == 16000 or chunks[0].shape[1] < 16000