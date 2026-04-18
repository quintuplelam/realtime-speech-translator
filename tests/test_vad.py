import torch
from src.api.vad import SileroVAD

def test_silerovad_initializes():
    vad = SileroVAD()
    assert vad is not None
    assert hasattr(vad, 'model')

def test_silerovad_detect_speech():
    vad = SileroVAD()
    # Create dummy audio: 16kHz, 1 second of silence + speech
    audio = torch.randn(1, 16000)
    result = vad.detect_speech(audio)
    assert isinstance(result, list)  # List of (start, end) tuples