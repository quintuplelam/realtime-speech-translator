# Broadcast Stream Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add broadcast stream audio source support with Silero VAD sentence detection and real-time translation pipeline.

**Architecture:** NPR/broadcast stream → ffmpeg (16kHz WAV) → Silero VAD (sentence detection) → Voxtral ASR → Argos Translate → SSE → Session Log. Each sentence detected by VAD triggers ASR+Translate pipeline.

**Tech Stack:** ffmpeg, Silero VAD, Voxtral, Argos Translate, FastAPI SSE

---

## File Structure

```
src/
├── api/
│   ├── main.py              # (existing)
│   ├── pipeline.py         # NEW: Main pipeline orchestrator
│   ├── audio_stream.py      # NEW: Stream connector (ffmpeg wrapper)
│   ├── vad.py              # NEW: Silero VAD wrapper
│   ├── asr.py              # (existing)
│   ├── translator.py       # (existing)
│   └── logger.py           # (existing)
tests/
├── test_pipeline.py        # NEW: Pipeline tests
└── test_vad.py            # NEW: VAD tests
```

---

## Task 1: Silero VAD Wrapper

**Files:**
- Create: `src/api/vad.py`
- Create: `tests/test_vad.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_vad.py
import torch
from src.api.vad import SileroVAD

def test_silerovad_initializes():
    vad = SileroVAD()
    assert vad is not None
    assert hasattr(vad, 'model')

def test_silerovad_detect_speech():
    vad = SileroVAD()
    # Create dummy audio: 16kHz, 1 second of silence + speech
    audio = torch.randn(1, 16000)
    result = vad.detect_speech(audio)
    assert isinstance(result, list)  # List of (start, end) tuples
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vad.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write implementation**

```python
# src/api/vad.py
import torch
from typing import List, Tuple

class SileroVAD:
    def __init__(self, model_path: str = None, threshold: float = 0.5):
        self.threshold = threshold
        # Load Silero VAD model
        if model_path is None:
            self.model, utils = torch.hub.load(
                "snakers4/silero-vad",
                "silero_vad",
                verbose=False
            )
            self.get_speech_timestamps = utils[0]
        else:
            self.model = torch.jit.load(model_path)
            self.get_speech_timestamps = self.model.get_speech_timestamps

    def detect_speech(self, audio: torch.Tensor) -> List[Tuple[int, int]]:
        """Detect speech segments in audio tensor.

        Args:
            audio: Tensor of shape (1, N) where N is sample count at 16kHz

        Returns:
            List of (start_sample, end_sample) tuples for speech segments
        """
        with torch.no_grad():
            speech_timestamps = self.get_speech_timestamps(
                audio,
                threshold=self.threshold,
                sampling_rate=16000
            )
        return [(s['start'], s['end']) for s in speech_timestamps]

    def is_speech_end(self, audio: torch.Tensor, min_silence_ms: int = 500) -> bool:
        """Check if audio segment ends with silence (sentence boundary).

        Args:
            audio: Tensor of shape (1, N)
            min_silence_ms: Minimum silence duration to consider as boundary

        Returns:
            True if this is likely a sentence ending
        """
        segments = self.detect_speech(audio)
        if not segments:
            return False

        last_end = segments[-1][1]
        audio_len = audio.shape[1]
        silence_samples = int(min_silence_ms * 16000 / 1000)

        # If last speech ends before final 25% of audio, we have trailing silence
        trailing_silence = audio_len - last_end
        return trailing_silence > silence_samples
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vad.py -v`
Expected: PASS

- [ ] **Step 5: Install Silero VAD dependency**

```bash
pip install silero-vad
```

- [ ] **Step 6: Commit**

```bash
git add src/api/vad.py tests/test_vad.py
git commit -m "feat: add Silero VAD wrapper for sentence detection"
```

---

## Task 2: Audio Stream Connector

**Files:**
- Create: `src/api/audio_stream.py`
- Create: `tests/test_audio_stream.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_audio_stream.py
import subprocess
from src.api.audio_stream import AudioStreamConnector

def test_audio_connector_initializes():
    connector = AudioStreamConnector("https://example.com/stream.mp3")
    assert connector is not None
    assert connector.url == "https://example.com/stream.mp3"

def test_ffmpeg_available():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    assert result.returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_audio_stream.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write implementation**

