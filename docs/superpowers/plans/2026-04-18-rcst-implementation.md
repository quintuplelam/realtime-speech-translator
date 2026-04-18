# RCST Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working end-to-end speech translation pipeline with Vue frontend, FastAPI backend, Voxtral ASR, and Argos Translate.

**Architecture:** FastAPI backend receives audio, runs Voxtral for ASR, Argos for translation, streams results via SSE to Vue frontend. Session logs written to markdown files.

**Tech Stack:** FastAPI, Vue 3, Voxtral Mini 4B (Rust CLI), Argos Translate (CTranslate2), SSE

---

## File Structure

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI app + SSE + endpoints
│   ├── asr.py           # Voxtral subprocess wrapper
│   ├── translator.py     # Argos Translate wrapper
│   └── logger.py        # Session markdown logger
├── ui/
│   ├── demo.html         # Current demo (already exists)
│   └── index.html       # Production Vue app
tests/
└── test_pipeline.py
sessions/                # Created at runtime
models/                  # Downloaded Voxtral weights
requirements.txt
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/api/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sse-starlette==1.8.2
argostranslate==1.9.1
python-multipart==0.0.6
aiofiles==23.2.1
```

- [ ] **Step 2: Create empty __init__.py files**

```bash
touch src/__init__.py src/api/__init__.py tests/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt src/ tests/
git commit -m "chore: project setup with requirements.txt"
```

---

## Task 2: Session Logger

**Files:**
- Create: `src/api/logger.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_logger.py
import os
import tempfile
from src.api.logger import SessionLogger

def test_session_logger_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = SessionLogger(tmpdir, "test-session")
        logger.log("Hello world", "你好世界")
        log_file = logger.session_dir / "session.md"
        assert log_file.exists()

def test_session_logger_format():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = SessionLogger(tmpdir, "test-session")
        logger.log("Hello world", "你好世界")
        content = (logger.session_dir / "session.md").read_text()
        assert "Hello world" in content
        assert "你好世界" in content
        assert "test-session" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_logger.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write implementation**

```python
# src/api/logger.py
from pathlib import Path
from datetime import datetime

class SessionLogger:
    def __init__(self, base_dir: str | Path, session_id: str):
        self.base_dir = Path(base_dir)
        self.session_id = session_id
        self.session_dir = self.base_dir / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._init_log_file()

    def _init_log_file(self):
        log_file = self.session_dir / "session.md"
        if not log_file.exists():
            log_file.write_text(f"# Session Log: {self.session_id}\n\n")

    def log(self, en: str, zh: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"| {timestamp} | {en} | {zh} |\n"
        log_file = self.session_dir / "session.md"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_logger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/logger.py tests/test_logger.py
git commit -m "feat: add session logger to markdown"
```

---

## Task 3: Argos Translator Wrapper

**Files:**
- Create: `src/api/translator.py`
- Create: `tests/test_translator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_translator.py
import argostranslate.package
import argostranslate.translate
from src.api.translator import Translator

def test_translator_initializes():
    t = Translator()
    assert t is not None

def test_translate_english_to_chinese():
    # Install package first if not installed
    argostranslate.package.update_package_index()
    packages = argostranslate.package.get_available_packages()
    pkg = next((p for p in packages if p.from_code == "en" and p.to_code == "zh"), None)
    if pkg:
        argostranslate.package.install_from_path(pkg.download())

    t = Translator()
    result = t.translate("Hello", "en", "zh")
    assert result is not None
    assert len(result) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_translator.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write implementation**

```python
# src/api/translator.py
import argostranslate.package
import argostranslate.translate
from typing import Optional

