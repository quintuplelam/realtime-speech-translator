# FunASR Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate ASR from Voxtral (vLLM) to FunASR nano 0.8B, update frontend to horizontal split layout with auto-scrolling, and support demo (broadcast) and real (microphone) modes.

**Architecture:** FunASR runs as direct library call in FastAPI process (no separate server). Frontend sends WAV chunks to `/audio` endpoint, receives `{en, zh}` response. English and Chinese update independently.

**Tech Stack:** FunASR nano 0.8B, Argos Translate, FastAPI, Web Audio API, getUserMedia

---

## File Structure

### New Files
- `src/api/funasr_client.py` — FunASR library wrapper

### Files to Modify
- `src/api/main.py` — Replace Voxtral with FunasrClient
- `src/ui/index.html` — Horizontal layout + auto-scroll + mic mode
- `requirements.txt` — Add funasr, remove vllm
- `CLAUDE.md` — Update tech stack
- `README.md` — Update documentation

### Files to Delete
- `src/api/voxtral.py`
- `src/api/asr.py`
- `start-vllm.py`
- `src/api/pipeline.py`
- `src/api/vad.py`
- `models/Voxtral-Mini-4B-Realtime-2602/` (directory)
- `models/Voxtral-Mini-3B-2507/` (directory)
- `models/Voxtral-Mini-4B-GGUF/` (directory)

---

## Tasks

### Task 1: Install FunASR and Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add funasr to requirements.txt**

Open `requirements.txt` and add:
```
funasr>=1.0
soundfile>=0.13.0
```

- [ ] **Step 2: Remove vllm from requirements.txt**

Remove any `vllm` entry from requirements.txt.

- [ ] **Step 3: Install dependencies**

Run: `.venv/bin/pip install funasr soundfile`
Expected: Successful installation

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "deps: add funasr, soundfile, remove vllm"
```

---

### Task 2: Create FunASR Client

**Files:**
- Create: `src/api/funasr_client.py`

- [ ] **Step 1: Create funasr_client.py**

Create `src/api/funasr_client.py` with content:

```python
"""FunASR Client - Direct library call for ASR."""
import io
import numpy as np
from typing import Optional


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
        self.model = AutoModel(model=self.model_id, device="cpu")
    
    def transcribe(self, wav_bytes: bytes) -> Optional[str]:
        """Transcribe audio from WAV bytes.
        
        Args:
            wav_bytes: WAV audio data
            
        Returns:
            Transcribed text or None
        """
        import soundfile as sf
        
        audio, sample_rate = sf.read(io.BytesIO(wav_bytes))
        
        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        result = self.model.generate(input=audio)
        if result and len(result) > 0:
            return result[0].get("text", "")
        return None
```

- [ ] **Step 2: Commit**

```bash
git add src/api/funasr_client.py
git commit -m "feat: add FunasrClient for ASR"
```

---

### Task 3: Update Backend main.py

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: Read current main.py to understand structure**

Review the current `/audio` endpoint and Voxtral imports.

- [ ] **Step 2: Replace Voxtral imports with FunASR**

Find and replace:
```python
from src.api.voxtral import VoxtralClient, VoxtralNotAvailableError
```
With:
```python
from src.api.funasr_client import FunasrClient
```

- [ ] **Step 3: Replace global client variable**

Find and replace:
```python
vx_client: Optional[VoxtralClient] = None
```
With:
```python
funasr_client: Optional[FunasrClient] = None
```

- [ ] **Step 4: Update get_voxtral_client function**

Replace `get_voxtral_client()` function with:
```python
def get_funasr_client() -> Optional[FunasrClient]:
    """Get or create FunASR client instance."""
    global funasr_client
    if funasr_client is None:
        funasr_client = FunasrClient()
    return funasr_client
```

- [ ] **Step 5: Update /audio endpoint**

In the `/audio` endpoint, find the Voxtral transcription code:
```python
vx = get_voxtral_client()
...
text = await asyncio.wait_for(vx.transcribe_chunk(pcm16_data), timeout=10.0)
```

Replace with:
```python
funasr = get_funasr_client()
...
text = funasr.transcribe(audio_data)
```

- [ ] **Step 6: Remove VoxtralNotAvailableError handling**

Remove any `except VoxtralNotAvailableError` blocks.

- [ ] **Step 7: Remove VLLM management endpoints**

Delete these endpoints if they exist:
- `@app.get("/vllm/health")`
- `@app.post("/vllm/connect")`
- `@app.post("/vllm/disconnect")`

- [ ] **Step 8: Remove deprecated pipeline endpoints**

Delete if present:
- `@app.post("/pipeline/start")`
- `@app.get("/pipeline/{pipeline_id}/stream")`
- `@app.post("/pipeline/stop")`

- [ ] **Step 9: Update /health endpoint**

Replace vLLM health check with FunASR status:
```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    funasr_loaded = funasr_client is not None
    return JSONResponse({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "funasr": "loaded" if funasr_loaded else "not_loaded",
    })
