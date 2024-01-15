import re
import glob
from openai import OpenAI

client = OpenAI()

def transcribe_with_whisper(file_path):
    audio_file = open(file_path, "rb")
    transcript = client.audio.transcriptions.create(
      model="whisper-1",
      file=audio_file,
      response_format="text"
    )
    return transcript

# Соберите все файлы по маске
file_paths = glob.glob("processed/chunks/????-SPEAKER_??-*.mp3")

# Файл для сохранения результатов
result_file = "processed/transcriptions.txt"

with open(result_file, "w", encoding='utf-8') as output_file:
    for file_path in file_paths[:5]:
        fileNamePattern = re.compile('(SPEAKER_\d+)-\((.+)\)\.mp3')
        match = fileNamePattern.search(file_path)
        speaker = match.group(1)
        timecode = match.group(2)
        transcription = transcribe_with_whisper(file_path)
        output_file.write(f"{speaker}, time: {timecode}: {transcription}\n")
        print(f"{speaker}, time: {timecode}: {transcription[:30]}...")

print(f"Транскрипции сохранены в {result_file}")