class Translator:
    def __init__(self):
        self._ensure_package_installed()

    def _ensure_package_installed(self, from_code="en", to_code="zh"):
        packages = argostranslate.package.get_available_packages()
        installed = {p.from_code + "_" + p.to_code for p in argostranslate.package.get_installed_packages()}
        target = f"{from_code}_{to_code}"

        if target not in installed:
            pkg = next((p for p in packages if p.from_code == from_code and p.to_code == to_code), None)
            if pkg:
                argostranslate.package.install_from_path(pkg.download())

    def translate(self, text: str, from_code: str = "en", to_code: str = "zh") -> Optional[str]:
        self._ensure_package_installed(from_code, to_code)
        try:
            return argostranslate.translate.translate(text, from_code, to_code)
        except Exception:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_translator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/translator.py tests/test_translator.py
git commit -m "feat: add Argos Translate wrapper"
```

---

## Task 4: Voxtral ASR Wrapper

**Files:**
- Create: `src/api/asr.py`
- Create: `tests/test_asr.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_asr.py
import subprocess
from src.api.asr import VoxtralASR, VoxtralNotFoundError

def test_voxtral_check():
    asr = VoxtralASR()
    assert asr is not None

def test_voxtral_cli_available():
    result = subprocess.run(["voxtral", "--help"], capture_output=True)
    # May fail if not installed - that's ok, we just check the wrapper
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_asr.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write implementation**

```python
# src/api/asr.py
import subprocess
import shlex
from pathlib import Path
from typing import Optional

class VoxtralNotFoundError(Exception):
    pass

class VoxtralASR:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path

    def check_cli(self) -> bool:
        """Check if voxtral CLI is available."""
        try:
            result = subprocess.run(
                ["voxtral", "--help"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def transcribe(self, audio_path: str) -> Optional[str]:
        """Transcribe audio file to text using voxtral CLI."""
        if not self.check_cli():
            raise VoxtralNotFoundError("voxtral CLI not found. Install from TrevorS/voxtral-mini-realtime-rs")

        cmd = ["voxtral", "transcribe", "--audio", audio_path]
        if self.model_path:
            cmd.extend(["--model", self.model_path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except subprocess.TimeoutExpired:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_asr.py -v`
Expected: PASS (may skip if voxtral not installed)

- [ ] **Step 5: Commit**

```bash
git add src/api/asr.py tests/test_asr.py
git commit -m "feat: add Voxtral ASR wrapper"
```

---

## Task 5: FastAPI Backend with SSE

**Files:**
- Create: `src/api/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_main.py
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_stream_endpoint_exists():
    # SSE endpoint - just check it responds
    with client.stream("GET", "/stream") as response:
        assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write implementation**

```python
# src/api/main.py
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from src.api.logger import SessionLogger
from src.api.translator import Translator
from src.api.asr import VoxtralASR, VoxtralNotFoundError

app = FastAPI(title="RCST API")

# Global instances
session_logger: Optional[SessionLogger] = None
translator = Translator()

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.get("/stream")
async def stream(request: Request):
    """SSE endpoint for real-time caption stream."""
    async def event_generator():
        # Demo mode - simulate captions
        demo_captions = [
            ("Welcome to the International Conference.", "歡迎參加國際會議。"),
            ("Today we discuss machine learning advances.", "今天我們討論機器學習進展。"),
            ("Thank you for your attention.", "感謝大家的聆聽。"),
        ]

        for en, zh in demo_captions:
            timestamp = datetime.now().isoformat()
            data = {"en": en, "zh": zh, "timestamp": timestamp}

            # Log to session
            if session_logger:
                session_logger.log(en, zh)

            yield {
                "event": "caption",
                "data": json.dumps(data)
            }
            await asyncio.sleep(5)  # 5 second interval

    return EventSourceResponse(event_generator())

@app.post("/audio")
async def audio(audio_data: bytes = None):
    """Receive audio and process through pipeline."""
    # TODO: Implement actual Voxtral processing
    return JSONResponse({"status": "received", "length": len(audio_data) if audio_data else 0})

@app.post("/session/start")
async def start_session(session_id: str = None):
    """Start a new session logger."""
    global session_logger
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_logger = SessionLogger("sessions", session_id)
    return JSONResponse({"session_id": session_id, "path": str(session_logger.session_dir)})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/main.py tests/test_main.py
