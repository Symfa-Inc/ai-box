from dataclasses import dataclass
import os


@dataclass
class Config:
    speaker: str = os.environ.get("SPEAKER", default="diarization").lower()
    mode: str = os.environ.get("MODE", default="cpu").lower()
    quality: str = os.environ.get("QUALITY", default="low").lower()
    parallelism: int = int(os.environ.get("PARALLELISM", default=1))
    hf_key:str =  os.environ.get('HF_TOKEN', default='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')
    device: str = None

    def __post_init__(self):

        self.device = "cuda" if self.mode == "gpu" else "cpu"

        if self.mode == "gpu" and self.quality == "low":
            self.quality = "high"

