from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.api.logger import SessionLogger
from src.api.asr import VoxtralASR, VoxtralNotFoundError

app = FastAPI(title="RCST API")

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/ui", StaticFiles(directory="src/ui"), name="ui")

# Global instances
session_logger: Optional[SessionLogger] = None
current_translator: Optional[object] = None

# Translator optional - may not be available if argostranslate deps missing
try:
    from src.api.translator import Translator
    current_translator = Translator()
except ImportError:
    current_translator = None


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.get("/stream")
async def stream(request: Request):
    """SSE endpoint for real-time caption stream (demo mode)."""
    async def event_generator():
        demo_captions = [
            ("Welcome to the International Conference.", "歡迎參加國際會議。"),
            ("Today we discuss machine learning advances.", "今天我們討論機器學習進展。"),
            ("Thank you for your attention.", "感謝大家的聆聽。"),
        ]

        for en, zh in demo_captions:
            timestamp = datetime.now().isoformat()
            data = {"en": en, "zh": zh, "timestamp": timestamp}

            if session_logger:
                session_logger.log(en, zh)

            yield {
                "event": "caption",
                "data": json.dumps(data)
            }
            await asyncio.sleep(5)

    return EventSourceResponse(event_generator())


@app.post("/audio")
async def process_audio(file: UploadFile = File(...)):
    """Receive audio chunk, return transcription + translation.

    Accepts WAV audio file and returns JSON with en (transcription)
    and zh (Chinese translation).
    """
    global session_logger, current_translator

    # Save uploaded audio to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        content = await file.read()

        # Write to WAV file
        with wave.open(temp_path, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            # Assume raw PCM data (convert from float32 to int16)
            import struct
            import numpy as np
            # Try to interpret as float32 PCM
            try:
                samples = np.frombuffer(content, dtype=np.float32)
                samples_int = (samples * 32767).astype(np.int16)
            except:
                # If already int16, use directly
                samples_int = np.frombuffer(content, dtype=np.int16)

            w.writeframes(samples_int.tobytes())

    result = {"en": "", "zh": "", "timestamp": datetime.now().isoformat()}

    try:
        # ASR using mock mode (Voxtral not installed)
        asr = VoxtralASR(mock_mode=True)
        text = asr.transcribe(temp_path)

        if text:
            result["en"] = text

            # Translate
            if current_translator:
                zh = current_translator.translate(text, "en", "zh")
                result["zh"] = zh or ""

            # Log to session
            if session_logger and text:
                session_logger.log(text, result["zh"])

    except Exception as e:
        result["en"] = f"Error: {str(e)}"

    finally:
        import os
        os.unlink(temp_path)

    return JSONResponse(result)


@app.post("/session/start")
async def start_session(session_id: str = None):
    """Start a new session logger."""
    global session_logger
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_logger = SessionLogger("sessions", session_id)
    return JSONResponse({"session_id": session_id, "path": str(session_logger.session_dir)})


# Keep old pipeline endpoints for compatibility but they won't work without Voxtral
@app.post("/pipeline/start")
async def start_pipeline(Request: Request):
    """Start a broadcast stream pipeline (deprecated - use /audio instead)."""
    body = await Request.json()
    stream_url = body.get("stream_url")
    pipeline_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return JSONResponse({
        "pipeline_id": pipeline_id,
        "stream_url": stream_url,
        "message": "Deprecated: Use frontend audio capture instead"
    })


@app.get("/pipeline/{pipeline_id}/stream")
async def pipeline_stream(pipeline_id: str):
    """SSE stream for pipeline captions (deprecated)."""
    return JSONResponse({"error": "Deprecated: Use /audio endpoint instead"}, status_code=410)


@app.post("/pipeline/stop")
async def stop_pipeline(Request: Request):
    """Stop a running pipeline (deprecated)."""
    return JSONResponse({"status": "stopped", "message": "Deprecated"})