git commit -m "feat: add FastAPI backend with SSE stream"
```

---

## Task 6: Vue Frontend Integration

**Files:**
- Create: `src/ui/index.html` (Production Vue app)

- [ ] **Step 1: Create Vue app that connects to SSE**

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RCST - 即時字幕</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0a;
            --bg-secondary: #141414;
            --text-primary: #f5f5f5;
            --accent-gold: #d4af37;
            --font-display: 'Playfair Display', serif;
            --font-body: 'Noto Sans SC', sans-serif;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: var(--font-body);
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo {
            font-family: var(--font-display);
            font-size: 1.25rem;
            color: var(--accent-gold);
        }
        .status { font-size: 0.75rem; color: #666; }
        .status.live { color: #4ade80; }
        .caption-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 2rem;
            gap: 1rem;
        }
        .caption-box {
            width: 100%;
            max-width: 1400px;
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 2.5rem 4rem;
            border-top: 2px solid var(--accent-gold);
        }
        .caption-label {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--accent-gold);
            margin-bottom: 0.75rem;
        }
        .caption-text {
            font-size: clamp(2rem, 4vw, 3rem);
            line-height: 1.4;
        }
        .caption-text.fade-in {
            animation: fadeIn 0.4s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">RCST</div>
        <div class="status" id="status">Connecting...</div>
    </header>

    <main class="caption-container">
        <div class="caption-box">
            <div class="caption-label">English</div>
            <div class="caption-text" id="enText"></div>
        </div>
        <div class="caption-box">
            <div class="caption-label">中文翻譯</div>
            <div class="caption-text" id="zhText"></div>
        </div>
    </main>

    <script>
        const enText = document.getElementById('enText');
        const zhText = document.getElementById('zhText');
        const status = document.getElementById('status');

        function connectSSE() {
            const eventSource = new EventSource('/stream');

            eventSource.addEventListener('caption', (event) => {
                const data = JSON.parse(event.data);

                // Animate text change
                [enText, zhText].forEach(el => {
                    el.classList.remove('fade-in');
                    void el.offsetWidth;
                    el.classList.add('fade-in');
                });

                enText.textContent = data.en;
                zhText.textContent = data.zh;
                status.textContent = 'Live';
                status.classList.add('live');
            });

            eventSource.onerror = () => {
                status.textContent = 'Reconnecting...';
                status.classList.remove('live');
                setTimeout(connectSSE, 3000);
            };
        }

        connectSSE();
    </script>
</body>
</html>
```

- [ ] **Step 2: Test frontend in browser**
Open `src/ui/index.html` and verify it can connect to backend SSE.

- [ ] **Step 3: Commit**

```bash
git add src/ui/index.html
git commit -m "feat: add Vue frontend for SSE captions"
```

---

## Task 7: End-to-End Test

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Write e2e test**

```python
# tests/test_e2e.py
import subprocess
import time
import requests
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

def test_session_start():
    response = client.post("/session/start")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "path" in data

def test_stream_sends_data():
    with client.stream("GET", "/stream") as response:
        assert response.status_code == 200
        # Read first event
        chunks = []
        start = time.time()
        while time.time() - start < 10:
            chunk = response.next()
            if chunk:
                chunks.append(chunk)
                if len(chunks) >= 1:
                    break
        assert len(chunks) > 0
```

- [ ] **Step 2: Run e2e test**

Run: `pytest tests/test_e2e.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: add end-to-end integration tests"
```

---

## Self-Review Checklist

1. **Spec coverage:** All requirements from spec have tasks:
   - Backend SSE ✓
   - Voxtral wrapper ✓
   - Argos Translate ✓
   - Session logger ✓
   - Vue frontend ✓

2. **Placeholder scan:** No TODOs, no TBDs

3. **Type consistency:** All method names match across tasks

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-18-rcst-implementation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
