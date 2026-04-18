import subprocess
import struct
import threading
import queue
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