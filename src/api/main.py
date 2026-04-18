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

# Translator optional - may not be available if argostranslate deps missing
try:
    from src.api.translator import Translator
    translator = Translator()
except ImportError:
    translator = None

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.get("/stream")
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

@app.post("/audio")
async def audio(audio_data: bytes = None):
    """Receive audio and process through pipeline."""
    # TODO: Implement actual Voxtral processing
    return JSONResponse({"status": "received", "length": len(audio_data) if audio_data else 0})

@app.post("/session/start")
async def start_session(session_id: str = None):
    """Start a new session logger."""
    global session_logger
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_logger = SessionLogger("sessions", session_id)
    return JSONResponse({"session_id": session_id, "path": str(session_logger.session_dir)})