# RCST - Realtime Conference Speech Translator

A low-latency, GPU-accelerated speech-to-text translation system for conferences, providing real-time English ↔ Traditional Chinese bidirectional translation with bilingual subtitle display.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Vue.js Frontend                         │
│         (src/ui/) - Netflix-style bilingual subtitles       │
└─────────────────────────────────────────────────────────────┘
                           ▲ SSE
                           │
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (src/api/)                  │
│  - SSE stream push  - Translation logging to .md             │
└─────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Voxtral   │  │    Argos     │  │   Session    │
│   Mini 4B    │  │  Translate   │  │    Logger    │
│  (ASR/Rust)  │  │ (EN↔ZH CTranslate2) │  (to .md) │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **ASR Engine** | Voxtral Mini 4B Realtime (Rust) | Q4 GGUF ~2.5GB, RTA ~0.4 |
| **VAD** | Silero VAD | Voice activity detection |
| **Translation** | Argos Translate (CTranslate2) | EN↔ZH local inference |
| **Backend** | FastAPI (Python) | SSE streaming, async |
| **Frontend** | Vue 3 + Vanilla JS | Single HTML, no build required |
| **Audio Source** | Network Broadcast Streams | NPR, BBC, etc. |

## Quick Start

### 1. Install Dependencies

```bash
# Create venv
python3.11 -m venv venv
source venv/bin/activate

# Install Python deps
pip install -r requirements.txt

# Install Voxtral CLI (Rust)
cargo install voxtral --features wgpu,cli,hub
```

### 2. Install Translation Models

```bash
# Argos Translate (auto-downloads on first use)
argospm update
argospm install translate-en_zh
```

### 3. Run Backend

```bash
# Start FastAPI server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open Frontend

```bash
# In browser
open http://localhost:8000/src/ui/index.html
```

## Testing with Broadcast Streams

### NPR News (English)

```bash
# Test stream connection
ffmpeg -i "https://npr-ice.streamguys1.com/live.mp3" -t 10 -ar 16000 -ac 1 test_audio.wav

# Start real-time pipeline
python -m src.api.pipeline --stream-url "https://npr-ice.streamguys1.com/live.mp3"
```

### Available Test Streams

| Station | Language | URL |
|---------|----------|-----|
| NPR News | English | `https://npr-ice.streamguys1.com/live.mp3` |
| BBC World Service | English | `http://stream.live.vc.bbcmedia.co.uk/bbc_world_service` |
| RFI Monde | French | `http://live-broadcast.rfi.fr/rfimonde-high.mp3` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/stream` | SSE stream of `{en, zh, timestamp}` |
| `POST` | `/audio` | Receive audio for processing |
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
│   │   ├── main.py          # FastAPI app + SSE + endpoints
│   │   ├── asr.py           # Voxtral subprocess wrapper
│   │   ├── translator.py    # Argos Translate wrapper
│   │   ├── logger.py        # Session markdown logger
│   │   └── pipeline.py      # Audio pipeline (VAD → ASR → Translate)
│   └── ui/
│       ├── demo.html        # Demo frontend
│       └── index.html       # Production frontend
├── tests/
├── docs/
├── sessions/                # Generated session logs
└── requirements.txt
```

## License

Apache 2.0