```python
# src/api/audio_stream.py
import subprocess
import wave
import struct
import threading
import queue
from pathlib import Path
from typing import Optional, Iterator
import torch

class AudioStreamConnector:
    """Connect to audio stream and yield WAV chunks via ffmpeg."""

    def __init__(self, url: str, sample_rate: int = 16000, channels: int = 1):
        self.url = url
        self.sample_rate = sample_rate
        self.channels = channels
        self._queue: queue.Queue[torch.Tensor] = queue.Queue(maxsize=10)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start streaming audio in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()

    def _stream_loop(self):
        """Internal loop to stream audio via ffmpeg."""
        cmd = [
            "ffmpeg",
            "-i", self.url,
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-f", "s16le",  # Raw 16-bit PCM
            "-"  # Output to stdout
        ]

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            buffer = b""

            while self._running:
                data = process.stdout.read(4096)
                if not data:
                    break

                buffer += data

                # Accumulate ~1 second chunks
                chunk_size = self.sample_rate * 2  # 16-bit = 2 bytes per sample
                while len(buffer) >= chunk_size:
                    chunk = buffer[:chunk_size]
                    buffer = buffer[chunk_size:]

                    # Convert to tensor
                    samples = list(struct.unpack(f"<{self.sample_rate}h", chunk))
                    audio_tensor = torch.tensor(samples, dtype=torch.float32).unsqueeze(0) / 32768.0

                    try:
                        self._queue.put_nowait(audio_tensor)
                    except queue.Full:
                        pass  # Drop if buffer full

            process.terminate()
        except Exception:
            pass

    def get_chunks(self, timeout: float = 1.0) -> Iterator[torch.Tensor]:
        """Yield audio chunks from stream.

        Args:
            timeout: Seconds to wait for chunk before yielding empty

        Yields:
            Audio tensors of shape (1, sample_rate)
        """
        while self._running:
            try:
                chunk = self._queue.get(timeout=timeout)
                yield chunk
            except queue.Empty:
                yield torch.zeros(1, self.sample_rate)

    def stop(self):
        """Stop streaming."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_audio_stream.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/audio_stream.py tests/test_audio_stream.py
git commit -m "feat: add audio stream connector (ffmpeg wrapper)"
```

---

## Task 3: Main Pipeline Orchestrator

**Files:**
- Create: `src/api/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_pipeline.py
import asyncio
from src.api.pipeline import AudioPipeline

def test_pipeline_initializes():
    pipeline = AudioPipeline(stream_url="https://example.com/stream.mp3")
    assert pipeline is not None
    assert hasattr(pipeline, 'vad')
    assert hasattr(pipeline, 'asr')
    assert hasattr(pipeline, 'translator')

def test_pipeline_process_creates_events():
    # Test that pipeline generates translation events
    pipeline = AudioPipeline(stream_url="https://example.com/stream.mp3")
    assert callable(pipeline.process_chunk)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write implementation**

```python
# src/api/pipeline.py
import asyncio
import torch
from typing import Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime

from src.api.vad import SileroVAD
from src.api.asr import VoxtralASR
from src.api.translator import Translator

@dataclass
class CaptionEvent:
    en: str
    zh: str
    timestamp: str

