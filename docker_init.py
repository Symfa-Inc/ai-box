import os
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

from pyannote.audio import Pipeline

read_key = os.environ.get('HF_TOKEN', None)
print(f"HF_TOKEN: {read_key}")
pyannote_pipeline = Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', use_auth_token=read_key)
pyannote_pipeline.to(torch.device("cuda"))

w_model_id = "openai/whisper-large-v3"

device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

model = AutoModelForSpeechSeq2Seq.from_pretrained(
    w_model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
)

processor = AutoProcessor.from_pretrained(w_model_id)

pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    max_new_tokens=128,
    chunk_length_s=30,
    batch_size=16,
    return_timestamps=True,
    torch_dtype=torch_dtype,
    device=device,
)