from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.api.logger import SessionLogger
from src.api.asr import VoxtralASR, VoxtralNotFoundError

app = FastAPI(title="RCST API")

# Global instances
session_logger: Optional[SessionLogger] = None
active_pipelines = {}

# Translator optional - may not be available if argostranslate deps missing
try:
    from src.api.translator import Translator
    translator = Translator()
except ImportError:
    translator = None

@ app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "timestamp": datetime.now().isoformat()})

@ app.get("/stream")
async def stream(request: Request):
    """SSE endpoint for real-time caption stream."""
    async def event_generator():
        # Demo mode - simulate captions
        demo_captions = [
            ("Welcome to the International Conference.", "歡迎參加國際會議。"),
            ("Today we discuss machine learning advances.", "今天我們討論機器學習進展。"),
            ("Thank you for your attention.", "感謝大家的聆聽。"),
        ]

        for en, zh in demo_captions:
            timestamp = datetime.now().isoformat()
            data = {"en": en, "zh": zh, "timestamp": timestamp}

            # Log to session
            if session_logger:
                session_logger.log(en, zh)

            yield {
                "event": "caption",
                "data": json.dumps(data)
            }
            await asyncio.sleep(5)  # 5 second interval

    return EventSourceResponse(event_generator())

@ app.post("/audio")
async def audio(audio_data: bytes = None):
    """Receive audio and process through pipeline."""
    return JSONResponse({"status": "received", "length": len(audio_data) if audio_data else 0})

@ app.post("/session/start")
async def start_session(session_id: str = None):
    """Start a new session logger."""
    global session_logger
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_logger = SessionLogger("sessions", session_id)
    return JSONResponse({"session_id": session_id, "path": str(session_logger.session_dir)})

@ app.post("/pipeline/start")
async def start_pipeline(stream_url: str):
    """Start a broadcast stream pipeline."""
    from src.api.pipeline import AudioPipeline
    pipeline_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    pipeline = AudioPipeline(stream_url)
    active_pipelines[pipeline_id] = pipeline
    return {"pipeline_id": pipeline_id, "stream_url": stream_url}

@ app.get("/pipeline/{pipeline_id}/stream")
async def pipeline_stream(pipeline_id: str):
    """SSE stream for pipeline captions."""
    from src.api.pipeline import AudioPipeline, CaptionEvent

    pipeline = active_pipelines.get(pipeline_id)
    if not pipeline:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    async def event_generator():
        async def callback(event: CaptionEvent):
            data = {
                "en": event.en,
                "zh": event.zh,
                "timestamp": event.timestamp
            }
            yield {
                "event": "caption",
                "data": json.dumps(data)
            }

        await pipeline.run(callback)

    return EventSourceResponse(event_generator())

@ app.post("/pipeline/stop")
async def stop_pipeline(pipeline_id: str):
    """Stop a running pipeline."""
    pipeline = active_pipelines.pop(pipeline_id, None)
    if pipeline:
        pipeline.stream.stop()
    return {"status": "stopped"}