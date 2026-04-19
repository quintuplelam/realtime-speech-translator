"""FunASR Client - Direct library call for ASR."""
import io
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
