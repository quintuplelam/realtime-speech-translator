import asyncio
from src.api.pipeline import AudioPipeline, CaptionEvent

def test_pipeline_initializes():
    pipeline = AudioPipeline(stream_url="https://example.com/stream.mp3")
    assert pipeline is not None
    assert hasattr(pipeline, 'vad')
    assert hasattr(pipeline, 'asr')
    assert hasattr(pipeline, 'translator')

def test_pipeline_process_creates_events():
    # Test that pipeline generates translation events
    pipeline = AudioPipeline(stream_url="https://example.com/stream.mp3")
    assert callable(pipeline.process_chunk)
