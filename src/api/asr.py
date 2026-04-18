import subprocess
import shlex
import random
from pathlib import Path
from typing import Optional

class VoxtralNotFoundError(Exception):
    pass

class VoxtralASR:
    def __init__(self, model_path: Optional[str] = None, mock_mode: bool = False):
        self.model_path = model_path
        self.mock_mode = mock_mode

    def check_cli(self) -> bool:
        """Check if voxtral CLI is available."""
        if self.mock_mode:
            return True
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
        if self.mock_mode:
            # Return mock transcript for testing
            mock_sentences = [
                "Welcome to the program.",
                "Today we have exciting news to share.",
                "Thank you for listening.",
                "This is a test of the speech recognition system.",
                "NPR brings you news from around the world.",
            ]
            return random.choice(mock_sentences)

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