```

- [ ] **Step 10: Commit**

```bash
git add src/api/main.py
git commit -m "feat: replace Voxtral with FunASR in backend"
```

---

### Task 4: Update Frontend HTML

**Files:**
- Modify: `src/ui/index.html`

- [ ] **Step 1: Replace vertical layout with horizontal split**

Find the `.caption-container` and `.caption-box` CSS. Replace with:

```css
.caption-container {
    flex: 1;
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: stretch;
    padding: 2rem;
    gap: 2rem;
    height: calc(100vh - 80px);
}
.caption-box {
    flex: 1;
    max-width: 50%;
    background: var(--bg-secondary);
    border-radius: 8px;
    padding: 2rem;
    border-top: 2px solid var(--accent-gold);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.caption-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--accent-gold);
    margin-bottom: 0.75rem;
    flex-shrink: 0;
}
.caption-history {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.caption-entry {
    font-size: 1.5rem;
    line-height: 1.4;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}
.caption-entry.fade-in {
    animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
```

- [ ] **Step 2: Update HTML structure**

Replace the caption boxes with:

```html
<main class="caption-container">
    <div class="caption-box">
        <div class="caption-label">English</div>
        <div class="caption-history" id="enHistory"></div>
    </div>
    <div class="caption-box">
        <div class="caption-label">中文翻譯</div>
        <div class="caption-history" id="zhHistory"></div>
    </div>
</main>
```

- [ ] **Step 3: Update JavaScript for streaming captions**

Replace the `animateText` function and caption handling:

```javascript
const enHistory = document.getElementById('enHistory');
const zhHistory = document.getElementById('zhHistory');

function prependCaption(historyEl, text) {
    const entry = document.createElement('div');
    entry.className = 'caption-entry fade-in';
    entry.textContent = text;
    historyEl.prepend(entry);
    // Auto-scroll to top
    historyEl.scrollTop = 0;
}

function addCaptions(en, zh) {
    if (en) prependCaption(enHistory, en);
    if (zh) prependCaption(zhHistory, zh);
}
```

- [ ] **Step 4: Update SSE handler**

In the `eventSource.addEventListener('caption', ...)` handler, replace `animateText` calls with `addCaptions`:

```javascript
eventSource.addEventListener('caption', (event) => {
    const data = JSON.parse(event.data);
    addCaptions(data.en, data.zh);
});
```

- [ ] **Step 5: Update /audio response handler**

In `sendAudioChunk`, replace `animateText` with `addCaptions`:

```javascript
if (result.en) {
    addCaptions(result.en, result.zh || '');
}
```

- [ ] **Step 6: Add microphone mode support**

Add a new function for microphone capture:

```javascript
let mediaStream = null;
let micProcessor = null;
let micAudioContext = null;

async function startMicMode() {
    try {
        // Request microphone
        mediaStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 16000
            } 
        });
        
        // Create audio context
        micAudioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
        
        // Create script processor for mic capture
        micProcessor = micAudioContext.createScriptProcessor(4096, 1, 1);
        
        micBuffer = [];
        micProcessor.onaudioprocess = (e) => {
            if (currentMode !== 'live') return;
            
            const inputData = e.inputBuffer.getChannelData(0);
            for (let i = 0; i < inputData.length; i++) {
                micBuffer.push(inputData[i]);
            }
            
            if (micBuffer.length >= CHUNK_SIZE) {
                const chunk = micBuffer.slice(0, CHUNK_SIZE);
                micBuffer = micBuffer.slice(CHUNK_SIZE);
                sendAudioChunk(chunk);
            }
        };
        
        // Connect mic to processor
        const micSource = micAudioContext.createMediaStreamSource(mediaStream);
        micSource.connect(micProcessor);
        micProcessor.connect(micAudioContext.destination);
        
        currentMode = 'live';
        updateModeUI('live');
        
    } catch (error) {
        console.error('Mic mode failed:', error);
        updateDebug('麥克風訪問失敗: ' + error.message);
        // Fallback to demo mode
        connectDemoSSE();
    }
}
```

- [ ] **Step 7: Update mode toggle button logic**

Update the demoBtn click handler:

```javascript
demoBtn.addEventListener('click', async () => {
    if (currentMode === 'live') {
        // Stop live mode
        stopLiveMode();
        connectDemoSSE();
    } else {
        // Show mode selection
        const useMic = confirm('使用麥克風？\n\n確定 = 麥克風模式\n取消 = 廣播演示模式');
        if (useMic) {
            await startMicMode();
        } else {
            await startLiveMode(); // This now uses broadcast stream
        }
    }
});
```

- [ ] **Step 8: Update stopLiveMode function**

```javascript
function stopLiveMode() {
    currentMode = 'demo';
    
    // Stop mic if active
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    if (micProcessor) {
        micProcessor.disconnect();
        micProcessor = null;
    }
    if (micAudioContext) {
        micAudioContext.close();
        micAudioContext = null;
    }
    // Stop broadcast audio if active
    if (hiddenAudio) {
        hiddenAudio.pause();
        if (hiddenAudio.src !== '') {
            hiddenAudio.src = '';
        }
    }
    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    
    audioBuffer = [];
    micBuffer = [];
    demoBtn.classList.remove('active');
    demoBtn.textContent = 'Demo Mode';
    updateDebug('');
    status.textContent = 'Demo Mode';
    status.classList.remove('live', 'processing');
}
```

- [ ] **Step 9: Commit**

```bash
git add src/ui/index.html
git commit -m "feat: horizontal layout with auto-scroll and mic mode"
```

---

### Task 5: Delete Voxtral Files

**Files to Delete:**
- `src/api/voxtral.py`
- `src/api/asr.py`
- `start-vllm.py`
- `src/api/pipeline.py`
- `src/api/vad.py`
- `models/Voxtral-Mini-4B-Realtime-2602/` (recursive)
- `models/Voxtral-Mini-3B-2507/` (recursive)
- `models/Voxtral-Mini-4B-GGUF/` (recursive)

- [ ] **Step 1: Delete Voxtral-related files**

Run:
```bash
rm -f src/api/voxtral.py src/api/asr.py start-vllm.py src/api/pipeline.py src/api/vad.py
rm -rf models/Voxtral-Mini-4B-Realtime-2602 models/Voxtral-Mini-3B-2507 models/Voxtral-Mini-4B-GGUF
```

- [ ] **Step 2: Delete Voxtral integration doc**

```bash
rm -f docs/superpowers/specs/2026-04-19-voxtral-integration.md
```

- [ ] **Step 3: Commit deletion**

```bash
git add -A
git commit -m "chore: remove Voxtral-related files"
```

---

### Task 6: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update CLAUDE.md ASR section**

Find the ASR section in CLAUDE.md and replace:
```
- **ASR**: WhisperX (https://github.com/m-bain/whisperX)
```
With:
```
- **ASR**: FunASR nano 0.8B (https://github.com/modelscope/FunASR)
```

- [ ] **Step 2: Update CLAUDE.md architecture**

Replace the architecture diagram with:
```
[Microphone/Broadcast] → Audio Chunking (3s) → FunASR (ASR) → Argos Translate (EN→ZH) → [Web UI]
```

- [ ] **Step 3: Update README.md tech stack**

Update the ASR Engine row:
```
| **ASR Engine** | FunASR nano 0.8B | Direct library call, no server |
```

- [ ] **Step 4: Update README.md installation section**

Remove Voxtral CLI installation steps. FunASR is installed via pip.

- [ ] **Step 5: Update README.md structure**

Remove `asr.py` from project structure (no longer exists).

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update for FunASR migration"
```

---

### Task 7: Test End-to-End

**Files:**
- Test: `src/ui/index.html` in browser

- [ ] **Step 1: Start FastAPI backend**

Run: `.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload`

- [ ] **Step 2: Open frontend**

Open `http://localhost:8000/ui/index.html` in browser.

- [ ] **Step 3: Test demo mode**

Click "Demo Mode" button. Verify:
- [ ] WNYC FM stream connects
- [ ] English captions appear in left panel
- [ ] Chinese translations appear in right panel
- [ ] Both panels auto-scroll to newest content
- [ ] Can scroll up to see history

- [ ] **Step 4: Test real mode (if mic available)**

Click "Live Mode" button. Accept mic permission. Verify:
- [ ] Microphone is captured
- [ ] English captions appear in left panel
- [ ] Chinese translations appear in right panel

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "feat: complete FunASR migration"
```

---

## Verification Checklist

After all tasks:
- [ ] FunASR model loads successfully
- [ ] `/audio` endpoint returns transcriptions
- [ ] Argos Translate produces Chinese translation
- [ ] Frontend displays horizontal layout correctly
- [ ] English and Chinese update independently
- [ ] Auto-scrolling works on new captions
- [ ] Demo mode (broadcast stream) works
- [ ] Real mode (microphone) works
- [ ] Session logger writes to .md file
- [ ] Voxtral files fully removed
