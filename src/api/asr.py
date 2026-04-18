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