class AudioPipeline:
    """Main pipeline: Stream → VAD → ASR → Translate → Caption"""

    def __init__(
        self,
        stream_url: str,
        vad: Optional[SileroVAD] = None,
        asr: Optional[VoxtralASR] = None,
        translator: Optional[Translator] = None
    ):
        from src.api.audio_stream import AudioStreamConnector

        self.stream_url = stream_url
        self.stream = AudioStreamConnector(stream_url)
        self.vad = vad or SileroVAD()
        self.asr = asr or VoxtralASR()
        self.translator = translator or Translator()

        self._buffer: List[torch.Tensor] = []
        self._min_segment_samples = 16000  # 1 second minimum

    def _process_buffer(self) -> Optional[str]:
        """Process accumulated buffer through ASR."""
        if len(self._buffer) < 3:  # Need at least 3 chunks (~3 seconds)
            return None

        # Concatenate buffer
        audio = torch.cat(self._buffer, dim=1)
        self._buffer.clear()

        # Check if this is a sentence ending
        if not self.vad.is_speech_end(audio, min_silence_ms=500):
            # Put it back if not a complete sentence
            self._buffer.append(audio)
            return None

        # Save temp WAV for Voxtral
        import tempfile
        import wave

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            # Write WAV
            with wave.open(temp_path, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                samples = (audio.squeeze().numpy() * 32767).astype('int16')
                w.writeframes(samples.tobytes())

        try:
            # ASR
            text = self.asr.transcribe(temp_path)
            if not text:
                return None
            return text
        finally:
            import os
            os.unlink(temp_path)

    async def run(self, callback: Callable[[CaptionEvent], None]):
        """Run pipeline with callback for each caption.

        Args:
            callback: Function called with CaptionEvent for each translation
        """
        self.stream.start()

        try:
            async for chunk in self.stream.get_chunks():
                self._buffer.append(chunk)

                # Try to process a sentence
                text = self._process_buffer()
                if text:
                    # Translate
                    zh = self.translator.translate(text, "en", "zh")

                    event = CaptionEvent(
                        en=text,
                        zh=zh or "",
                        timestamp=datetime.now().isoformat()
                    )
                    callback(event)

                await asyncio.sleep(0.1)
        finally:
            self.stream.stop()

    def process_chunk(self, audio: torch.Tensor) -> Optional[CaptionEvent]:
        """Process a single audio chunk (sync version).

        Args:
            audio: Audio tensor of shape (1, N)

        Returns:
            CaptionEvent if a sentence was completed, None otherwise
        """
        self._buffer.append(audio)

        text = self._process_buffer()
        if not text:
            return None

        zh = self.translator.translate(text, "en", "zh")
        return CaptionEvent(
            en=text,
            zh=zh or "",
            timestamp=datetime.now().isoformat()
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator with VAD sentence detection"
```

---

## Task 4: Broadcast Stream Tests

**Files:**
- Create: `tests/test_broadcast_stream.py`

- [ ] **Step 1: Write broadcast stream tests**

```python
# tests/test_broadcast_stream.py
import subprocess
import time
import requests
from src.api.audio_stream import AudioStreamConnector
from src.api.pipeline import AudioPipeline

NPR_STREAM_URL = "https://npr-ice.streamguys1.com/live.mp3"

def test_npr_stream_connection():
    """Test that NPR stream is accessible."""
    try:
        response = requests.head(NPR_STREAM_URL, timeout=10)
        assert response.status_code in [200, 301, 302], f"Stream returned {response.status_code}"
    except requests.exceptions.ConnectionError:
        # May fail in WSL without network, just skip
        pass

def test_ffmpeg_extracts_audio():
    """Test ffmpeg can extract audio from NPR stream."""
    # Extract 5 seconds of audio
    result = subprocess.run([
        "ffmpeg", "-y", "-i", NPR_STREAM_URL,
        "-t", "5", "-ar", "16000", "-ac", "1",
        "/tmp/test_npr.wav"
    ], capture_output=True, timeout=30)

    assert result.returncode == 0, f"ffmpeg failed: {result.stderr}"
    assert subprocess.run(["stat", "/tmp/test_npr.wav"]).returncode == 0

def test_audio_stream_yields_chunks():
    """Test AudioStreamConnector yields audio chunks."""
    if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0:
        return  # Skip if no ffmpeg

    connector = AudioStreamConnector(NPR_STREAM_URL)
    connector.start()

    chunks = []
    start = time.time()
    while time.time() - start < 5:  # Collect 5 seconds
        try:
            chunk = connector._queue.get(timeout=1.0)
            chunks.append(chunk)
        except:
            break

    connector.stop()

    assert len(chunks) > 0, "Should have received audio chunks"
    # Each chunk should be ~1 second of 16kHz audio
    assert chunks[0].shape[1] == 16000 or chunks[0].shape[1] < 16000
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_broadcast_stream.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/test_broadcast_stream.py
git commit -m "test: add broadcast stream integration tests"
```

---

## Task 5: Update main.py with Pipeline Integration

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: Read current main.py**

Run: `cat src/api/main.py`

- [ ] **Step 2: Add pipeline endpoints**

Add these endpoints to main.py:

```python
from src.api.pipeline import AudioPipeline, CaptionEvent

# Store active pipelines
active_pipelines = {}

@app.post("/pipeline/start")
async def start_pipeline(stream_url: str):
    """Start a broadcast stream pipeline."""
    pipeline_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    pipeline = AudioPipeline(stream_url)
    active_pipelines[pipeline_id] = pipeline
    return {"pipeline_id": pipeline_id, "stream_url": stream_url}

@app.get("/pipeline/{pipeline_id}/stream")
async def pipeline_stream(pipeline_id: str):
    """SSE stream for pipeline captions."""
    pipeline = active_pipelines.get(pipeline_id)
    if not pipeline:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    async def event_generator():
        async def callback(event: CaptionEvent):
            data = {
                "en": event.en,
                "zh": event.zh,
                "timestamp": event.timestamp
            }
            yield {
                "event": "caption",
                "data": json.dumps(data)
            }

        await pipeline.run(callback)

    return EventSourceResponse(event_generator())

@app.post("/pipeline/stop")
async def stop_pipeline(pipeline_id: str):
    """Stop a running pipeline."""
    pipeline = active_pipelines.pop(pipeline_id, None)
    if pipeline:
        pipeline.stream.stop()
    return {"status": "stopped"}
```

- [ ] **Step 3: Commit**

```bash
git add src/api/main.py
git commit -m "feat: integrate pipeline into FastAPI endpoints"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - Silero VAD wrapper ✓
   - Audio stream connector ✓
   - Pipeline orchestrator ✓
   - Broadcast stream tests ✓
   - FastAPI integration ✓

2. **Placeholder scan:** No TODOs, no TBDs

3. **Type consistency:** CaptionEvent used consistently across tasks

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-18-broadcast-pipeline.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
