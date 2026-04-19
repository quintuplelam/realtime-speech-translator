# FunASR Migration Design

**Date:** 2026-04-19
**Status:** Approved
**Type:** ASR Engine Migration (Voxtral → FunASR)

---

## 1. Overview

Replace Voxtral-Mini-4B-Realtime-2602 (vLLM) with FunASR nano 0.8B for ASR. FunASR runs as a direct library call (no separate server process), simplifying the architecture significantly.

**Key Changes:**
- ASR: Voxtral (vLLM server) → FunASR nano 0.8B (direct library)
- UI Layout: Vertical (English top, Chinese bottom) → Horizontal (English left, Chinese right)
- Audio Sources: Demo mode (broadcast stream), Real mode (microphone)
- Translation: Argos Translate (unchanged)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (src/ui/index.html)             │
│   - Demo mode: WNYC FM broadcast stream capture            │
│   - Real mode: Microphone input via getUserMedia           │
│   - Layout: Left = English, Right = Chinese (horizontal)   │
│   - Auto-scrolling: New captions prepend at top            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ POST /audio (WAV)
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (src/api/)                │
│   - /audio: Receives WAV, returns {en, zh}                │
│   - FunASR nano 0.8B (direct library call, no server)     │
│   - Argos Translate for EN→ZH translation                  │
│   - Session logging to .md                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Two-Mode Operation

| Mode | Audio Source | Use Case |
|------|-------------|----------|
| **Demo** | WNYC FM broadcast stream (`/proxy/npr`) | System demo, no mic needed |
| **Real** | Microphone (`getUserMedia`) | Actual conference use |

### Mode Switching (Frontend)

```javascript
if (mode === 'demo') {
  // Capture from broadcast stream
  hiddenAudio = document.createElement('audio');
  hiddenAudio.src = NPR_STREAM_URL;
  // Web Audio API processing
} else {
  // Capture from microphone
  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  // Connect to AudioContext
}
```

---

## 4. Streaming Display Behavior

**English and Chinese update independently (no SSE sync required):**

```
T0: ASR result arrives → English displayed immediately
T1: Translation result arrives → Chinese displayed (may lag English by 0.5-1s)
```

```javascript
eventSource.addEventListener('caption', (event) => {
    const data = JSON.parse(event.data);
    animateText(enText, data.en);      // English: immediate
    if (data.zh) {
        animateText(zhText, data.zh); // Chinese: after translation
    }
});
```

---

## 5. Frontend Layout

### Horizontal Split with Auto-Scrolling

```
┌──────────────────┬──────────────────┐
│       EN         │       ZH         │
│    (left/top)    │   (right/bot)   │
├──────────────────┼──────────────────┤
│ English caption  │ 中文翻譯 caption │
│ English caption  │ 中文翻譯 caption │
│ English caption  │ 中文翻譯 caption │
│      ...         │      ...        │
│  ▼ auto-scroll   │  ▼ auto-scroll  │
└──────────────────┴──────────────────┘
```

- New captions prepend at top (newest first)
- Auto-scroll to top on new caption arrival
- User can scroll up to view history

---

## 6. Files to Delete

| File | Reason |
|------|--------|
| `src/api/voxtral.py` | VoxtralClient - completely removed |
| `src/api/asr.py` | Deprecated, was just Voxtral alias |
| `start-vllm.py` | vLLM startup script - Voxtral-specific |
| `src/api/pipeline.py` | Depends on VoxtralASR |
| `src/api/vad.py` | Using FunASR built-in VAD |
| `docs/superpowers/specs/2026-04-19-voxtral-integration.md` | Voxtral docs |
| `models/Voxtral-Mini-4B-Realtime-2602/` | Voxtral model |
| `models/Voxtral-Mini-3B-2507/` | Voxtral model |
| `models/Voxtral-Mini-4B-GGUF/` | Voxtral model |

---

## 7. Files to Keep (Unchanged)

| File | Reason |
|------|--------|
| `src/api/translator.py` | Argos Translate, works correctly |
| `src/api/logger.py` | Session logging, works correctly |
| `src/api/main.py` | FastAPI app (modify endpoints only) |

---

## 8. Files to Create

| File | Description |
|------|-------------|
| `src/api/funasr_client.py` | FunASR nano 0.8B library wrapper |

### funasr_client.py Design

