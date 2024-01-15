import os

from pyannote.audio import Pipeline

read_key = os.environ.get('HF_TOKEN', None)
print(f"HF_TOKEN: {read_key}")
pyannote_pipeline = Pipeline.from_pretrained('pyannote/speaker-diarization', use_auth_token=read_key)