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
                self.model,
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