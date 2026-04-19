"""FunASR Client - Using FunASRNano via temp file (stable approach)."""
import io
import sys
import os
import tempfile
from typing import Optional

# Add Fun-ASR-vllm to path for custom model class
FUNASR_VLLM_PATH = "/home/quintuplelam/realtime-speech-translator/Fun-ASR-vllm"
sys.path.insert(0, FUNASR_VLLM_PATH)


class FunasrClient:
    """Client for FunASR ASR model using FunASRNano.

    Model: FunAudioLLM/Fun-ASR-Nano-2512
    Supports English and Chinese speech recognition
    VAD: Built-in
    """

    def __init__(self, model_id: str = "FunAudioLLM/Fun-ASR-Nano-2512"):
        self.model_id = model_id
        self.model = None
        self.kwargs = None
        self._load_model()

    def _load_model(self):
        """Load FunASR model."""
        import torch
        from model import FunASRNano

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[FunASR] Loading FunASRNano on {device}...")

        m, kwargs = FunASRNano.from_pretrained(model=self.model_id, device=device)
        m.eval()
        self.model = m
        self.kwargs = kwargs

        print("[FunASR] Model loaded successfully!")

    def transcribe(self, wav_bytes: bytes) -> Optional[str]:
        """Transcribe audio from WAV bytes.

        Saves to temp file and uses file path (more stable than raw tensor).
        """
        import soundfile as sf

        # Save WAV bytes to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(wav_bytes)
            temp_path = f.name

        try:
            # Run inference with file path (more stable)
            result = self.model.inference(
                data_in=[temp_path],
                **self.kwargs
            )

            if result and len(result) > 0:
                return result[0][0].get("text", "")
            return None
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
