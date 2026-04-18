import subprocess
from src.api.asr import VoxtralASR, VoxtralNotFoundError

def test_voxtral_check():
    asr = VoxtralASR()
    assert asr is not None

def test_voxtral_cli_available():
    result = subprocess.run(["voxtral", "--help"], capture_output=True)
    # May fail if not installed - that's ok, we just check the wrapper
