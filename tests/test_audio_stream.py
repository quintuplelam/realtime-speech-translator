import subprocess
from src.api.audio_stream import AudioStreamConnector

def test_audio_connector_initializes():
    connector = AudioStreamConnector("https://example.com/stream.mp3")
    assert connector is not None
    assert connector.url == "https://example.com/stream.mp3"

def test_ffmpeg_available():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    assert result.returncode == 0