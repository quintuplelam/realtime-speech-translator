# RCST (Realtime Conference Speech Translator) Design Spec

**Date:** 2026-04-18
**Status:** Approved

## Overview

A low-latency, GPU-accelerated speech-to-text translation system for conferences, providing real-time English ↔ Traditional Chinese bidirectional translation with bilingual subtitle display.

**Target Latency:** < 4s end-to-end

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Vue.js Frontend                          │
│         (src/ui/) - Netflix-style bilingual subtitles       │
└─────────────────────────────────────────────────────────────┘
                           ▲ SSE
                           │
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (src/api/)                  │
│                  - SSE stream push                          │
│                  - Translation logging to .md               │
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

---

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **ASR Engine** | Voxtral Mini 4B Realtime (Rust) | Q4 GGUF ~2.5GB, RTA ~0.4 |
| **Translation** | Argos Translate (CTranslate2) | EN↔ZH local inference |
| **Backend** | FastAPI (Python) | SSE streaming, async |
| **Frontend** | Vue 3 + Vite | Single HTML demo first |
| **GPU Support** | CUDA via CTranslate2 | `ARGOS_DEVICE_TYPE=cuda` |

---

## Components

### 1. ASR Layer (Voxtral Mini 4B)

- **Input:** Raw audio chunks (16kHz, 16-bit PCM)
- **Output:** English text with word-level timestamps
- **Model:** `mistralai/Voxtral-Mini-4B-Realtime-2602` (Q4 GGUF)
- **Interface:** Rust CLI → subprocess spawn from Python

### 2. Translation Layer (Argos Translate)

- **Input:** English text (one sentence at a time)
- **Output:** Traditional Chinese text
- **Model:** `translate-en_zh` Argos package
- **Interface:** Python library `argostranslate.translate`
- **GPU:** `ARGOS_DEVICE_TYPE=cuda` env var

### 3. Backend API (FastAPI)

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/stream` | SSE stream of `{en, zh, timestamp}` |
| `POST` | `/audio` | Receive audio for processing |

**SSE Event Format:**
```
data: {"en": "...", "zh": "...", "timestamp": "2026-04-18T..."}
```

### 4. Session Logger

- **Output:** `sessions/{session_id}/{timestamp}.md`
- **Format:**
  ```markdown
  # Session Log

  ## 2026-04-18 14:30:00

  | Time | English | 中文翻譯 |
  |------|---------|----------|
  | 14:30:01 | Welcome... | 歡迎... |
  ```

### 5. Frontend (Vue 3)

**Layout:**
- Deep black background (#0a0a0a)
- Two caption boxes stacked vertically
- EN box on top, ZH box below
- Font: Playfair Display (EN), Noto Sans SC (ZH)
- Gold accent (#d4af37) for labels

**Features:**
- SSE client connecting to `/stream`
- Fade-in animation on new caption
- Auto-reconnect on disconnect
- Fullscreen mode button

---

## UI Design

### Caption Box Styling
- Background: #141414 with subtle gold top-border gradient
- Text: #f5f5f5, 48px+, centered
- Max-width: 1400px, centered in viewport
- Padding: 2.5rem 4rem

### Header
- Logo: "RCST" in Playfair Display, gold
- Status indicator: pulsing dot (green when live)

---

## File Structure

```
realtime-speech-translator/
├── CLAUDE.md
├── .impeccable.md
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app + SSE endpoint
│   │   ├── asr.py           # Voxtral subprocess wrapper
│   │   ├── translator.py     # Argos Translate wrapper
│   │   └── logger.py        # Session markdown logger
│   └── ui/
│       ├── demo.html         # Current Vue demo
│       └── index.html       # Production Vue app
├── sessions/                # Generated session logs
├── models/                  # Downloaded model weights
├── requirements.txt
└── tests/
    └── test_pipeline.py
```

---

## Implementation Phases

### Phase 1: Backend Core (This Plan)
- FastAPI skeleton with health endpoint
- Voxtral CLI integration
- Argos Translate integration
- SSE endpoint returning mock data
- Session logger

### Phase 2: Frontend Integration
- Vue 3 app connecting to SSE
- Real-time caption display
- Fullscreen mode

### Phase 3: Audio Pipeline
- Audio chunking (500ms, 50% overlap)
- VAD integration if needed
- End-to-end latency optimization

---

## Verification

- [ ] Backend `/health` returns 200
- [ ] `/stream` SSE connects and sends events
- [ ] Argos Translate EN→ZH works locally
- [ ] Session .md file is created and updated
- [ ] Frontend connects to SSE and displays captions
- [ ] End-to-end latency < 4s

---

## Design Context (from .impeccable.md)

**Users:** 专业会议场景 — 国际会议、商务谈判、学术交流
**Brand:** 优雅/经典 (Netflix风格字幕)
**Theme:** 深色模式，专业电影字幕感