```python
"""FunASR Client - Direct library call for ASR."""
import numpy as np
from typing import Optional
import soundfile as sf

class FunasrClient:
    """Client for FunASR nano 0.8B ASR model.
    
    Model: damo/speech_paraformer-large-asr_nat_en-zh-cn-16k-common
    Size: ~800M params, ~1-2GB
    VAD: Built-in (no separate VAD needed)
    """
    
    def __init__(self, model_id: str = "damo/speech_paraformer-large-asr_nat_en-zh-cn-16k-common"):
        self.model_id = model_id
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load FunASR model."""
        from funasr import AutoModel
        self.model = AutoModel(model=self.model_id)
    
    def transcribe(self, wav_bytes: bytes) -> Optional[str]:
        """Transcribe audio from WAV bytes.
        
        Args:
            wav_bytes: WAV audio data
            
        Returns:
            Transcribed text or None
        """
        import io
        audio, sample_rate = sf.read(io.BytesIO(wav_bytes))
        
        result = self.model.generate(input=audio)
        if result and len(result) > 0:
            return result[0].get("text", "")
        return None
    
    @staticmethod
    def convert_wav_to_pcm16(wav_bytes: bytes) -> bytes:
        """Convert WAV to PCM16 forFunASR.
        
        Args:
            wav_bytes: WAV file content
            
        Returns:
            Raw PCM16 audio bytes (16kHz, mono)
        """
        import io
        import numpy as np
        audio, sample_rate = sf.read(io.BytesIO(wav_bytes))
        
        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            import soxr
            num_samples = int(len(audio) * 16000 / sample_rate)
            audio = soxr.resample(audio, num_samples).astype(np.float32)
        
        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()
```

---

## 9. Backend Changes (src/api/main.py)

### Modified /audio Endpoint

```python
from src.api.funasr_client import FunasrClient
from src.api.translator import Translator

# Global instances
funasr_client: Optional[FunasrClient] = None
current_translator: Optional[Translator] = None

@app.post("/audio")
async def process_audio(request: Request):
    """Receive audio chunk, return transcription + translation."""
    global funasr_client, current_translator
    
    audio_data = await request.body()
    if not audio_data:
        return JSONResponse({"en": "", "zh": "", "error": "No audio data"})
    
    result = {"en": "", "zh": "", "timestamp": datetime.now().isoformat()}
    
    try:
        # Initialize FunASR client if needed
        if funasr_client is None:
            funasr_client = FunasrClient()
        
        # Get transcription
        text = funasr_client.transcribe(audio_data)
        
        if text:
            result["en"] = text
            
            # Translate EN→ZH
            if current_translator:
                zh = current_translator.translate(text, "en", "zh")
                result["zh"] = zh or ""
            
            # Log session
            if session_logger and text:
                session_logger.log(text, result["zh"])
    
    except Exception as e:
        result["en"] = f"Error: {str(e)}"
    
    return JSONResponse(result)
```

---

## 10. Dependencies

```txt
# Requirements additions
funasr>=1.0
soundfile>=0.13.0

# Existing (keep)
argostranslate>=1.9.1
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sse-starlette>=1.8.2
```

---

## 11. Step-by-Step Implementation

### Phase 1: Setup FunASR
1. Install FunASR: `pip install funasr`
2. Create `src/api/funasr_client.py`

### Phase 2: Update Backend
3. Modify `src/api/main.py` to use FunasrClient
4. Remove Voxtral-related code

### Phase 3: Update Frontend
5. Update `src/ui/index.html` layout to horizontal split
6. Implement auto-scrolling
7. Add microphone mode toggle

### Phase 4: Cleanup
8. Delete Voxtral files
9. Delete Vad.py
10. Update CLAUDE.md and README.md

---

## 12. Verification Checklist

- [ ] FunASR model loads successfully
- [ ] `/audio` endpoint returns transcriptions
- [ ] Argos Translate produces Chinese translation
- [ ] Frontend displays horizontal layout correctly
- [ ] English and Chinese update independently
- [ ] Auto-scrolling works on new captions
- [ ] Demo mode (broadcast stream) works
- [ ] Real mode (microphone) works
- [ ] Session logger writes to .md file
- [ ] Latency is acceptable (< 4s end-to-end)

---

## 13. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| FunASR model download fails | Manual download via `huggingface-cli` |
| Large memory usage | FunASR nano 0.8B is lightweight |
| Mic permission denied | Fallback to demo mode |

---

## 14. Open Questions

None - all clarified during design.
