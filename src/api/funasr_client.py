"""FunASR Client - Using Fun-ASR-vllm approach with FunASRNano + vLLM."""
import io
import sys
from typing import Optional

# Add Fun-ASR-vllm to path for custom model class
FUNASR_VLLM_PATH = "/home/quintuplelam/realtime-speech-translator/.worktrees/feature/rcst-pipeline/Fun-ASR-vllm"
sys.path.insert(0, FUNASR_VLLM_PATH)


class FunasrClient:
    """Client for FunASR ASR model using FunASRNano + vLLM.

    Model: FunAudioLLM/Fun-ASR-Nano-2512
    Supports English and Chinese speech recognition via vLLM acceleration
    VAD: Built-in
    """

    def __init__(self, model_id: str = "FunAudioLLM/Fun-ASR-Nano-2512"):
        self.model_id = model_id
        self.model = None
        self.kwargs = None
        self.vllm = None
        self.vllm_sampling_params = None
        self._load_model()

    def _load_model(self):
        """Load FunASR model with vLLM acceleration."""
        import torch
        from model import FunASRNano
        from vllm import LLM, SamplingParams

        # Use GPU if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[FunASR] Loading FunASRNano on {device}...")

        # Load base model
        m, kwargs = FunASRNano.from_pretrained(model=self.model_id, device=device)
        m.eval()
        self.model = m
        self.kwargs = kwargs

        # Initialize vLLM for acceleration
        vllm_model_dir = "yuekai/Fun-ASR-Nano-2512-vllm"
        print(f"[FunASR] Loading vLLM model: {vllm_model_dir}...")

        self.vllm = LLM(
            model=vllm_model_dir,
            enable_prompt_embeds=True,
            gpu_memory_utilization=0.4,
            max_model_len=16384,  # Lowered to fit GPU memory
        )
        self.vllm_sampling_params = SamplingParams(
            top_p=0.001,
            max_tokens=500,
        )

        # Attach vLLM to model
        self.model.vllm = self.vllm
        self.model.vllm_sampling_params = self.vllm_sampling_params

        print("[FunASR] Model and vLLM loaded successfully!")

    def transcribe(self, wav_bytes: bytes) -> Optional[str]:
        """Transcribe audio from WAV bytes.

        Args:
            wav_bytes: WAV audio data

        Returns:
            Transcribed text or None
        """
        import soundfile as sf
        import torch

        audio, sample_rate = sf.read(io.BytesIO(wav_bytes))

        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Convert to torch tensor (FunASRNano expects torch.Tensor)
        audio_tensor = torch.from_numpy(audio).float().cuda()

        # Use vLLM-accelerated inference
        result = self.model.inference(
            data_in=[audio_tensor],
            **self.kwargs
        )

        if result and len(result) > 0:
            return result[0][0].get("text", "")
        return None
