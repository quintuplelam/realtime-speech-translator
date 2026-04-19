# RCST - Realtime Conference Speech Translator

A low-latency, GPU-accelerated speech-to-text translation system for conferences, providing real-time English ↔ Traditional Chinese bidirectional translation with bilingual subtitle display.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Vue.js Frontend                             │
│  - HTML5 Audio (plays NPR stream)                              │
│  - Web Audio API (captures audio chunks)                        │
│  - SSE connection (receives translations)                     │
│  - Netflix-style bilingual subtitles                           │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ SSE (translation results)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (src/api/)                      │
│  - POST /audio (receives audio chunks)                          │
│  - GET /stream (SSE for translation results)                   │
│  - FunASR ASR + Argos Translate                                │
│  - Session logging to .md                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **ASR Engine** | FunASR nano 0.8B | Direct library call, no server |
| **VAD** | Silero VAD | Voice activity detection |
| **Translation** | Argos Translate (CTranslate2) | EN↔ZH local inference |
| **Backend** | FastAPI (Python) | REST + SSE streaming |
| **Frontend** | Vue 3 + Vanilla JS | Single HTML, no build required |
| **Audio Source** | Network Broadcast Streams | NPR, BBC, etc. |

## Key Design: Audio Separation

**Problem:** Original design had audio flowing through two paths (server ffmpeg + frontend playback), causing:
- Bandwidth waste
- SSE connection instability
- Complex error handling

**Solution:** Clean separation of concerns

```
[NPR Stream] ──> [HTML5 Audio: frontend only] ──> [Web Audio API: capture] ──> [POST /audio] ──> [Backend processing] ──> [SSE results]
```

**Benefits:**
1. Audio plays in one place only
2. SSE only carries text (not audio bytes)
3. Frontend controls playback + capture
4. Backend is stateless for audio transport

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/audio` | Receive audio chunk, return transcription + translation |
| `GET` | `/stream` | SSE stream for receiving translations (demo mode) |

## Session Logs

Sessions are saved to `sessions/{session_id}/session.md`:

```markdown
# Session Log: 20260418_143000

| Time | English | 中文翻譯 |
|------|---------|----------|
| 14:30:01 | Welcome to the conference. | 歡迎參加會議。 |
| 14:30:05 | Thank you for your attention. | 感謝大家的聆聽。 |
```

## Project Structure

```
realtime-speech-translator/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI app + endpoints
│   │   ├── translator.py    # Argos Translate wrapper
│   │   ├── logger.py        # Session markdown logger
│   │   └── pipeline.py      # Audio processing pipeline
│   └── ui/
│       ├── index.html       # Production frontend
│       └── demo.html        # Demo mode frontend
├── tests/
├── docs/
├── sessions/                # Generated session logs
└── requirements.txt
```

## Quick Start

### 1. Install Dependencies

```bash
# Create venv
python3.11 -m venv venv
source venv/bin/activate

# Install Python deps
pip install -r requirements.txt
```

### 2. Run Backend

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open Frontend

```bash
# In browser
open http://localhost:8000/ui/index.html

# Click "Live: NPR" button to start
```

## Testing with Broadcast Streams

### NPR News (English)

```bash
# Test stream connection
curl -I "https://npr-ice.streamguys1.com/live.mp3"
```

### Available Test Streams

| Station | Language | URL |
|---------|----------|-----|
| NPR News | English | `https://npr-ice.streamguys1.com/live.mp3` |
| BBC World Service | English | `http://stream.live.vc.bbcmedia.co.uk/bbc_world_service` |
| RFI Monde | French | `http://live-broadcast.rfi.fr/rfimonde-high.mp3` |

## License

Apache 2.0
