"""
RCST API Server - FunASR

FastAPI backend for Realtime Conference Speech Translator.
Uses FunASR for speech-to-text and Argos Translate for EN↔ZH translation.
"""

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime
from typing import Optional

from src.api.logger import SessionLogger
from src.api.funasr_client import FunasrClient
import httpx

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
app.mount("/ui", StaticFiles(directory="src/ui", html=True), name="ui")


@app.get("/proxy/npr")
async def proxy_npr():
    """Proxy WNYC FM stream for audio capture."""
    NPR_URL = "https://fm939.wnyc.org/wnycfm"

    async def stream_generator():
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                async with client.stream("GET", NPR_URL) as response:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk
        except Exception as e:
            print(f"NPR proxy error: {e}")

    return StreamingResponse(
        stream_generator(),
        media_type="audio/mpeg",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "no-cache",
        }
    )

# Global instances
session_logger: Optional[SessionLogger] = None
current_translator: Optional[object] = None
funasr_client: Optional[FunasrClient] = None

# Translator optional - may not be available if argostranslate deps missing
try:
    from src.api.translator import Translator
    current_translator = Translator()
    print("Argos Translate loaded successfully")
except ImportError as e:
    print(f"Warning: Argos Translate not available: {e}")
    current_translator = None


def get_funasr_client() -> Optional[FunasrClient]:
    """Get or create FunASR client instance."""
    global funasr_client
    if funasr_client is None:
        funasr_client = FunasrClient()
    return funasr_client


@app.get("/health")
async def health():
    """Health check endpoint."""
    funasr_loaded = funasr_client is not None
    return JSONResponse({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "funasr": "loaded" if funasr_loaded else "not_loaded",
    })


@app.post("/audio")
async def process_audio(request: Request):
    """Receive audio chunk, return transcription + translation."""
    global session_logger, current_translator

    audio_data = await request.body()

    if not audio_data or len(audio_data) == 0:
        return JSONResponse({"en": "", "zh": "", "error": "No audio data received"})

    result = {"en": "", "zh": "", "timestamp": datetime.now().isoformat()}

    try:
        funasr = get_funasr_client()

        if funasr is None:
            result["en"] = "Error: FunASR client not initialized"
            return JSONResponse(result)

        # Get transcription (FunASR is synchronous, run in thread to not block)
        text = await asyncio.to_thread(funasr.transcribe, audio_data)

        if text:
            result["en"] = text

            # Translate EN→ZH
            if current_translator:
                zh = current_translator.translate(text, "en", "zh")
                result["zh"] = zh or ""

            # Log to session
            if session_logger and text:
                session_logger.log(text, result["zh"])

    except asyncio.TimeoutError:
        result["en"] = ""
        result["zh"] = ""
    except Exception as e:
        result["en"] = f"Error: {str(e)}"

    return JSONResponse(result)


@app.post("/session/start")
async def start_session(session_id: str = None):
    """Start a new session logger."""
    global session_logger
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_logger = SessionLogger("sessions", session_id)
    return JSONResponse({"session_id": session_id, "path": str(session_logger.session_dir)})
