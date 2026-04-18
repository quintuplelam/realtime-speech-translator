# RCST Frontend-Backend Separation Design Spec

**Date:** 2026-04-18
**Status:** Approved

## Problem Statement

Original architecture had audio flowing through two paths:
1. Server-side ffmpeg → ASR → Translate → SSE
2. Frontend HTML5 Audio playback

This caused:
- Bandwidth waste (same audio twice)
- SSE connections breaking (`ERR_INCOMPLETE_CHUNKED_ENCODING`)
- Complex error handling

## New Architecture

```
[NPR Stream] ──> [HTML5 Audio: plays stream] ──> [Web Audio API: captures] ──> [POST /audio chunks] ──> [Backend pipeline] ──> [SSE results]
```

### Frontend Responsibilities
- Play NPR stream via HTML5 Audio
- Capture audio via Web Audio API (MediaStreamSource → MediaRecorder or AudioContext)
- Send audio chunks to `/audio` endpoint
- Receive translations via SSE or direct response
- Display bilingual captions

### Backend Responsibilities
- Receive audio chunks via POST `/audio`
- Process through VAD → ASR → Translate pipeline
- Return transcription + translation (REST response or SSE)
- Log to session.md

## Frontend Changes

### New index.html Structure
- Audio element plays stream (not shown to user visually)
- Web Audio API captures audio output
- Sends audio chunks every ~3 seconds
- Updates UI with translation results

### Audio Capture Method
Using `AudioContext.createMediaStreamSource()` + `AudioWorklet` or `MediaRecorder`:

```javascript
// Pseudocode
const audioContext = new AudioContext();
const source = audioContext.createMediaStreamSource(audioElement.captureStream());
const processor = audioContext.createScriptProcessor(4096, 1, 1);
source.connect(processor);
processor.onaudioprocess = (e) => {
  const audioData = e.inputBuffer.getChannelData(0);
  sendToBackend(audioData);
};
```

## Backend Changes

### POST /audio Endpoint
```python
@app.post("/audio")
async def process_audio(audio_data: UploadFile = File(...)):
    """Receive audio chunk, return transcription + translation."""
    # Save uploaded audio
    # Process through pipeline
    # Return JSON with en, zh
```

### /pipeline/* Endpoints
- Deprecated or repurposed
- Main flow now uses `/audio` REST endpoint

## Files to Modify

1. `src/ui/index.html` - New audio capture implementation
2. `src/api/main.py` - New `/audio` endpoint
3. `src/api/pipeline.py` - Simplify (remove stream handling)

## Verification

- [ ] Frontend plays NPR stream
- [ ] Web Audio API captures audio
- [ ] Backend receives audio chunks
- [ ] Transcription appears in UI
- [ ] Translation appears in UI
- [ ] Session log is created
