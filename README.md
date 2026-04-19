# RCST - Realtime Conference Speech Translator

A low-latency, GPU-accelerated speech-to-text translation system for conferences, providing real-time English ↔ Traditional Chinese bidirectional translation with bilingual subtitle display.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (src/ui/)                       │
│         Vanilla HTML/JS - Netflix-style bilingual          │
│         subtitles with horizontal split layout             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ POST /audio (WAV chunks)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (src/api/)                │
│   - POST /audio: Receives WAV, returns {en, zh}           │
│   - GET /proxy/npr: NPR stream proxy                       │
│   - GET /health: Health check                              │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    FunASR    │  │    Argos     │  │   Session    │
│   Nano 0.8B  │  │  Translate   │  │    Logger    │
│   (ASR)      │  │  (EN→ZH)     │  │   (.md)      │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **ASR Engine** | FunASR nano 0.8B | Direct library call, no server |
| **VAD** | Built into FunASR | No separate VAD needed |
| **Translation** | Argos Translate (CTranslate2) | EN↔ZH local inference |
| **Backend** | FastAPI (Python) | REST API |
| **Frontend** | Vanilla HTML/JS | Single file, no build required |
| **Audio Source** | Microphone or Broadcast Streams | NPR, BBC, etc. |

## Two Modes

| Mode | Audio Source | Description |
|------|-------------|-------------|
| **Demo** | NPR broadcast stream via `/proxy/npr` | System demo without microphone |
| **Real** | Microphone via `getUserMedia` | Actual conference use |

## Key Design: Audio Separation

**Audio plays only in the frontend** (via HTML5 Audio element or Web Audio API destination). Backend receives **text only** via `POST /audio`.

**Benefits:**
1. Audio plays in one place only
2. Frontend controls playback + capture
3. Backend is stateless for audio transport

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/audio` | Receive WAV audio chunk, return transcription + translation |
| `GET` | `/proxy/npr` | Proxy for WNYC FM broadcast stream |
| `POST` | `/session/start` | Start a new session logger |

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
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── funasr_client.py  # FunASR ASR client wrapper
│   │   ├── translator.py      # Argos Translate wrapper
│   │   ├── audio_stream.py    # Audio stream connector (ffmpeg)
│   │   └── logger.py          # Session markdown logger
│   └── ui/
│       ├── index.html         # Production frontend
│       └── demo.html          # Demo mode frontend
├── Fun-ASR-vllm/              # FunASR model submodule
├── tests/                     # Test suite
├── docs/                      # Design specs and implementation plans
├── sessions/                  # Generated session logs
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

# Initialize git submodule
git submodule update --init --recursive
```

### 2. Run Backend

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open Frontend

```bash
# In browser
open http://localhost:8000/ui/index.html

# Click "Start Demo" button to select mode
```

## Testing Broadcast Streams

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
