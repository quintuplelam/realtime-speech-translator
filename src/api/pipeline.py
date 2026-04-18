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
