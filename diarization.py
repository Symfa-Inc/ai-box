from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained('pyannote/speaker-diarization', use_auth_token="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")

# DEMO_FILE = {'uri': 'blabal', 'audio': 'audio.wav'}
dz = pipeline('processed/Interview.mp3')

with open("processed/diarization.txt", "w") as text_file:
    text_file.write(str(dz))
